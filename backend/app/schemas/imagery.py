
from datetime import datetime
from pathlib import PurePath

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


class ImageryCreate(BaseModel):

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    filename: str = Field(
        min_length=1,
        max_length=255,
    )

    acquisition_date: datetime | None = None

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, value: str) -> str:

        if (
            "/" in value
            or "\\" in value
            or ":" in value
            or any(ord(c) < 32 for c in value)
        ):
            raise ValueError("Invalid filename")

        allowed_extensions = {
            ".jpg",
            ".jpeg",
            ".png",
            ".tif",
            ".tiff",
        }

        if PurePath(value).suffix.lower() not in allowed_extensions:
            raise ValueError("Unsupported imagery format")

        return value


class ImageryOut(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    filename: str
    acquisition_date: datetime | None
    crs: str | None
