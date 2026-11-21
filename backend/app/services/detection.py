
import io
import sys
from pathlib import Path

from fastapi import HTTPException
from PIL import Image
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal

from app.api.v1.imagery import (
    get_storage_root,
    MAX_UPLOAD_BYTES,
    MAX_IMAGE_PIXELS,
)


class DetectionParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        allow_inf_nan=False,
    )

    threshold: float = Field(
        default=0.15, gt=0, le=1
    )

    min_region_area: float = Field(
        default=50, ge=1
    )

    max_size: Literal[512, 768, 1024] = 1024


def load_stored_image(imagery):

    metadata = imagery.metadata_json or {}

    if metadata.get("storage_status") != "stored":
        raise HTTPException(
            409, "Actual image file has not been uploaded"
        )

    extension = Path(imagery.filename).suffix.lower()

    if extension not in (".jpg", ".jpeg", ".png"):
        raise HTTPException(
            415,
            "This detection endpoint currently supports JPG and PNG. "
            "GeoTIFF preprocessing is not yet integrated.",
        )

    expected_key = (
        f"projects/{imagery.project_id}/imagery/"
        f"{imagery.id}{extension}"
    )

    if imagery.storage_key != expected_key:
        raise HTTPException(
            409, "Invalid imagery storage reference"
        )

    root = get_storage_root()
    path = (root / expected_key).resolve()

    if not path.is_relative_to(root):
        raise HTTPException(409, "Invalid storage location")

    try:
        with path.open("rb") as handle:
            data = handle.read(MAX_UPLOAD_BYTES + 1)
    except OSError:
        raise HTTPException(409, "Stored image is unavailable")

    if not data or len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(409, "Invalid stored image size")

    try:
        with Image.open(io.BytesIO(data)) as image:

            expected_format = (
                "PNG" if extension == ".png" else "JPEG"
            )

            if image.format != expected_format:
                raise HTTPException(
                    409, "Stored image format mismatch"
                )

            if image.width * image.height > MAX_IMAGE_PIXELS:
                raise HTTPException(
                    413, "Image dimensions exceed limit"
                )

            if getattr(image, "n_frames", 1) != 1:
                raise HTTPException(
                    415, "Multiple frames are unsupported"
                )

            return image.convert("RGB")

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(400, "Stored image cannot be decoded")


def execute_detection(before, after, parameters):

    repo_root = Path(__file__).resolve().parents[3]

    if not (
        repo_root / "utils" / "change_detection.py"
    ).is_file():
        raise HTTPException(
            503, "Detection engine is unavailable"
        )

    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    try:
        import numpy as np
        from utils.change_detection import detect_changes
    except (ImportError, OSError):
        raise HTTPException(
            503, "Detection dependencies are unavailable"
        )

    before_image = load_stored_image(before)
    after_image = load_stored_image(after)

    if before_image.size != after_image.size:
        raise HTTPException(
            422,
            "Images must have identical dimensions "
            "before comparison",
        )

    width, height = before_image.size

    scale = min(
        1.0,
        parameters.max_size / max(width, height),
    )

    size = (
        max(1, round(width * scale)),
        max(1, round(height * scale)),
    )

    if size != before_image.size:
        before_image = before_image.resize(
            size, Image.Resampling.BILINEAR
        )
        after_image = after_image.resize(
            size, Image.Resampling.BILINEAR
        )

    _, _, regions, stats = detect_changes(
        np.asarray(before_image),
        np.asarray(after_image),
        threshold=parameters.threshold,
        min_region_area=parameters.min_region_area,
    )

    result = {
        "engine": "classical_rgb_change_detection",
        "stats": stats,
        "original_size": {
            "width": width,
            "height": height,
        },
        "processed_size": {
            "width": size[0],
            "height": size[1],
        },
        "coordinate_space": "processed_image_pixels",
        "geo_note": (
            "Geographic coordinates are unavailable. "
            "No coordinates or square-metre areas were invented."
        ),
        "alignment_note": (
            "Automatic alignment was not performed. "
            "Inputs must already represent the same aligned scene."
        ),
        "disclaimer": (
            "Candidate visual differences require human review."
        ),
    }

    return result, regions
