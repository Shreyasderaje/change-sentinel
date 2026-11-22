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

