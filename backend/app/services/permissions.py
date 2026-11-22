
from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models import Project, ProjectAccess, User


def require_project_access(
    db: Session,
    project_id: str,
    user: User,
    write: bool = False,
) -> Project:

    project = db.get(Project, project_id)

    if project is None:
        raise HTTPException(404, "Project not found")

    if user.role not in ("admin", "analyst", "officer"):
        raise HTTPException(403, "Permission denied")

    if user.role != "admin":

        has_access = (
            project.owner_id == user.id
            or db.scalar(
                select(ProjectAccess.id).where(
                    ProjectAccess.project_id == project_id,
                    ProjectAccess.user_id == user.id,
                )
            ) is not None
        )

        if not has_access:
            raise HTTPException(404, "Project not found")

    if write and user.role not in ("admin", "analyst"):
        raise HTTPException(403, "Write permission denied")

    return project


def lookup_eligible_user(db, project_id, user_id):

    if db.get_bind().dialect.name == "postgresql":
        return db.execute(
            text(
                "SELECT * FROM sentinel_security.eligible_user("
                ":pid, :uid)"
            ),
            {"pid": project_id, "uid": user_id},
        ).one_or_none()

    return db.execute(
        select(User.id, User.role, User.active).where(
            User.id == user_id
        )
    ).one_or_none()
