
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import current_user

from app.models.entities import (
    Imagery,
    CandidateRegion,
    Investigation,
    AnalystDecision,
    User,
)

from app.schemas.analysis import (
    AnalysisOut,
    CandidateRegionOut,
)

from app.schemas.investigation import InvestigationOut
from app.schemas.decision import DecisionOut

from app.api.v1.analyses import require_analysis_access
from app.api.v1.investigations import require_manager


router = APIRouter(tags=["reports"])


@router.get("/analyses/{analysis_id}/report")
def generate_report(
    analysis_id: str,
    download: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):

    analysis = require_analysis_access(
        analysis_id, db, user
    )

    project = require_manager(
        db, analysis.project_id, user
    )

    if analysis.status != "completed":
        raise HTTPException(
            409,
            "Analysis must be completed before reporting",
        )

    imagery = db.scalars(
        select(Imagery).where(
            Imagery.project_id == project.id,
            Imagery.id.in_([
                analysis.before_imagery_id,
                analysis.after_imagery_id,
            ]),
        )
    ).all()

    imagery_data = {
        row.id: {
            "id": row.id,
            "filename": row.filename,
            "acquisition_date": row.acquisition_date,
            "crs": row.crs,
        }
        for row in imagery
    }

    regions = db.scalars(
        select(CandidateRegion)
        .where(
            CandidateRegion.analysis_id == analysis.id
        )
        .order_by(CandidateRegion.id)
    ).all()

    investigations = db.scalars(
        select(Investigation)
        .join(
            CandidateRegion,
            Investigation.region_id == CandidateRegion.id,
        )
        .where(
            CandidateRegion.analysis_id == analysis.id,
            Investigation.project_id == project.id,
        )
        .order_by(Investigation.id)
    ).all()

    decisions = db.scalars(
        select(AnalystDecision)
        .join(
            Investigation,
            AnalystDecision.investigation_id == Investigation.id,
        )
        .join(
            CandidateRegion,
            Investigation.region_id == CandidateRegion.id,
        )
        .where(
            Investigation.project_id == project.id,
            CandidateRegion.analysis_id == analysis.id,
        )
        .order_by(AnalystDecision.created_at)
    ).all()

    report = {
        "report_type": "change_detection",
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc),
        "generated_by": user.id,

        "project": {
            "id": project.id,
            "name": project.name,
            "description": project.description,
        },

        "analysis": AnalysisOut.model_validate(
            analysis
        ).model_dump(),

        "imagery": {
            "before": imagery_data.get(
                analysis.before_imagery_id
            ),
            "after": imagery_data.get(
                analysis.after_imagery_id
            ),
        },

        "summary": {
            "candidate_regions": len(regions),
            "investigations": len(investigations),
            "reviewed_investigations": sum(
                row.status == "reviewed"
                for row in investigations
            ),
            "confirmed_decisions": sum(
                row.decision == "confirmed"
                for row in decisions
            ),
            "rejected_decisions": sum(
                row.decision == "rejected"
                for row in decisions
            ),
            "inconclusive_decisions": sum(
                row.decision == "inconclusive"
                for row in decisions
            ),
        },

        "regions": [
            CandidateRegionOut.model_validate(
                row
            ).model_dump()
            for row in regions
        ],

        "investigations": [
            InvestigationOut.model_validate(
                row
            ).model_dump()
            for row in investigations
        ],

        "decisions": [
            DecisionOut.model_validate(
                row
            ).model_dump()
            for row in decisions
        ],

        "limitations": [
            "Candidate regions indicate potential changes.",
            "Analyst decisions are human assessments.",
            "Missing geographic metadata remains null.",
            "Field evidence attachments are not included.",
        ],
    }

    headers = {
        "Cache-Control": "no-store",
    }

    if download:
        headers["Content-Disposition"] = (
            'attachment; filename="change-sentinel-report.json"'
        )

    return JSONResponse(
        content=jsonable_encoder(report),
        headers=headers,
    )
