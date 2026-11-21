
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class InvestigationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    region_id: str = Field(min_length=1, max_length=36)


class InvestigationAssign(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assigned_to_id: str = Field(min_length=1, max_length=36)


class InvestigationStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["in_progress", "submitted"]


class InvestigationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    region_id: str
    assigned_to_id: str | None
    status: str
    created_at: datetime
