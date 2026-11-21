import os
os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['ENVIRONMENT'] = 'development'
os.environ['JWT_SECRET'] = 'isolated-test-secret-not-for-production-2026'
from sqlalchemy.pool import StaticPool
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
import app.models
from app.main import app
from app.core.database import Base, get_db
from app.models import User
from app.core.security import hash_password

engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
Base.metadata.create_all(engine)
TestSession = sessionmaker(bind=engine)
def override_db():
    with TestSession() as db: yield db
app.dependency_overrides[get_db] = override_db
client = TestClient(app)

def test_health():
    assert client.get('/api/v1/health').json()['status'] == 'ok'

def test_missing_auth():
    assert client.get('/api/v1/projects').status_code == 401

def test_register_is_not_privileged():
    response = client.post('/api/v1/auth/register', json={'email':'officer@example.org','password':'a-long-test-password'})
    assert response.status_code == 201, response.text
    token = response.json()['access_token']
    assert client.post('/api/v1/projects', headers={'Authorization':f'Bearer {token}'}, json={'name':'Cannot create'}).status_code == 403

def test_project_isolation():
    with TestSession() as db:
        db.add_all([User(id='analyst-a', email='a@example.org', password_hash=hash_password('a-long-test-password'), role='analyst'), User(id='analyst-b', email='b@example.org', password_hash=hash_password('b-long-test-password'), role='analyst')])
        db.commit()
    a = client.post('/api/v1/auth/login',json={'email':'a@example.org','password':'a-long-test-password'}).json()['access_token']
    b = client.post('/api/v1/auth/login',json={'email':'b@example.org','password':'b-long-test-password'}).json()['access_token']
    project = client.post('/api/v1/projects', headers={'Authorization':f'Bearer {a}'},json={'name':'Private'}).json()
    assert client.get('/api/v1/projects/'+project['id'],headers={'Authorization':f'Bearer {b}'}).status_code == 404
    assert client.get('/api/v1/projects/'+project['id'],headers={'Authorization':f'Bearer {a}'}).status_code == 200


from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from app.core.config import get_settings


def create_test_account():
    email = f"test-{uuid4().hex}@example.org"
    password = "a-secure-test-password"

    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password
        }
    )

    assert response.status_code == 201, response.text

    return email, password, response.json()["access_token"]


def test_current_user_profile():
    email, password, token = create_test_account()

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200

    data = response.json()

    assert data["email"] == email
    assert data["role"] == "officer"
    assert data["active"] is True
    assert data["id"]
    assert set(data) == {"id", "email", "role", "active"}


def test_profile_requires_authentication():
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401


def test_invalid_token():
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid-token"}
    )

    assert response.status_code == 401


def test_expired_token():
    email, password, token = create_test_account()

    profile = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert profile.status_code == 200
    user_id = profile.json()["id"]

    settings = get_settings()

    expired_token = jwt.encode(
        {
            "sub": user_id,
            "exp": datetime.now(timezone.utc)
                   - timedelta(minutes=5)
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm
    )

    response = client.get(
        "/api/v1/auth/me",
        headers={
            "Authorization": f"Bearer {expired_token}"
        }
    )

    assert response.status_code == 401


def test_wrong_password():
    email, password, token = create_test_account()

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "incorrect-password"
        }
    )

    assert response.status_code == 401


def test_duplicate_registration():
    email, password, token = create_test_account()

    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password
        }
    )

    assert response.status_code == 409


def test_prevent_role_escalation():
    email = f"role-{uuid4().hex}@example.org"

    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "a-secure-test-password",
            "role": "admin"
        }
    )

    assert response.status_code == 201

    token = response.json()["access_token"]

    profile = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert profile.status_code == 200
    assert profile.json()["role"] == "officer"


def test_inactive_user_token_rejected():
    email, password, token = create_test_account()

    from sqlalchemy import select

    with TestSession() as db:
        user = db.scalar(
            select(User).where(User.email == email)
        )
        user.active = False
        db.commit()

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 401



# PROJECT AND IMAGERY API TESTS

from app.models.entities import ProjectAccess


def create_role_account(role):
    user_id = str(uuid4())
    email = f"{role}-{uuid4().hex}@example.org"
    password = "secure-test-password-2026"

    with TestSession() as db:
        db.add(User(
            id=user_id,
            email=email,
            password_hash=hash_password(password),
            role=role,
            active=True,
        ))
        db.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )

    assert response.status_code == 200, response.text

    headers = {
        "Authorization":
            "Bearer " + response.json()["access_token"]
    }

    return user_id, headers


def create_owned_project(headers):
    response = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"name": "Test Project"},
    )

    assert response.status_code in (200, 201), response.text
    return response.json()["id"]


def grant_project_membership(project_id, user_id):
    with TestSession() as db:
        db.add(ProjectAccess(
            id=str(uuid4()),
            project_id=project_id,
            user_id=user_id,
        ))
        db.commit()


