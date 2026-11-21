
"""Secure application database tables."""

from alembic import op
from sqlalchemy import text


revision = "0002_database_security"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


TABLES = (
    "users",
    "projects",
    "project_access",
    "imagery",
    "analyses",
    "candidate_regions",
    "investigations",
    "analyst_decisions",
    "reports",
    "alembic_version",
)


def upgrade():
    bind = op.get_bind()

    if bind.dialect.name != "postgresql":
        return

    for table in TABLES:
        op.execute(
            f"ALTER TABLE public.{table} "
            "ENABLE ROW LEVEL SECURITY"
        )

        op.execute(
            f"REVOKE ALL PRIVILEGES ON TABLE "
            f"public.{table} FROM PUBLIC"
        )

    for role in ("anon", "authenticated"):
        exists = bind.execute(
            text(
                "SELECT EXISTS ("
                "SELECT 1 FROM pg_roles "
                "WHERE rolname = :role)"
            ),
            {"role": role},
        ).scalar()

        if exists:
            for table in TABLES:
                op.execute(
                    f"REVOKE ALL PRIVILEGES ON TABLE "
                    f"public.{table} FROM {role}"
                )


def downgrade():
    raise RuntimeError(
        "Automatic reversal of database security "
        "is disabled. An authorized manual review "
        "is required."
    )
