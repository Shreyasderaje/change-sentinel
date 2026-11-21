
from fastapi import HTTPException
from sqlalchemy import select
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
