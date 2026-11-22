import os
import sys
import secrets
import importlib.util
from pathlib import Path
from getpass import getpass
from sqlalchemy import URL, create_engine, text

sys.path.insert(0, str(Path.cwd().parent))
sys.path.insert(0, str(Path.cwd()))

path = Path(
    "migrations/versions/0003_tenant_isolation.py"
)

spec = importlib.util.spec_from_file_location(
    "migration", path
)

migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)

for name in (
    "install_read_policies",
    "install_auth_functions",
    "install_write_policies",
):
    if not hasattr(migration, name):
        raise SystemExit("Missing implementation: " + name)

password = getpass("Local PostgreSQL password: ")

suffix = secrets.token_hex(6)
dbname = "sentinel_api_" + suffix
login = "sentinel_login_" + suffix
login_password = secrets.token_hex(32)

def url(user, pw, database):
    return URL.create(
        "postgresql+pg8000",
        username=user,
        password=pw,
        host="127.0.0.1",
        port=5432,
        database=database,
    )

control = create_engine(
    url("postgres", password, "sentinel_rls_test"),
    connect_args={"ssl_context": False},
    isolation_level="AUTOCOMMIT",
    hide_parameters=True,
)

created_db = False
created_login = False
admin = None
runtime = None

try:
    with control.connect() as conn:
        identity = conn.execute(text(
            "SELECT current_database(), current_user, "
            "host(inet_server_addr())"
        )).one()

        assert tuple(identity) == (
            "sentinel_rls_test",
            "postgres",
            "127.0.0.1",
        )

        flags = conn.execute(text("""
            SELECT rolcanlogin, rolsuper, rolbypassrls,
                   rolcreatedb, rolcreaterole,
                   rolinherit, rolreplication
            FROM pg_roles
            WHERE rolname='sentinel_app'
        """)).one()

        assert not any(flags)

        conn.exec_driver_sql(
            f"CREATE DATABASE {dbname} TEMPLATE template0"
        )

        created_db = True

        conn.exec_driver_sql(
            f"CREATE ROLE {login} LOGIN INHERIT "
            "NOSUPERUSER NOBYPASSRLS NOCREATEDB "
            "NOCREATEROLE NOREPLICATION "
            f"PASSWORD '{login_password}'"
        )

        created_login = True

        conn.exec_driver_sql(
            f"GRANT sentinel_app TO {login}"
        )

    print("PASS: Restricted database login created")

    os.environ.update({
        "DATABASE_URL": url(
            login, login_password, dbname
        ).render_as_string(hide_password=False),
        "ENVIRONMENT": "development",
        "DB_SSL_MODE": "disable",
        "JWT_SECRET": secrets.token_urlsafe(48),
        "SARVAM_API_KEY": "",
    })

    from app.core.database import Base, engine as runtime
    from app.core.security import hash_password
    import app.models
    from app.main import app
    from fastapi.testclient import TestClient

    admin = create_engine(
        url("postgres", password, dbname),
        connect_args={"ssl_context": False},
        hide_parameters=True,
    )

    with admin.begin() as conn:
        assert conn.scalar(text(
            "SELECT current_database()"
        )) == dbname

        Base.metadata.create_all(conn)

        migration.install_read_policies(conn)
        migration.install_auth_functions(conn)
        migration.install_write_policies(conn)

        for uid in ("analyst-a", "analyst-b"):
            conn.execute(
                Base.metadata.tables["users"].insert(),
                {
                    "id": uid,
                    "email": uid + "@example.org",
                    "password_hash": hash_password(
                        "synthetic-test-password"
                    ),
                    "role": "analyst",
                    "active": True,
                },
            )

    print("PASS: All policy installers executed")

    with runtime.connect() as conn:
        flags = conn.execute(text("""
            SELECT current_user, rolsuper,
                   rolbypassrls,
                   pg_has_role(
                       current_user,'sentinel_app','USAGE'
                   )
            FROM pg_roles
            WHERE rolname=current_user
        """)).one()

        assert tuple(flags) == (
            login, False, False, True
        )

    print("PASS: Runtime login restrictions verified")

    from tempfile import TemporaryDirectory

    with TemporaryDirectory(prefix="sentinel-test-") as storage, TestClient(app) as client:

        os.environ["SENTINEL_STORAGE_ROOT"] = storage

        def request(method, endpoint, expected,
                    token=None, **kwargs):

            headers = (
                {"Authorization": "Bearer " + token}
                if token else {}
            )

            response = client.request(
                method,
                "/api/v1" + endpoint,
                headers=headers,
                **kwargs,
            )

            assert response.status_code == expected, (
                method, endpoint, response.status_code
            )

            print("PASS:", method, endpoint, expected)

            return (
                response.json()
                if response.content else None
            )

        def authenticate(uid):
            return request(
                "POST", "/auth/login", 200,
                json={
                    "email": uid + "@example.org",
                    "password": "synthetic-test-password",
                },
            )["access_token"]

        a = authenticate("analyst-a")
        b = authenticate("analyst-b")

        officer = request(
            "POST", "/auth/register", 201,
            json={
                "email": "officer@example.org",
                "password": "synthetic-test-password",
            },
        )["access_token"]

        profile = request(
            "GET", "/auth/me", 200, officer
        )

        assert profile["role"] == "officer"

        request("GET", "/projects", 401)

        request(
            "POST", "/projects", 403, officer,
            json={"name": "Forbidden"},
        )

        project = request(
            "POST", "/projects", 201, a,
            json={"name": "Security test project"},
        )

        pid = project["id"]

        request("GET", "/projects/" + pid, 404, b)

        request(
            "PUT", "/projects/" + pid, 200, a,
            json={"name": "Updated project"},
        )

        request(
            "POST", "/projects/" + pid + "/members",
            201, a,
            json={"user_id": profile["id"]},
        )

        request(
            "GET", "/projects/" + pid, 200, officer
        )


        import io
        from PIL import Image, ImageDraw
        from sqlalchemy.exc import DBAPIError

        def image_bytes(changed=False):
            image = Image.new("RGB", (128, 128), "black")

            if changed:
                ImageDraw.Draw(image).rectangle(
                    (25, 25, 100, 100),
                    fill="white",
                )

            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            return buffer.getvalue()

        imagery_url = "/projects/" + pid + "/imagery/upload"

        before = request(
            "POST", imagery_url, 201, a,
            files={
                "file": (
                    "before.png",
                    image_bytes(),
                    "image/png",
                )
            },
        )

        after = request(
            "POST", imagery_url, 201, a,
            files={
                "file": (
                    "after.png",
                    image_bytes(True),
                    "image/png",
                )
            },
        )

        analysis = request(
            "POST",
            "/projects/" + pid + "/analyses",
            201, a,
            json={
                "before_imagery_id": before["id"],
                "after_imagery_id": after["id"],
            },
        )

        aid = analysis["id"]

        analysis = request(
            "POST", "/analyses/" + aid + "/run",
            200, a,
        )

        assert analysis["status"] == "completed"

        regions = request(
            "GET", "/analyses/" + aid + "/regions",
            200, a,
        )

        assert len(regions) > 0

        request(
            "GET", "/analyses/" + aid,
            404, b,
        )

        investigation = request(
            "POST",
            "/projects/" + pid + "/investigations",
            201, a,
            json={"region_id": regions[0]["id"]},
        )

        iid = investigation["id"]
        endpoint = "/investigations/" + iid

        request("GET", endpoint, 404, officer)

        request(
            "PUT", endpoint + "/assign",
            200, a,
            json={"assigned_to_id": profile["id"]},
        )

        request("GET", endpoint, 200, officer)
        request("GET", endpoint, 404, b)

        request(
            "PUT", endpoint + "/status",
            409, officer,
            json={"status": "submitted"},
        )

        request(
            "PUT", endpoint + "/status",
            200, officer,
            json={"status": "in_progress"},
        )

        request(
            "PUT", endpoint + "/status",
            200, officer,
            json={"status": "submitted"},
        )

        try:
            with runtime.begin() as conn:
                conn.execute(text(
                    "SELECT set_config("
                    "'sentinel.user_id', 'analyst-a', true)"
                ))

                result = conn.execute(text("""
                    UPDATE public.investigations
                    SET status = 'reviewed'
                    WHERE id = :iid
                """), {"iid": iid})

                assert result.rowcount == 1

        except DBAPIError as exc:
            error = exc.orig.args[0]
            assert isinstance(error, dict)
            assert error.get("C") == "23514"

            print("PASS: Review without decision blocked")
        else:
            raise AssertionError(
                "Review without decision was allowed"
            )

        request(
            "POST", endpoint + "/decision",
            403, officer,
            json={
                "decision": "confirmed",
                "rationale": "Unauthorized review",
            },
        )

        request(
            "POST", endpoint + "/decision",
            201, a,
            json={
                "decision": "confirmed",
                "rationale": "Synthetic test verification",
            },
        )

        reviewed = request(
            "GET", endpoint, 200, a
        )

        assert reviewed["status"] == "reviewed"

        request(
            "POST", endpoint + "/decision",
            409, a,
            json={
                "decision": "confirmed",
                "rationale": "Duplicate review",
            },
        )

        report = request(
            "GET", "/analyses/" + aid + "/report",
            200, a,
        )

        assert report["summary"]["confirmed_decisions"] == 1

        request(
            "GET", "/analyses/" + aid + "/report",
            404, b,
        )

        print("SUCCESS: Full PostgreSQL workflow passed")

    print("SUCCESS: Restricted PostgreSQL API smoke test passed")

finally:
    if runtime is not None:
        runtime.dispose()

    if admin is not None:
        admin.dispose()

    try:
        with control.connect() as conn:
            if created_db:
                conn.exec_driver_sql(
                    f"DROP DATABASE {dbname}"
                )

            if created_login:
                conn.exec_driver_sql(
                    f"DROP ROLE {login}"
                )

        print("Temporary database and login cleaned up")

    finally:
        control.dispose()
