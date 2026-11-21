
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import current_user
from app.models.entities import (
    Analysis,
    CandidateRegion,
    Imagery,
    User,
)
from app.schemas.analysis import (
    AnalysisCreate,
    AnalysisOut,
    CandidateRegionOut,
)
from app.services.permissions import require_project_access


router = APIRouter(tags=["analyses"])


def require_analysis_access(
    analysis_id: str,
    db: Session,
    user: User,
) -> Analysis:

    analysis = db.get(Analysis, analysis_id)

    if analysis is None:
        raise HTTPException(404, "Analysis not found")

    require_project_access(
        db, analysis.project_id, user
    )

    return analysis


@router.post(
    "/projects/{project_id}/analyses",
    response_model=AnalysisOut,
    status_code=201,
)
def create_analysis(
    project_id: str,
    payload: AnalysisCreate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):

    project = require_project_access(
        db, project_id, user, write=True
    )

    if user.role != "admin" and project.owner_id != user.id:
        raise HTTPException(403, "Write permission denied")

    if payload.before_imagery_id == payload.after_imagery_id:
        raise HTTPException(
            422,
            "Before and after imagery must be different",
        )

    for imagery_id in (
        payload.before_imagery_id,
        payload.after_imagery_id,
    ):
        imagery = db.scalar(
            select(Imagery).where(
                Imagery.id == imagery_id,
                Imagery.project_id == project_id,
            )
        )

        if imagery is None:
            raise HTTPException(
                404,
                "Imagery not found in this project",
            )

    analysis = Analysis(
        project_id=project_id,
        before_imagery_id=payload.before_imagery_id,
        after_imagery_id=payload.after_imagery_id,
        status="pending",
        parameters_json=payload.parameters_json,
        results_json=None,
    )

    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    return analysis


@router.get(
    "/projects/{project_id}/analyses",
    response_model=list[AnalysisOut],
)
def list_analyses(
    project_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):

    require_project_access(db, project_id, user)

    query = (
        select(Analysis)
        .where(Analysis.project_id == project_id)
        .order_by(Analysis.created_at.desc(), Analysis.id)
        .offset(offset)
        .limit(limit)
    )

    return db.scalars(query).all()


@router.get(
    "/analyses/{analysis_id}",
    response_model=AnalysisOut,
)
def get_analysis(
    analysis_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):

    return require_analysis_access(
        analysis_id, db, user
    )


@router.get(
    "/analyses/{analysis_id}/regions",
    response_model=list[CandidateRegionOut],
)
def list_regions(
    analysis_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):

    require_analysis_access(analysis_id, db, user)

    query = (
        select(CandidateRegion)
        .where(
            CandidateRegion.analysis_id == analysis_id
        )
        .order_by(CandidateRegion.id)
        .offset(offset)
        .limit(limit)
    )

    return db.scalars(query).all()


@router.get(
    "/regions/{region_id}",
    response_model=CandidateRegionOut,
)
def get_region(
    region_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):

    region = db.get(CandidateRegion, region_id)

    if region is None:
        raise HTTPException(404, "Region not found")

    require_analysis_access(
        region.analysis_id, db, user
    )

    return region


from sqlalchemy import update
from pydantic import ValidationError

from app.services.detection import (
    DetectionParameters,
    execute_detection,
)


@router.post(
    "/analyses/{analysis_id}/run",
    response_model=AnalysisOut,
)
def run_analysis(
    analysis_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):

    analysis = require_analysis_access(
        analysis_id, db, user
    )

    project = require_project_access(
        db, analysis.project_id, user, write=True
    )

    if user.role != "admin" and project.owner_id != user.id:
        raise HTTPException(403, "Write permission denied")

    if analysis.status != "pending":
        raise HTTPException(
            409, "Only pending analyses can be executed"
        )

    before = db.get(
        Imagery, analysis.before_imagery_id
    )

    after = db.get(
        Imagery, analysis.after_imagery_id
    )

    if (
        before is None
        or after is None
        or before.id == after.id
        or before.project_id != project.id
        or after.project_id != project.id
    ):
        raise HTTPException(
            409, "Invalid analysis image pair"
        )

    try:
        parameters = DetectionParameters.model_validate(
            analysis.parameters_json or {}
        )
    except ValidationError:
        raise HTTPException(
            422, "Invalid detection parameters"
        )

    result, regions = execute_detection(
        before, after, parameters
    )

    try:
        changed = db.execute(
            update(Analysis)
            .where(
                Analysis.id == analysis_id,
                Analysis.project_id == project.id,
                Analysis.status == "pending",
            )
            .values(
                status="completed",
                results_json=result,
                parameters_json=parameters.model_dump(),
            )
            .execution_options(
                synchronize_session=False
            )
        )

        if changed.rowcount != 1:
            raise HTTPException(
                409, "Analysis has already been processed"
            )

        for index, region in enumerate(
            regions, start=1
        ):
            x, y, width, height = region["bbox_xywh"]

            db.add(CandidateRegion(
                analysis_id=analysis_id,
                region_label=f"Region {index}",
                bbox_pixels={
                    "x": int(x),
                    "y": int(y),
                    "width": int(width),
                    "height": int(height),
                },
                area_pixels=int(region["pixel_count"]),
                area_m2=None,
                geometry_geojson=None,
            ))

        db.commit()

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise HTTPException(
            500, "Unable to persist analysis results"
        )

    db.refresh(analysis)

    return analysis
