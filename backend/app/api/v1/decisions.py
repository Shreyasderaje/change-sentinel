
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import current_user

from app.models.entities import (
    AnalystDecision,
    User,
)

from app.api.v1.investigations import (
    require_investigation,
    require_manager,
)

from app.schemas.decision import (
    DecisionCreate,
    DecisionOut,
)


router = APIRouter(tags=["decisions"])


@router.post(
    "/investigations/{investigation_id}/decision",
    response_model=DecisionOut,
    status_code=201,
)
def create_decision(
    investigation_id: str,
    payload: DecisionCreate,
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

    if investigation.status != "submitted":
        raise HTTPException(
            409,
            "Investigation must be submitted for review",
        )

    existing = db.scalar(
        select(AnalystDecision.id)
        .where(
            AnalystDecision.investigation_id
            == investigation_id
        )
        .limit(1)
    )

    if existing is not None:
        raise HTTPException(
            409,
            "A decision already exists",
        )

    decision = AnalystDecision(
        investigation_id=investigation_id,
        reviewer_id=user.id,
        decision=payload.decision,
        rationale=payload.rationale,
    )

    db.add(decision)

    investigation.status = "reviewed"

    db.commit()
    db.refresh(decision)

    return decision


@router.get(
    "/investigations/{investigation_id}/decision",
    response_model=DecisionOut,
)
def get_decision(
    investigation_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):

    require_investigation(
        db, investigation_id, user
    )

    decision = db.scalar(
        select(AnalystDecision)
        .where(
            AnalystDecision.investigation_id
            == investigation_id
        )
        .order_by(
            AnalystDecision.created_at.desc(),
            AnalystDecision.id,
        )
        .limit(1)
    )

    if decision is None:
        raise HTTPException(
            404,
            "Decision not found",
        )

    return decision