def test_project_update_success():
    _, headers = create_role_account("analyst")
    pid = create_owned_project(headers)

    response = client.put(
        f"/api/v1/projects/{pid}",
        headers=headers,
        json={
            "name": "Updated Project",
            "description": "Updated description",
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["name"] == "Updated Project"

    saved = client.get(
        f"/api/v1/projects/{pid}",
        headers=headers,
    )

    assert saved.status_code == 200
    assert saved.json()["name"] == "Updated Project"
    assert saved.json()["description"] == "Updated description"


def test_project_delete_success():
    _, headers = create_role_account("analyst")
    pid = create_owned_project(headers)

    response = client.delete(
        f"/api/v1/projects/{pid}",
        headers=headers,
    )

    assert response.status_code == 204, response.text
    assert not response.content

    response = client.get(
        f"/api/v1/projects/{pid}",
        headers=headers,
    )

    assert response.status_code == 404


def test_project_write_requires_authentication():
    _, headers = create_role_account("analyst")
    pid = create_owned_project(headers)

    assert client.put(
        f"/api/v1/projects/{pid}",
        json={"name": "Unauthorized"},
    ).status_code == 401

    assert client.delete(
        f"/api/v1/projects/{pid}"
    ).status_code == 401


def test_project_cross_tenant_write_denied():
    _, owner = create_role_account("analyst")
    _, other = create_role_account("analyst")
    pid = create_owned_project(owner)

    assert client.put(
        f"/api/v1/projects/{pid}",
        headers=other,
        json={"name": "Unauthorized"},
    ).status_code == 404

    assert client.delete(
        f"/api/v1/projects/{pid}",
        headers=other,
    ).status_code == 404

    saved = client.get(
        f"/api/v1/projects/{pid}",
        headers=owner,
    )

    assert saved.status_code == 200
    assert saved.json()["name"] == "Test Project"


def test_officer_cannot_modify_project():
    _, owner = create_role_account("analyst")
    officer_id, officer = create_role_account("officer")
    pid = create_owned_project(owner)

    grant_project_membership(pid, officer_id)

    assert client.put(
        f"/api/v1/projects/{pid}",
        headers=officer,
        json={"name": "Unauthorized"},
    ).status_code == 403

    assert client.delete(
        f"/api/v1/projects/{pid}",
        headers=officer,
    ).status_code == 403


def test_analyst_membership_does_not_grant_write():
    _, owner = create_role_account("analyst")
    member_id, member = create_role_account("analyst")
    pid = create_owned_project(owner)

    grant_project_membership(pid, member_id)

    assert client.get(
        f"/api/v1/projects/{pid}",
        headers=member,
    ).status_code == 200

    assert client.put(
        f"/api/v1/projects/{pid}",
        headers=member,
        json={"name": "Unauthorized"},
    ).status_code == 404

    assert client.delete(
        f"/api/v1/projects/{pid}",
        headers=member,
    ).status_code == 404


def test_project_update_invalid_input():
    _, headers = create_role_account("analyst")
    pid = create_owned_project(headers)

    for name in ("", "   ", "x" * 161):
        response = client.put(
            f"/api/v1/projects/{pid}",
            headers=headers,
            json={"name": name},
        )

        assert response.status_code == 422, response.text


def test_project_delete_with_dependencies():
    _, owner = create_role_account("analyst")
    member_id, _ = create_role_account("officer")
    pid = create_owned_project(owner)

    grant_project_membership(pid, member_id)

    response = client.delete(
        f"/api/v1/projects/{pid}",
        headers=owner,
    )

    assert response.status_code == 409, response.text

    assert client.get(
        f"/api/v1/projects/{pid}",
        headers=owner,
    ).status_code == 200


def test_admin_can_manage_other_projects():
    _, owner = create_role_account("analyst")
    _, admin = create_role_account("admin")
    pid = create_owned_project(owner)

    response = client.put(
        f"/api/v1/projects/{pid}",
        headers=admin,
        json={"name": "Admin Updated"},
    )

    assert response.status_code == 200, response.text

    response = client.delete(
        f"/api/v1/projects/{pid}",
        headers=admin,
    )

    assert response.status_code == 204, response.text


def test_imagery_invalid_format():
    _, headers = create_role_account("analyst")
    pid = create_owned_project(headers)

    response = client.post(
        f"/api/v1/projects/{pid}/imagery",
        headers=headers,
        json={"filename": "malicious.exe"},
    )

    assert response.status_code in (400, 422), response.text


def test_imagery_cross_project_access():
    _, owner = create_role_account("analyst")
    _, other = create_role_account("analyst")
    pid = create_owned_project(owner)

    response = client.get(
        f"/api/v1/projects/{pid}/imagery",
        headers=other,
    )

    assert response.status_code == 404, response.text

    response = client.post(
        f"/api/v1/projects/{pid}/imagery",
        headers=other,
        json={"filename": "satellite.png"},
    )

    assert response.status_code == 404, response.text


# ANALYSIS API TESTS

from app.models.entities import CandidateRegion


def register_test_imagery(pid, headers, filename):
    response = client.post(
        f"/api/v1/projects/{pid}/imagery",
        headers=headers,
        json={"filename": filename},
    )

    assert response.status_code == 201, response.text

    return response.json()["id"]


def create_analysis_fixture(headers):
    pid = create_owned_project(headers)

    before = register_test_imagery(
        pid, headers, "before.png"
    )

    after = register_test_imagery(
        pid, headers, "after.png"
    )

    payload = {
        "before_imagery_id": before,
        "after_imagery_id": after,
    }

    return pid, payload


def test_analysis_create_pending():
    _, headers = create_role_account("analyst")
    pid, payload = create_analysis_fixture(headers)

    response = client.post(
        f"/api/v1/projects/{pid}/analyses",
        headers=headers,
        json=payload,
    )

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["status"] == "pending"
    assert data["project_id"] == pid
    assert data["results_json"] is None

    aid = data["id"]

    saved = client.get(
        f"/api/v1/analyses/{aid}",
        headers=headers,
    )

    assert saved.status_code == 200
    assert saved.json()["id"] == aid

    listed = client.get(
        f"/api/v1/projects/{pid}/analyses",
        headers=headers,
    )

    assert listed.status_code == 200
    assert any(
        item["id"] == aid for item in listed.json()
    )


def test_analysis_same_imagery_rejected():
    _, headers = create_role_account("analyst")
    pid, payload = create_analysis_fixture(headers)

    payload["after_imagery_id"] = (
        payload["before_imagery_id"]
    )

    response = client.post(
        f"/api/v1/projects/{pid}/analyses",
        headers=headers,
        json=payload,
    )

    assert response.status_code == 422


def test_analysis_cross_project_imagery_rejected():
    _, owner = create_role_account("analyst")
    pid, payload = create_analysis_fixture(owner)

    other_pid = create_owned_project(owner)

    payload["after_imagery_id"] = register_test_imagery(
        other_pid, owner, "foreign.png"
    )

    response = client.post(
        f"/api/v1/projects/{pid}/analyses",
        headers=owner,
        json=payload,
    )

    assert response.status_code == 404


def test_analysis_missing_imagery_rejected():
    _, headers = create_role_account("analyst")
    pid, payload = create_analysis_fixture(headers)

    payload["after_imagery_id"] = str(uuid4())

    response = client.post(
        f"/api/v1/projects/{pid}/analyses",
        headers=headers,
        json=payload,
    )

    assert response.status_code == 404


def test_officer_cannot_create_analysis():
    _, owner = create_role_account("analyst")
    officer_id, officer = create_role_account("officer")

    pid, payload = create_analysis_fixture(owner)

    grant_project_membership(pid, officer_id)

    response = client.post(
        f"/api/v1/projects/{pid}/analyses",
        headers=officer,
        json=payload,
    )

    assert response.status_code == 403


def test_analysis_cross_tenant_access_denied():
    _, owner = create_role_account("analyst")
    _, other = create_role_account("analyst")

    pid, payload = create_analysis_fixture(owner)

    created = client.post(
        f"/api/v1/projects/{pid}/analyses",
        headers=owner,
        json=payload,
    )

    assert created.status_code == 201

    aid = created.json()["id"]

    for endpoint in (
        f"/api/v1/projects/{pid}/analyses",
        f"/api/v1/analyses/{aid}",
        f"/api/v1/analyses/{aid}/regions",
    ):
        response = client.get(
            endpoint, headers=other
        )

        assert response.status_code == 404


def test_candidate_region_access():
    _, owner = create_role_account("analyst")
    _, other = create_role_account("analyst")

    pid, payload = create_analysis_fixture(owner)

    created = client.post(
        f"/api/v1/projects/{pid}/analyses",
        headers=owner,
        json=payload,
    )

    assert created.status_code == 201

    aid = created.json()["id"]

    empty = client.get(
        f"/api/v1/analyses/{aid}/regions",
        headers=owner,
    )

    assert empty.status_code == 200
    assert empty.json() == []

    region_id = str(uuid4())

    # Synthetic fixture for testing only.
    with TestSession() as db:
        db.add(CandidateRegion(
            id=region_id,
            analysis_id=aid,
            region_label="Test region",
            bbox_pixels={
                "x": 10,
                "y": 20,
                "width": 30,
                "height": 40,
            },
            area_pixels=1200,
            area_m2=None,
            geometry_geojson=None,
        ))
        db.commit()

    response = client.get(
        f"/api/v1/regions/{region_id}",
        headers=owner,
    )

    assert response.status_code == 200
    assert response.json()["area_m2"] is None
    assert response.json()["geometry_geojson"] is None

    listed = client.get(
        f"/api/v1/analyses/{aid}/regions",
        headers=owner,
    )

    assert listed.status_code == 200
    assert listed.json()[0]["id"] == region_id

    denied = client.get(
        f"/api/v1/regions/{region_id}",
        headers=other,
    )

    assert denied.status_code == 404


def test_analysis_requires_authentication():
    pid = str(uuid4())
    aid = str(uuid4())
    rid = str(uuid4())

    for endpoint in (
        f"/api/v1/projects/{pid}/analyses",
        f"/api/v1/analyses/{aid}",
        f"/api/v1/analyses/{aid}/regions",
        f"/api/v1/regions/{rid}",
    ):
        assert client.get(endpoint).status_code == 401


# INVESTIGATION API TESTS

from app.models.entities import Analysis


def create_investigation_region():
    _, owner = create_role_account("analyst")
    pid, payload = create_analysis_fixture(owner)

    response = client.post(
        f"/api/v1/projects/{pid}/analyses",
        headers=owner,
        json=payload,
    )

    assert response.status_code == 201, response.text

    aid = response.json()["id"]
    rid = str(uuid4())

    # Synthetic completed analysis for testing only.
    with TestSession() as db:
        analysis = db.get(Analysis, aid)
        analysis.status = "completed"

        db.add(CandidateRegion(
            id=rid,
            analysis_id=aid,
            region_label="Test investigation region",
            area_pixels=100,
        ))

        db.commit()

    return pid, rid, owner


def create_investigation_fixture():
    pid, rid, owner = create_investigation_region()

    response = client.post(
        f"/api/v1/projects/{pid}/investigations",
        headers=owner,
        json={"region_id": rid},
    )

    assert response.status_code == 201, response.text

    return pid, response.json()["id"], owner


def test_investigation_create_success():
    pid, iid, owner = create_investigation_fixture()

    response = client.get(
        f"/api/v1/investigations/{iid}",
        headers=owner,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "open"
    assert response.json()["assigned_to_id"] is None

    listed = client.get(
        f"/api/v1/projects/{pid}/investigations",
        headers=owner,
    )

    assert listed.status_code == 200
    assert any(
        row["id"] == iid for row in listed.json()
    )


def test_investigation_cross_project_region():
    pid, rid, owner = create_investigation_region()
    another_project = create_owned_project(owner)

    response = client.post(
        f"/api/v1/projects/{another_project}/investigations",
        headers=owner,
        json={"region_id": rid},
    )

    assert response.status_code == 404


def test_investigation_cross_tenant_denied():
    pid, iid, owner = create_investigation_fixture()
    _, other = create_role_account("analyst")

    assert client.get(
        f"/api/v1/investigations/{iid}",
        headers=other,
    ).status_code == 404

    assert client.get(
        f"/api/v1/projects/{pid}/investigations",
        headers=other,
    ).status_code == 404


def test_investigation_assignment_success():
    pid, iid, owner = create_investigation_fixture()
    officer_id, officer = create_role_account("officer")

    grant_project_membership(pid, officer_id)

    response = client.put(
        f"/api/v1/investigations/{iid}/assign",
        headers=owner,
        json={"assigned_to_id": officer_id},
    )

    assert response.status_code == 200, response.text
    assert response.json()["assigned_to_id"] == officer_id

    assert client.get(
        f"/api/v1/investigations/{iid}",
        headers=officer,
    ).status_code == 200


def test_investigation_unrelated_officer_rejected():
    pid, iid, owner = create_investigation_fixture()
    officer_id, officer = create_role_account("officer")

    response = client.put(
        f"/api/v1/investigations/{iid}/assign",
        headers=owner,
        json={"assigned_to_id": officer_id},
    )

    assert response.status_code == 404


def test_unassigned_officer_cannot_access():
    pid, iid, owner = create_investigation_fixture()
    officer_id, officer = create_role_account("officer")

    grant_project_membership(pid, officer_id)

    response = client.get(
        f"/api/v1/investigations/{iid}",
        headers=officer,
    )

    assert response.status_code == 404

    listed = client.get(
        f"/api/v1/projects/{pid}/investigations",
        headers=officer,
    )

    assert listed.status_code == 200
    assert listed.json() == []


def test_investigation_status_workflow():
    pid, iid, owner = create_investigation_fixture()
    officer_id, officer = create_role_account("officer")

    grant_project_membership(pid, officer_id)

    assigned = client.put(
        f"/api/v1/investigations/{iid}/assign",
        headers=owner,
        json={"assigned_to_id": officer_id},
    )

    assert assigned.status_code == 200, assigned.text

    endpoint = f"/api/v1/investigations/{iid}/status"

    assert client.put(
        endpoint,
        headers=officer,
        json={"status": "submitted"},
    ).status_code == 409

    started = client.put(
        endpoint,
        headers=officer,
        json={"status": "in_progress"},
    )

    assert started.status_code == 200, started.text

    submitted = client.put(
        endpoint,
        headers=officer,
        json={"status": "submitted"},
    )

    assert submitted.status_code == 200
    assert submitted.json()["status"] == "submitted"

    assert client.put(
        endpoint,
        headers=officer,
        json={"status": "approved"},
    ).status_code == 422


def test_officer_cannot_reassign_investigation():
    pid, iid, owner = create_investigation_fixture()
    officer_id, officer = create_role_account("officer")

    grant_project_membership(pid, officer_id)

    response = client.put(
        f"/api/v1/investigations/{iid}/assign",
        headers=officer,
        json={"assigned_to_id": officer_id},
    )

    assert response.status_code == 403


# ANALYST DECISION TESTS


def create_submitted_investigation():
    pid, iid, owner = create_investigation_fixture()

    officer_id, officer = create_role_account("officer")

    grant_project_membership(pid, officer_id)

    assigned = client.put(
        f"/api/v1/investigations/{iid}/assign",
        headers=owner,
        json={"assigned_to_id": officer_id},
    )

    assert assigned.status_code == 200, assigned.text

    for status in ("in_progress", "submitted"):
        response = client.put(
            f"/api/v1/investigations/{iid}/status",
            headers=officer,
            json={"status": status},
        )

        assert response.status_code == 200, response.text

    return pid, iid, owner, officer


def decision_payload():
    return {
        "decision": "confirmed",
        "rationale": "Synthetic review for API testing.",
    }


def test_analyst_decision_success():
    pid, iid, owner, officer = (
        create_submitted_investigation()
    )

    endpoint = f"/api/v1/investigations/{iid}/decision"

    profile = client.get(
        "/api/v1/auth/me",
        headers=owner,
    )

    assert profile.status_code == 200

    response = client.post(
        endpoint,
        headers=owner,
        json=decision_payload(),
    )

    assert response.status_code == 201, response.text
    assert response.json()["decision"] == "confirmed"
    assert response.json()["reviewer_id"] == profile.json()["id"]

    saved = client.get(
        endpoint, headers=owner
    )

    assert saved.status_code == 200
    assert saved.json()["id"] == response.json()["id"]

    investigation = client.get(
        f"/api/v1/investigations/{iid}",
        headers=owner,
    )

    assert investigation.status_code == 200
    assert investigation.json()["status"] == "reviewed"


def test_duplicate_decision_rejected():
    pid, iid, owner, officer = (
        create_submitted_investigation()
    )

    endpoint = f"/api/v1/investigations/{iid}/decision"

    first = client.post(
        endpoint,
        headers=owner,
        json=decision_payload(),
    )

    assert first.status_code == 201

    second = client.post(
        endpoint,
        headers=owner,
        json={
            "decision": "rejected",
            "rationale": "Attempt to replace decision",
        },
    )

    assert second.status_code == 409

    saved = client.get(endpoint, headers=owner)
    assert saved.status_code == 200
    assert saved.json()["id"] == first.json()["id"]
    assert saved.json()["decision"] == "confirmed"


def test_decision_before_submission_rejected():
    pid, iid, owner = create_investigation_fixture()

    response = client.post(
        f"/api/v1/investigations/{iid}/decision",
        headers=owner,
        json=decision_payload(),
    )

    assert response.status_code == 409


def test_officer_cannot_make_decision():
    pid, iid, owner, officer = (
        create_submitted_investigation()
    )

    response = client.post(
        f"/api/v1/investigations/{iid}/decision",
        headers=officer,
        json=decision_payload(),
    )

    assert response.status_code == 403


def test_decision_cross_tenant_access_denied():
    pid, iid, owner, officer = (
        create_submitted_investigation()
    )

    _, other = create_role_account("analyst")

    endpoint = f"/api/v1/investigations/{iid}/decision"

    response = client.post(
        endpoint,
        headers=other,
        json=decision_payload(),
    )

    assert response.status_code == 404

    created = client.post(
        endpoint,
        headers=owner,
        json=decision_payload(),
    )

    assert created.status_code == 201

    assert client.get(
        endpoint, headers=other
    ).status_code == 404

    assert client.get(endpoint).status_code == 401


def test_analyst_member_cannot_make_decision():
    pid, iid, owner, officer = (
        create_submitted_investigation()
    )

    member_id, member = create_role_account("analyst")

    grant_project_membership(pid, member_id)

    response = client.post(
        f"/api/v1/investigations/{iid}/decision",
        headers=member,
        json=decision_payload(),
    )

    assert response.status_code == 403


def test_invalid_decision_rejected():
    pid, iid, owner, officer = (
        create_submitted_investigation()
    )

    endpoint = f"/api/v1/investigations/{iid}/decision"

    payloads = [
        {
            "decision": "automatic_approval",
            "rationale": "Invalid decision",
        },
        {
            "decision": "confirmed",
            "rationale": "",
        },
        {
            "decision": "confirmed",
            "rationale": "   ",
        },
        {
            "decision": "confirmed",
            "rationale": "x" * 5001,
        },
        {
            "decision": "confirmed",
            "rationale": "Invalid reviewer",
            "reviewer_id": "forged-reviewer",
        },
    ]

    for payload in payloads:
        response = client.post(
            endpoint,
            headers=owner,
            json=payload,
        )

        assert response.status_code == 422, response.text


def test_admin_can_record_decision():
    pid, iid, owner, officer = (
        create_submitted_investigation()
    )

    admin_id, admin = create_role_account("admin")

    response = client.post(
        f"/api/v1/investigations/{iid}/decision",
        headers=admin,
        json={
            "decision": "inconclusive",
            "rationale": "Additional evidence required",
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["reviewer_id"] == admin_id
    assert response.json()["decision"] == "inconclusive"


# REPORT API TESTS

from app.models.entities import Investigation


def get_region_analysis_id(region_id):
    with TestSession() as db:
        region = db.get(CandidateRegion, region_id)
        return region.analysis_id


def get_investigation_analysis_id(investigation_id):
    with TestSession() as db:
        investigation = db.get(
            Investigation, investigation_id
        )

        region = db.get(
            CandidateRegion, investigation.region_id
        )

        return region.analysis_id


def test_report_generation_success():
    pid, rid, owner = create_investigation_region()

    aid = get_region_analysis_id(rid)

    response = client.get(
        f"/api/v1/analyses/{aid}/report",
        headers=owner,
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["project"]["id"] == pid
    assert data["analysis"]["id"] == aid
    assert data["summary"]["candidate_regions"] == 1
    assert data["regions"][0]["id"] == rid
    assert data["imagery"]["before"]["filename"] == "before.png"
    assert data["imagery"]["after"]["filename"] == "after.png"


def test_report_download():
    pid, rid, owner = create_investigation_region()

    aid = get_region_analysis_id(rid)

    response = client.get(
        f"/api/v1/analyses/{aid}/report?download=true",
        headers=owner,
    )

    assert response.status_code == 200

    assert "attachment" in response.headers[
        "content-disposition"
    ]

    assert "application/json" in response.headers[
        "content-type"
    ]

    assert response.headers["cache-control"] == "no-store"


def test_report_preserves_missing_geographic_data():
    pid, rid, owner = create_investigation_region()

    aid = get_region_analysis_id(rid)

    response = client.get(
        f"/api/v1/analyses/{aid}/report",
        headers=owner,
    )

    assert response.status_code == 200

    region = response.json()["regions"][0]

    assert region["geometry_geojson"] is None
    assert region["area_m2"] is None


def test_report_requires_completed_analysis():
    _, owner = create_role_account("analyst")

    pid, payload = create_analysis_fixture(owner)

    analysis = client.post(
        f"/api/v1/projects/{pid}/analyses",
        headers=owner,
        json=payload,
    )

    assert analysis.status_code == 201

    aid = analysis.json()["id"]

    response = client.get(
        f"/api/v1/analyses/{aid}/report",
        headers=owner,
    )

    assert response.status_code == 409


def test_report_cross_tenant_access_denied():
    pid, rid, owner = create_investigation_region()

    _, other = create_role_account("analyst")

    aid = get_region_analysis_id(rid)

    response = client.get(
        f"/api/v1/analyses/{aid}/report",
        headers=other,
    )

    assert response.status_code == 404


def test_report_officer_access_denied():
    pid, rid, owner = create_investigation_region()

    officer_id, officer = create_role_account("officer")

    grant_project_membership(pid, officer_id)

    aid = get_region_analysis_id(rid)

    response = client.get(
        f"/api/v1/analyses/{aid}/report",
        headers=officer,
    )

    assert response.status_code == 403


def test_report_contains_human_decision():
    pid, iid, owner, officer = (
        create_submitted_investigation()
    )

    decision = client.post(
        f"/api/v1/investigations/{iid}/decision",
        headers=owner,
        json=decision_payload(),
    )

    assert decision.status_code == 201, decision.text

    aid = get_investigation_analysis_id(iid)

    response = client.get(
        f"/api/v1/analyses/{aid}/report",
        headers=owner,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["summary"]["confirmed_decisions"] == 1
    assert data["summary"]["reviewed_investigations"] == 1

    assert data["decisions"][0]["decision"] == "confirmed"

    assert data["decisions"][0]["reviewer_id"] == (
        decision.json()["reviewer_id"]
    )


def test_report_requires_authentication():
    response = client.get(
        f"/api/v1/analyses/{uuid4()}/report"
    )

    assert response.status_code == 401


# MEMBERSHIP API TESTS


def test_add_and_list_project_members():
    _, owner = create_role_account("analyst")
    officer_id, officer = create_role_account("officer")

    pid = create_owned_project(owner)

    endpoint = f"/api/v1/projects/{pid}/members"

    response = client.post(
        endpoint,
        headers=owner,
        json={"user_id": officer_id},
    )

    assert response.status_code == 201, response.text
    assert response.json()["user_id"] == officer_id

    listed = client.get(endpoint, headers=owner)

    assert listed.status_code == 200
    assert any(
        row["user_id"] == officer_id
        for row in listed.json()
    )

    assert client.get(
        f"/api/v1/projects/{pid}",
        headers=officer,
    ).status_code == 200


def test_duplicate_membership_rejected():
    _, owner = create_role_account("analyst")
    officer_id, _ = create_role_account("officer")

    pid = create_owned_project(owner)

    endpoint = f"/api/v1/projects/{pid}/members"

    payload = {"user_id": officer_id}

    assert client.post(
        endpoint, headers=owner, json=payload
    ).status_code == 201

    assert client.post(
        endpoint, headers=owner, json=payload
    ).status_code == 409


def test_officer_cannot_manage_members():
    _, owner = create_role_account("analyst")
    officer_id, officer = create_role_account("officer")
    target_id, _ = create_role_account("officer")

    pid = create_owned_project(owner)

    grant_project_membership(pid, officer_id)

    endpoint = f"/api/v1/projects/{pid}/members"

    assert client.get(
        endpoint, headers=officer
    ).status_code == 403

    assert client.post(
        endpoint,
        headers=officer,
        json={"user_id": target_id},
    ).status_code == 403


def test_membership_cross_tenant_denied():
    _, owner = create_role_account("analyst")
    _, other = create_role_account("analyst")
    target_id, _ = create_role_account("officer")

    pid = create_owned_project(owner)

    endpoint = f"/api/v1/projects/{pid}/members"

    assert client.get(
        endpoint, headers=other
    ).status_code == 404

    assert client.post(
        endpoint,
        headers=other,
        json={"user_id": target_id},
    ).status_code == 404


def test_analyst_member_cannot_manage_members():
    _, owner = create_role_account("analyst")
    member_id, member = create_role_account("analyst")
    target_id, _ = create_role_account("officer")

    pid = create_owned_project(owner)

    grant_project_membership(pid, member_id)

    endpoint = f"/api/v1/projects/{pid}/members"

    assert client.get(
        endpoint, headers=member
    ).status_code == 403

    assert client.post(
        endpoint,
        headers=member,
        json={"user_id": target_id},
    ).status_code == 403


def test_remove_membership_revokes_access():
    _, owner = create_role_account("analyst")
    officer_id, officer = create_role_account("officer")

    pid = create_owned_project(owner)

    endpoint = f"/api/v1/projects/{pid}/members"

    assert client.post(
        endpoint,
        headers=owner,
        json={"user_id": officer_id},
    ).status_code == 201

    response = client.delete(
        f"{endpoint}/{officer_id}",
        headers=owner,
    )

    assert response.status_code == 204

    assert client.get(
        f"/api/v1/projects/{pid}",
        headers=officer,
    ).status_code == 404


def test_assigned_officer_removal_rejected():
    pid, iid, owner = create_investigation_fixture()

    officer_id, officer = create_role_account("officer")

    endpoint = f"/api/v1/projects/{pid}/members"

    assert client.post(
        endpoint,
        headers=owner,
        json={"user_id": officer_id},
    ).status_code == 201

    assigned = client.put(
        f"/api/v1/investigations/{iid}/assign",
        headers=owner,
        json={"assigned_to_id": officer_id},
    )

    assert assigned.status_code == 200, assigned.text

    response = client.delete(
        f"{endpoint}/{officer_id}",
        headers=owner,
    )

    assert response.status_code == 409


def test_invalid_membership_rejected():
    owner_id, owner = create_role_account("analyst")
    inactive_id, _ = create_role_account("officer")
    admin_id, _ = create_role_account("admin")

    with TestSession() as db:
        account = db.get(User, inactive_id)
        account.active = False
        db.commit()

    pid = create_owned_project(owner)

    endpoint = f"/api/v1/projects/{pid}/members"

    for invalid_id in (
        str(uuid4()), inactive_id, admin_id
    ):
        response = client.post(
            endpoint,
            headers=owner,
            json={"user_id": invalid_id},
        )

        assert response.status_code == 404

    assert client.post(
        endpoint,
        headers=owner,
        json={"user_id": owner_id},
    ).status_code == 409

    assert client.get(endpoint).status_code == 401


# IMAGE UPLOAD API TESTS

import io
from PIL import Image
from app.models.entities import Imagery
from app.api.v1 import imagery as imagery_module


def make_test_image():
    buffer = io.BytesIO()
    Image.new("RGB", (32, 32), "green").save(
        buffer, format="PNG"
    )
    return buffer.getvalue()


def test_actual_image_upload(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "SENTINEL_STORAGE_ROOT", str(tmp_path)
    )

    _, owner = create_role_account("analyst")
    pid = create_owned_project(owner)

    data = make_test_image()

    response = client.post(
        f"/api/v1/projects/{pid}/imagery/upload",
        headers=owner,
        files={
            "file": ("satellite.png", data, "image/png")
        },
    )

    assert response.status_code == 201, response.text

    imagery_id = response.json()["id"]

    with TestSession() as db:
        row = db.get(Imagery, imagery_id)

        assert row is not None
        assert row.project_id == pid
        assert row.crs is None
        assert row.metadata_json["storage_status"] == "stored"
        assert (tmp_path / row.storage_key).read_bytes() == data


def test_upload_corrupted_image():
    _, owner = create_role_account("analyst")
    pid = create_owned_project(owner)

    response = client.post(
        f"/api/v1/projects/{pid}/imagery/upload",
        headers=owner,
        files={"file": ("fake.png", b"not an image", "image/png")},
    )

    assert response.status_code == 400


def test_upload_unsupported_extension():
    _, owner = create_role_account("analyst")
    pid = create_owned_project(owner)

    response = client.post(
        f"/api/v1/projects/{pid}/imagery/upload",
        headers=owner,
        files={
            "file": ("image.exe", make_test_image(), "image/png")
        },
    )

    assert response.status_code == 415


def test_upload_extension_mismatch():
    _, owner = create_role_account("analyst")
    pid = create_owned_project(owner)

    response = client.post(
        f"/api/v1/projects/{pid}/imagery/upload",
        headers=owner,
        files={
            "file": ("image.jpg", make_test_image(), "image/jpeg")
        },
    )

    assert response.status_code == 415


def test_upload_size_limit(monkeypatch):
    monkeypatch.setattr(
        imagery_module, "MAX_UPLOAD_BYTES", 10
    )

    _, owner = create_role_account("analyst")
    pid = create_owned_project(owner)

    response = client.post(
        f"/api/v1/projects/{pid}/imagery/upload",
        headers=owner,
        files={
            "file": ("image.png", make_test_image(), "image/png")
        },
    )

    assert response.status_code == 413


def test_upload_cross_tenant_denied():
    _, owner = create_role_account("analyst")
    _, other = create_role_account("analyst")

    pid = create_owned_project(owner)

    response = client.post(
        f"/api/v1/projects/{pid}/imagery/upload",
        headers=other,
        files={
            "file": ("image.png", make_test_image(), "image/png")
        },
    )

    assert response.status_code == 404


def test_officer_upload_denied():
    _, owner = create_role_account("analyst")
    officer_id, officer = create_role_account("officer")

    pid = create_owned_project(owner)

    grant_project_membership(pid, officer_id)

    response = client.post(
        f"/api/v1/projects/{pid}/imagery/upload",
        headers=officer,
        files={
            "file": ("image.png", make_test_image(), "image/png")
        },
    )

    assert response.status_code == 403


def test_upload_requires_authentication():
    response = client.post(
        f"/api/v1/projects/{uuid4()}/imagery/upload",
        files={
            "file": ("image.png", make_test_image(), "image/png")
        },
    )

    assert response.status_code == 401


# REAL DETECTION TESTS

from PIL import ImageDraw


def make_detection_image(changed=False, size=(128, 128)):
    image = Image.new("RGB", size, "black")

    if changed:
        ImageDraw.Draw(image).rectangle(
            (30, 30, 90, 90),
            fill="white",
        )

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def upload_detection_image(pid, headers, filename, data):

    response = client.post(
        f"/api/v1/projects/{pid}/imagery/upload",
        headers=headers,
        files={"file": (filename, data, "image/png")},
    )

    assert response.status_code == 201, response.text

    return response.json()["id"]


def create_real_analysis(
    headers,
    changed=True,
    after_size=(128, 128),
    parameters=None,
):
    pid = create_owned_project(headers)

    before = upload_detection_image(
        pid, headers, "before.png",
        make_detection_image(),
    )

    after = upload_detection_image(
        pid, headers, "after.png",
        make_detection_image(changed, after_size),
    )

    response = client.post(
        f"/api/v1/projects/{pid}/analyses",
        headers=headers,
        json={
            "before_imagery_id": before,
            "after_imagery_id": after,
            "parameters_json": parameters,
        },
    )

    assert response.status_code == 201, response.text

    return pid, response.json()["id"]


def test_real_change_detection(tmp_path, monkeypatch):

    monkeypatch.setenv(
        "SENTINEL_STORAGE_ROOT", str(tmp_path)
    )

    _, owner = create_role_account("analyst")

    pid, aid = create_real_analysis(owner)

    response = client.post(
        f"/api/v1/analyses/{aid}/run",
        headers=owner,
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["status"] == "completed"
    assert data["results_json"]["stats"]["changed_pixels"] > 0

    regions = client.get(
        f"/api/v1/analyses/{aid}/regions",
        headers=owner,
    )

    assert regions.status_code == 200
    assert len(regions.json()) > 0
    assert len(regions.json()) == (
        data["results_json"]["stats"]["candidate_region_count"]
    )

    for region in regions.json():
        assert region["area_pixels"] > 0
        assert region["area_m2"] is None
        assert region["geometry_geojson"] is None

    report = client.get(
        f"/api/v1/analyses/{aid}/report",
        headers=owner,
    )

    assert report.status_code == 200
    assert report.json()["summary"]["candidate_regions"] > 0


def test_identical_images_no_changes(tmp_path, monkeypatch):

    monkeypatch.setenv(
        "SENTINEL_STORAGE_ROOT", str(tmp_path)
    )

    _, owner = create_role_account("analyst")

    pid, aid = create_real_analysis(
        owner, changed=False
    )

    response = client.post(
        f"/api/v1/analyses/{aid}/run",
        headers=owner,
    )

    assert response.status_code == 200, response.text

    assert response.json()["results_json"]["stats"][
        "changed_pixels"
    ] == 0

    regions = client.get(
        f"/api/v1/analyses/{aid}/regions",
        headers=owner,
    )

    assert regions.status_code == 200
    assert regions.json() == []


def test_detection_requires_real_files():

    _, owner = create_role_account("analyst")
    pid, payload = create_analysis_fixture(owner)

    created = client.post(
        f"/api/v1/projects/{pid}/analyses",
        headers=owner,
        json=payload,
    )

    assert created.status_code == 201

    aid = created.json()["id"]

    response = client.post(
        f"/api/v1/analyses/{aid}/run",
        headers=owner,
    )

    assert response.status_code == 409

    saved = client.get(
        f"/api/v1/analyses/{aid}",
        headers=owner,
    )

    assert saved.json()["status"] == "pending"


def test_detection_cannot_run_twice(tmp_path, monkeypatch):

    monkeypatch.setenv(
        "SENTINEL_STORAGE_ROOT", str(tmp_path)
    )

    _, owner = create_role_account("analyst")

    pid, aid = create_real_analysis(owner)
    endpoint = f"/api/v1/analyses/{aid}/run"

    assert client.post(
        endpoint, headers=owner
    ).status_code == 200

    assert client.post(
        endpoint, headers=owner
    ).status_code == 409


def test_detection_cross_tenant_denied(tmp_path, monkeypatch):

    monkeypatch.setenv(
        "SENTINEL_STORAGE_ROOT", str(tmp_path)
    )

    _, owner = create_role_account("analyst")
    _, other = create_role_account("analyst")

    pid, aid = create_real_analysis(owner)

    assert client.post(
        f"/api/v1/analyses/{aid}/run",
        headers=other,
    ).status_code == 404


def test_officer_cannot_execute_detection(tmp_path, monkeypatch):

    monkeypatch.setenv(
        "SENTINEL_STORAGE_ROOT", str(tmp_path)
    )

    _, owner = create_role_account("analyst")

    officer_id, officer = create_role_account("officer")

    pid, aid = create_real_analysis(owner)

    grant_project_membership(pid, officer_id)

    assert client.post(
        f"/api/v1/analyses/{aid}/run",
        headers=officer,
    ).status_code == 403


def test_detection_dimension_mismatch(tmp_path, monkeypatch):

    monkeypatch.setenv(
        "SENTINEL_STORAGE_ROOT", str(tmp_path)
    )

    _, owner = create_role_account("analyst")

    pid, aid = create_real_analysis(
        owner,
        after_size=(64, 64),
    )

    assert client.post(
        f"/api/v1/analyses/{aid}/run",
        headers=owner,
    ).status_code == 422

    saved = client.get(
        f"/api/v1/analyses/{aid}", headers=owner
    )

    assert saved.json()["status"] == "pending"


def test_detection_invalid_parameters(tmp_path, monkeypatch):

    monkeypatch.setenv(
        "SENTINEL_STORAGE_ROOT", str(tmp_path)
    )

    _, owner = create_role_account("analyst")

    pid, aid = create_real_analysis(
        owner,
        parameters={"threshold": 5},
    )

    assert client.post(
        f"/api/v1/analyses/{aid}/run",
        headers=owner,
    ).status_code == 422


# COMPLETE WORKFLOW TEST


def test_complete_change_sentinel_workflow(
    tmp_path, monkeypatch
):
    monkeypatch.setenv(
        "SENTINEL_STORAGE_ROOT", str(tmp_path)
    )

    analyst_id, analyst = create_role_account("analyst")
    officer_id, officer = create_role_account("officer")

    # Create project, upload actual images and register analysis.
    pid, aid = create_real_analysis(analyst)

    # Execute the real detection engine.
    response = client.post(
        f"/api/v1/analyses/{aid}/run",
        headers=analyst,
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "completed"

    assert response.json()["results_json"]["stats"][
        "changed_pixels"
    ] > 0

    # Retrieve actual detected candidate regions.
    regions = client.get(
        f"/api/v1/analyses/{aid}/regions",
        headers=analyst,
    )

    assert regions.status_code == 200
    assert len(regions.json()) > 0

    region = regions.json()[0]
    rid = region["id"]

    assert region["area_pixels"] > 0
    assert region["area_m2"] is None
    assert region["geometry_geojson"] is None

    # Add officer through the membership API.
    member = client.post(
        f"/api/v1/projects/{pid}/members",
        headers=analyst,
        json={"user_id": officer_id},
    )

    assert member.status_code == 201, member.text

    # Create an investigation for a detected region.
    investigation = client.post(
        f"/api/v1/projects/{pid}/investigations",
        headers=analyst,
        json={"region_id": rid},
    )

    assert investigation.status_code == 201, investigation.text

    iid = investigation.json()["id"]

    # Assign the officer.
    assigned = client.put(
        f"/api/v1/investigations/{iid}/assign",
        headers=analyst,
        json={"assigned_to_id": officer_id},
    )

    assert assigned.status_code == 200, assigned.text
    assert assigned.json()["assigned_to_id"] == officer_id

    # Officer retrieves the assigned investigation.
    response = client.get(
        f"/api/v1/investigations/{iid}",
        headers=officer,
    )

    assert response.status_code == 200

    # Officer starts and submits the investigation.
    for status in ("in_progress", "submitted"):
        response = client.put(
            f"/api/v1/investigations/{iid}/status",
            headers=officer,
            json={"status": status},
        )

        assert response.status_code == 200, response.text
        assert response.json()["status"] == status

    # Record a synthetic human decision for testing only.
    decision = client.post(
        f"/api/v1/investigations/{iid}/decision",
        headers=analyst,
        json={
            "decision": "confirmed",
            "rationale": (
                "Synthetic image change confirmed "
                "during automated workflow testing."
            ),
        },
    )

    assert decision.status_code == 201, decision.text
    assert decision.json()["reviewer_id"] == analyst_id

    # Download the consolidated report.
    report = client.get(
        f"/api/v1/analyses/{aid}/report?download=true",
        headers=analyst,
    )

    assert report.status_code == 200, report.text
    assert "attachment" in report.headers["content-disposition"]

    data = report.json()

    assert data["project"]["id"] == pid
    assert data["analysis"]["id"] == aid
    assert data["analysis"]["status"] == "completed"
    assert data["summary"]["candidate_regions"] > 0
    assert data["summary"]["investigations"] == 1
    assert data["summary"]["reviewed_investigations"] == 1
    assert data["summary"]["confirmed_decisions"] == 1

    assert data["investigations"][0]["status"] == "reviewed"
    assert data["decisions"][0]["reviewer_id"] == analyst_id

    # Verify that unrelated users cannot access the report.
    _, unrelated = create_role_account("analyst")

    denied = client.get(
        f"/api/v1/analyses/{aid}/report",
        headers=unrelated,
    )

    assert denied.status_code == 404

    # Verify authentication is required.
    assert client.get(
        f"/api/v1/analyses/{aid}/report"
    ).status_code == 401


# Additional JWT security regression tests

def test_token_without_expiration_is_rejected():
    _, _, valid_token = create_test_account()

    profile = client.get(
        "/api/v1/auth/me",
        headers={
            "Authorization": f"Bearer {valid_token}"
        },
    )

    assert profile.status_code == 200

    settings = get_settings()

    token = jwt.encode(
        {"sub": profile.json()["id"]},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


def test_token_without_subject_is_rejected():
    settings = get_settings()

    token = jwt.encode(
        {
            "exp": datetime.now(timezone.utc)
                   + timedelta(minutes=5)
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


def test_token_with_empty_subject_is_rejected():
    settings = get_settings()

    token = jwt.encode(
        {
            "sub": "",
            "exp": datetime.now(timezone.utc)
                   + timedelta(minutes=5)
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
