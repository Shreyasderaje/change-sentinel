
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class DecisionCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    decision: Literal[
        "confirmed",
        "rejected",
        "inconclusive",
    ]

    rationale: str = Field(
        min_length=1,
        max_length=5000,
    )


class DecisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    investigation_id: str
    reviewer_id: str
    decision: str
    rationale: str | None
    created_at: datetime
