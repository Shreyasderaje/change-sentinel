"""Authorization and relationship-integrity checks for investigation chat."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Analysis, CandidateRegion, Imagery, Investigation, Project, ProjectAccess, User


# AnalystDecision.decision is a free-form String in the current schema. There
# are no decision values or write paths in this repository defining approval
# semantics. Keep this empty until the product owners define that contract.
SUPPORTED_VERIFIED_DECISIONS: frozenset[str] = frozenset()


def _analyst_can_access_project(db: Session, project_id: str, user_id: str) -> bool:
    owner_id = db.scalar(select(Project.owner_id).where(Project.id == project_id))
    if owner_id is None:
        return False
    if owner_id == user_id:
        return True
    return (
        db.scalar(
            select(ProjectAccess.id).where(
                ProjectAccess.project_id == project_id,
                ProjectAccess.user_id == user_id,
            )
        )
        is not None
    )


def get_investigation_context(
    db: Session, project_id: str, investigation_id: str, user: User
) -> dict[str, Any] | None:
    """Authorize first, then ensure all linked records remain in one project.

    Returns an insufficient, unverified context for consistent investigation
    data because this repository defines no approved decision vocabulary.
    No arbitrary persisted text, JSON blobs, or geometry is returned to the
    caller or supplied to the model until that verification contract exists.
    None means not found, unauthorized, or inconsistent linkage.
    """
    if user.role == "analyst":
        if not _analyst_can_access_project(db, project_id, user.id):
            return None
    elif user.role not in {"officer", "admin"}:
        return None

    # Read only the fields needed to establish scope/assignment. Do not load the
    # rest of the investigation until the authenticated principal is authorized.
    summary = db.execute(
        select(Investigation.project_id, Investigation.assigned_to_id).where(
            Investigation.id == investigation_id
        )
    ).one_or_none()
    if summary is None or summary.project_id != project_id:
        return None
    if user.role == "officer" and summary.assigned_to_id != user.id:
        return None

    investigation = db.get(Investigation, investigation_id)
    if investigation is None or investigation.project_id != project_id:
        return None

    region = db.get(CandidateRegion, investigation.region_id)
    if region is None or not region.analysis_id:
        return None

    # CandidateRegion's analysis_id is its sole relationship to Analysis.
    # Resolve that exact FK and require its tenant to match the investigation.
    analysis = db.get(Analysis, region.analysis_id)
    if (
        analysis is None
        or analysis.id != region.analysis_id
        or analysis.project_id != investigation.project_id
    ):
        return None

    for imagery_id in (analysis.before_imagery_id, analysis.after_imagery_id):
        if imagery_id is None:
            continue
        imagery = db.get(Imagery, imagery_id)
        if imagery is None or imagery.project_id != analysis.project_id:
            return None

    # Do not infer approval from populated results, geometry, a completed
    # analysis, or a free-form decision string. There is no supported decision
    # vocabulary yet, so all records remain unverified and no model call is safe.
    return {
        "sufficient": False,
        "verification_status": "unverified",
        "reason": "No supported analyst verification decision is recorded.",
    }
