from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, or_
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import current_user
from app.models import Project, ProjectAccess, User
from app.schemas.project import ProjectCreate, ProjectOut
router = APIRouter(prefix='/projects', tags=['projects'])

@router.post('', response_model=ProjectOut, status_code=201)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if user.role not in ('analyst', 'admin'):
        raise HTTPException(403, 'Only analysts can create projects')
    project = Project(name=payload.name, description=payload.description, owner_id=user.id)
    db.add(project); db.commit(); db.refresh(project)
    return project

@router.get('', response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db), user: User = Depends(current_user)):
    allowed = select(ProjectAccess.project_id).where(ProjectAccess.user_id == user.id)
    query = select(Project) if user.role == 'admin' else select(Project).where(or_(Project.owner_id == user.id, Project.id.in_(allowed)))
    return db.scalars(query).all()

@router.get('/{project_id}', response_model=ProjectOut)
def get_project(project_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    project = db.get(Project, project_id)
    if project is None: raise HTTPException(404, 'Project not found')
    authorized = user.role == 'admin' or project.owner_id == user.id or db.scalar(select(ProjectAccess.id).where(ProjectAccess.project_id == project_id, ProjectAccess.user_id == user.id)) is not None
    if not authorized: raise HTTPException(404, 'Project not found')
    return project


from app.schemas.project import ProjectUpdate
from app.models.entities import Imagery, Analysis, Investigation
from sqlalchemy.exc import IntegrityError
from fastapi import Response


def _require_project_write(project_id, db, user):
    if user.role not in ("analyst", "admin"):
        raise HTTPException(403, "Insufficient permissions")

    project = db.get(Project, project_id)

    if project is None:
        raise HTTPException(404, "Project not found")

    if user.role != "admin" and project.owner_id != user.id:
        raise HTTPException(404, "Project not found")

    return project


@router.put("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: str,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    project = _require_project_write(project_id, db, user)

    if not payload.name.strip():
        raise HTTPException(422, "Project name cannot be blank")

    project.name = payload.name.strip()
    project.description = payload.description

    db.commit()
    db.refresh(project)

    return project


@router.delete("/{project_id}", status_code=204)
def delete_project(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    project = _require_project_write(project_id, db, user)

    for model in (
        ProjectAccess,
        Imagery,
        Analysis,
        Investigation,
    ):
        dependent = db.scalar(
            select(model.id)
            .where(model.project_id == project_id)
            .limit(1)
        )

        if dependent is not None:
            raise HTTPException(
                409,
                "Cannot delete project with dependent records",
            )

    try:
        db.delete(project)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            409,
            "Project deletion conflicts with existing records",
        )

    return Response(status_code=204)
