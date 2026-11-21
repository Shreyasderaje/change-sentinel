
from alembic import context

from app.core.config import get_settings
from app.core.database import Base, engine

# Register all database models
import app.models


config = context.config
settings = get_settings()

target_metadata = Base.metadata


def run_migrations_offline():
    """Generate migrations without connecting to the database."""

    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations using the SSL-configured database engine."""

    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
