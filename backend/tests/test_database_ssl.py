import ssl

from app.core.database_config import build_connect_args


def test_local_postgresql_ssl_disabled_omits_ssl_context():
    assert build_connect_args("postgresql+pg8000://user:pass@db/test", False) == {}


def test_postgresql_ssl_enabled_uses_verified_context():
    args = build_connect_args("postgresql+pg8000://user:pass@db/test", True)

    context = args["ssl_context"]
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True


def test_postgresql_ssl_uses_optional_ca_file(monkeypatch):
    observed = {}
    secure_context = ssl.create_default_context()

    def capture_default_context(*, cafile=None):
        observed["cafile"] = cafile
        return secure_context

    monkeypatch.setattr("app.core.database_config.ssl.create_default_context", capture_default_context)

    args = build_connect_args(
        "postgresql+pg8000://user:pass@remote/test",
        True,
        "/run/secrets/postgres-ca.pem",
    )

    assert observed["cafile"] == "/run/secrets/postgres-ca.pem"
    assert args["ssl_context"] is secure_context


def test_sqlite_connection_arguments_are_unchanged():
    assert build_connect_args("sqlite:///./dev.db", True) == {
        "check_same_thread": False
    }


def test_test_environment_is_ready_before_application_settings_load():
    from app.core.config import get_settings

    settings = get_settings()

    assert settings.database_url == "sqlite://"
    assert settings.environment == "development"
    assert settings.sarvam_api_key.get_secret_value() == "test-only-dummy-sarvam-key"
