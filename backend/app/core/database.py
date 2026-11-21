import ssl

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def build_database_engine(url):
    settings = get_settings()
    parsed = make_url(url)
    connect_args = {}

    if parsed.get_backend_name() == "sqlite":
        if settings.environment != "development":
            raise RuntimeError("SQLite is development-only")

        connect_args["check_same_thread"] = False

    elif parsed.drivername == "postgresql+pg8000":
        if settings.db_ssl_mode == "disable":
            if (
                settings.environment != "development"
                or parsed.host not in (
                    "localhost", "127.0.0.1", "::1"
                )
                or parsed.query
            ):
                raise RuntimeError(
                    "Unsafe SSL configuration"
                )

            connect_args["ssl_context"] = False
        else:
            connect_args["ssl_context"] = (
                ssl.create_default_context(
                    cafile=settings.db_ssl_ca_file
                )
            )
    else:
        raise RuntimeError("Unsupported database driver")

    return create_engine(
        url,
        connect_args=connect_args,
        pool_pre_ping=True,
    )


settings = get_settings()

engine = build_database_engine(settings.database_url)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)



@event.listens_for(SessionLocal, "after_begin")
def apply_transaction_identity(
    session, transaction, connection
):
    if connection.dialect.name == "postgresql":
        connection.execute(
            text(
                "SELECT set_config("
                "'sentinel.user_id', :uid, true)"
            ),
            {"uid": session.info.get(
                "sentinel_user_id", ""
            )},
        )


def bind_user_identity(session, user_id):
    if not isinstance(user_id, str) or not user_id:
        raise ValueError("Invalid authenticated identity")

    existing = session.info.get("sentinel_user_id")

    if existing is not None and existing != user_id:
        raise RuntimeError(
            "Database session identity cannot change"
        )

    session.info["sentinel_user_id"] = user_id

    connection = session.connection()

    if connection.dialect.name == "postgresql":
        connection.execute(
            text(
                "SELECT set_config("
                "'sentinel.user_id', :uid, true)"
            ),
            {"uid": user_id},
        )


def get_db():
    with SessionLocal() as session:
        yield session
