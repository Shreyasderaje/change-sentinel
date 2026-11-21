
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Response,
)

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import current_user

from app.models.entities import (
    ProjectAccess,
    Investigation,
    User,
)

from app.schemas.member import (
    MemberCreate,
    MemberOut,
)

from app.api.v1.investigations import require_manager


router = APIRouter(tags=["members"])


@router.post(
    "/projects/{project_id}/members",
    response_model=MemberOut,
    status_code=201,
)
def add_member(
    project_id: str,
    payload: MemberCreate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):

    project = require_manager(
        db, project_id, user
    )

    if payload.user_id == project.owner_id:
        raise HTTPException(
            409, "Project owner already has access"
        )

    member = db.execute(
        select(User.id, User.role, User.active).where(
            User.id == payload.user_id
        )
    ).one_or_none()

    if (
        member is None
        or not member.active
        or member.role not in ("analyst", "officer")
    ):
        raise HTTPException(
            404, "Eligible user not found"
        )

    existing = db.scalar(
        select(ProjectAccess).where(
            ProjectAccess.project_id == project_id,
            ProjectAccess.user_id == member.id,
        )
    )

    if existing is not None:
        raise HTTPException(
            409, "User is already a project member"
        )

    membership = ProjectAccess(
        project_id=project_id,
        user_id=member.id,
    )

    try:
        db.add(membership)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            409, "Membership conflicts with existing records"
        )

    db.refresh(membership)

    return membership


@router.get(
    "/projects/{project_id}/members",
    response_model=list[MemberOut],
)
def list_members(
    project_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):

    require_manager(db, project_id, user)

    query = (
        select(ProjectAccess)
        .where(
            ProjectAccess.project_id == project_id
        )
        .order_by(ProjectAccess.id)
        .offset(offset)
        .limit(limit)
    )

    return db.scalars(query).all()


@router.delete(
    "/projects/{project_id}/members/{member_id}",
    status_code=204,
)
def remove_member(
    project_id: str,
    member_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):

    project = require_manager(
        db, project_id, user
    )

    if member_id == project.owner_id:
        raise HTTPException(
            409, "Cannot remove the project owner"
        )

    membership = db.scalar(
        select(ProjectAccess).where(
            ProjectAccess.project_id == project_id,
            ProjectAccess.user_id == member_id,
        ).with_for_update()
    )

    if membership is None:
        raise HTTPException(
            404, "Membership not found"
        )

    assigned = db.scalar(
        select(Investigation.id)
        .where(
            Investigation.project_id == project_id,
            Investigation.assigned_to_id == member_id,
        )
        .limit(1)
    )

    if assigned is not None:
        raise HTTPException(
            409,
            "Cannot remove a member with assigned investigations",
        )

    db.delete(membership)
    db.commit()

    return Response(status_code=204)
