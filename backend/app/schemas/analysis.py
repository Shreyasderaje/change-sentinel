
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class AnalysisCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    before_imagery_id: str = Field(min_length=1, max_length=36)
    after_imagery_id: str = Field(min_length=1, max_length=36)
    parameters_json: dict | None = None


class AnalysisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    before_imagery_id: str | None
    after_imagery_id: str | None
    status: str
    parameters_json: dict | None
    results_json: dict | None
    created_at: datetime


class CandidateRegionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    analysis_id: str
    region_label: str
    bbox_pixels: dict | None
    area_pixels: int | None
    area_m2: float | None
    geometry_geojson: dict | None
