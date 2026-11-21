
from alembic import context

from app.core.config import get_settings
from app.core.database import Base, build_database_engine

# Register all database models
import app.models


config = context.config
settings = get_settings()

target_metadata = Base.metadata


def run_migrations_offline():
    """Generate migrations without connecting to the database."""

    context.configure(
        url=settings.get_migration_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations using the SSL-configured database engine."""

    migration_engine = build_database_engine(
        settings.get_migration_url()
    )

    try:
        with migration_engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
            )

            with context.begin_transaction():
                context.run_migrations()
    finally:
        migration_engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
