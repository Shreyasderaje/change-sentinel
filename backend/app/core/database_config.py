"""Pure database driver connection argument construction."""

import ssl


def build_connect_args(
    database_url: str,
    db_ssl_enabled: bool,
    db_ssl_ca_file: str | None = None,
) -> dict:
    """Build driver arguments while keeping PostgreSQL TLS verification enabled."""
    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}

    if database_url.startswith("postgresql+pg8000") and db_ssl_enabled:
        return {"ssl_context": ssl.create_default_context(cafile=db_ssl_ca_file)}

    return {}
