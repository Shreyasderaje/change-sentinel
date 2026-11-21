
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import current_user

from app.models.entities import (
    Analysis,
    CandidateRegion,
    Investigation,
    ProjectAccess,
    User,
)

from app.services.permissions import require_project_access

from app.schemas.investigation import (
    InvestigationCreate,
    InvestigationAssign,
    InvestigationStatus,
    InvestigationOut,
)


router = APIRouter(tags=["investigations"])


def require_manager(db, project_id, user):

    project = require_project_access(
        db, project_id, user, write=True
    )

    if user.role != "admin" and project.owner_id != user.id:
        raise HTTPException(403, "Write permission denied")

    return project


def require_investigation(db, investigation_id, user, lock=False):

    query = select(Investigation).where(
        Investigation.id == investigation_id
    )

    if lock:
        query = query.with_for_update()

    investigation = db.scalar(query)

    if investigation is None:
        raise HTTPException(404, "Investigation not found")

    require_project_access(
        db, investigation.project_id, user
    )

    if user.role == "officer":
        if investigation.assigned_to_id != user.id:
            raise HTTPException(404, "Investigation not found")

    return investigation


@router.post(
    "/projects/{project_id}/investigations",
    response_model=InvestigationOut,
    status_code=201,
)
def create_investigation(
    project_id: str,
    payload: InvestigationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):

    require_manager(db, project_id, user)

    region = db.scalar(
        select(CandidateRegion)
        .join(
            Analysis,
            CandidateRegion.analysis_id == Analysis.id,
        )
        .where(
            CandidateRegion.id == payload.region_id,
            Analysis.project_id == project_id,
        )
    )

    if region is None:
        raise HTTPException(
            404, "Region not found in this project"
        )

    analysis = db.get(Analysis, region.analysis_id)

    if analysis.status != "completed":
        raise HTTPException(
            409, "Analysis must be completed first"
        )

    investigation = Investigation(
        project_id=project_id,
        region_id=region.id,
        assigned_to_id=None,
        status="open",
    )

    db.add(investigation)
    db.commit()
    db.refresh(investigation)

    return investigation


@router.get(
    "/projects/{project_id}/investigations",
    response_model=list[InvestigationOut],
)
def list_investigations(
    project_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):

    require_project_access(db, project_id, user)

    query = select(Investigation).where(
        Investigation.project_id == project_id
    )

    if user.role == "officer":
        query = query.where(
            Investigation.assigned_to_id == user.id
        )

    query = (
        query.order_by(
            Investigation.created_at.desc(),
            Investigation.id,
        )
        .offset(offset)
        .limit(limit)
    )

    return db.scalars(query).all()


@router.get(
    "/investigations/{investigation_id}",
    response_model=InvestigationOut,
)
def get_investigation(
    investigation_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):

    return require_investigation(
        db, investigation_id, user
    )


@router.put(
    "/investigations/{investigation_id}/assign",
    response_model=InvestigationOut,
)
def assign_investigation(
    investigation_id: str,
    payload: InvestigationAssign,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):

    if user.role not in ("admin", "analyst"):
        raise HTTPException(403, "Permission denied")

    investigation = require_investigation(
        db, investigation_id, user, lock=True
    )

    require_manager(
        db, investigation.project_id, user
    )

    if investigation.status != "open":
        raise HTTPException(
            409, "Only open investigations can be assigned"
        )

    officer = db.execute(
        select(User.id, User.role, User.active).where(
            User.id == payload.assigned_to_id
        )
    ).one_or_none()

    if officer is None or officer.role != "officer" or not officer.active:
        raise HTTPException(404, "Eligible officer not found")

    membership = db.scalar(
        select(ProjectAccess.id).where(
            ProjectAccess.project_id == investigation.project_id,
            ProjectAccess.user_id == officer.id,
        )
    )

    if membership is None:
        raise HTTPException(404, "Eligible officer not found")

    investigation.assigned_to_id = officer.id

    db.commit()
    db.refresh(investigation)

    return investigation


@router.put(
    "/investigations/{investigation_id}/status",
    response_model=InvestigationOut,
)
def update_investigation_status(
    investigation_id: str,
    payload: InvestigationStatus,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):

    investigation = require_investigation(
        db, investigation_id, user, lock=True
    )

    if user.role != "officer":
        raise HTTPException(403, "Permission denied")

    if investigation.assigned_to_id != user.id:
        raise HTTPException(403, "Permission denied")

    transitions = {
        "open": {"in_progress"},
        "in_progress": {"submitted"},
        "submitted": set(),
    }

    allowed = transitions.get(
        investigation.status, set()
    )

    if payload.status not in allowed:
        raise HTTPException(
            409, "Invalid investigation status transition"
        )

    investigation.status = payload.status

    db.commit()
    db.refresh(investigation)

    return investigation
