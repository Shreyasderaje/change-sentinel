"""FastAPI adapter for the existing Change Sentinel image pipeline."""

from __future__ import annotations

import base64
import io
import os
from datetime import datetime, timezone

import cv2
import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from utils import change_detection as cd
from utils import geospatial, image_processing as ip, report_generation as rg

MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_IMAGE_PIXELS = 40_000_000
ALLOWED_FORMATS = {"JPEG", "PNG", "TIFF"}
DEFAULT_MAX_SIZE = 1024

app = FastAPI(title="Change Sentinel API", version="1.0.0")
origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


def _read_upload(data: bytes, name: str) -> tuple[np.ndarray, str]:
    if not data:
        raise HTTPException(status_code=400, detail=f"{name} image is empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"{name} image exceeds the 20 MB limit.")
    try:
        # Decode the bytes rather than relying on user supplied filename or MIME type.
        from PIL import Image

        with Image.open(io.BytesIO(data)) as image:
            image_format = (image.format or "").upper()
            if image_format not in ALLOWED_FORMATS:
                raise HTTPException(status_code=415, detail=f"{name} must be a JPG, PNG, or TIFF image.")
            if image.width * image.height > MAX_IMAGE_PIXELS:
                raise HTTPException(status_code=413, detail=f"{name} image dimensions exceed the 40 megapixel limit.")
            image.verify()
        rgb = ip.load_rgb_image(io.BytesIO(data))
        ip.image_size(rgb)
    except HTTPException:
        raise
    except ip.ImageValidationError as exc:
        raise HTTPException(status_code=400, detail=f"{name}: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"{name} is not a valid supported image.") from exc
    return rgb, image_format


def _png_base64(rgb: np.ndarray) -> str:
    success, encoded = cv2.imencode(".png", cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    if not success:
        raise RuntimeError("Could not encode analysis preview.")
    return base64.b64encode(encoded.tobytes()).decode("ascii")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze")
async def analyze(
    before: UploadFile = File(...),
    after: UploadFile = File(...),
    before_label: str = Form(""),
    after_label: str = Form(""),
    threshold: float = Form(0.15),
    min_region_area: float = Form(50),
    max_size: int = Form(DEFAULT_MAX_SIZE),
    attempt_alignment: bool = Form(False),
):
    if not 0 <= threshold <= 1:
        raise HTTPException(status_code=422, detail="threshold must be between 0 and 1.")
    if min_region_area < 0:
        raise HTTPException(status_code=422, detail="min_region_area must be zero or greater.")
    if max_size not in {512, 768, 1024, 1536, 2048}:
        raise HTTPException(status_code=422, detail="max_size must be one of 512, 768, 1024, 1536, or 2048.")
    before_bytes, after_bytes = await before.read(MAX_UPLOAD_BYTES + 1), await after.read(MAX_UPLOAD_BYTES + 1)
    before_raw, before_format = _read_upload(before_bytes, "Before")
    after_raw, _ = _read_upload(after_bytes, "After")
    warnings = ip.compare_dimensions(before_raw, after_raw)
    try:
        before_rgb, after_rgb = ip.prepare_pair(before_raw, after_raw, max_size=max_size)
    except ip.ImageValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    geo_note = (
        "No geographic metadata is available for these inputs. All coordinates are image pixel coordinates (origin: top-left). "
        "No latitude/longitude values have been invented."
    )
    georef = None
    if before_format == "TIFF":
        georef, geo_note = geospatial.read_georeference(before_bytes)

    alignment_note = "Not attempted (global translation alignment was disabled)."
    alignment_warning = None
    if attempt_alignment:
        try:
            aligned, info = ip.try_align(before_rgb, after_rgb)
            alignment_note = info.get("message", str(info))
            if info["status"] == "applied":
                after_rgb = aligned
            elif info["status"] == "unreliable":
                alignment_warning = info["message"]
        except (ValueError, cv2.error) as exc:
            alignment_warning = f"Automatic alignment could not be estimated ({exc}); results may contain alignment-induced false positives."
            alignment_note = "Alignment estimate failed; no correction was applied."

    difference_map, mask, regions, stats = cd.detect_changes(
        before_rgb, after_rgb, threshold=threshold, min_region_area=min_region_area
    )
    regions = geospatial.annotate_regions(regions, georef)
    overlay = ip.create_change_overlay(after_rgb, mask, regions)
    difference_rgb = ip.difference_to_rgb(difference_map)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    before_name, after_name = os.path.basename(before.filename or "before"), os.path.basename(after.filename or "after")
    report = rg.build_report(
        generated_at=generated_at,
        source_note="Uploaded through the Change Sentinel web interface",
        before_label=before_label,
        after_label=after_label,
        file_note=f"{before_name} ({before_raw.shape[1]}x{before_raw.shape[0]} px), {after_name} ({after_raw.shape[1]}x{after_raw.shape[0]} px)",
        threshold=threshold,
        min_region_area=min_region_area,
        max_size=max_size,
        alignment_note=alignment_note,
        stats=stats,
        regions=regions,
        geo_note=geo_note,
    )
    return {
        "disclaimer": "Candidate visual differences from classical RGB image processing; results require human review and are not confirmed real-world changes.",
        "stats": stats,
        "regions": regions,
        "warnings": warnings + ([alignment_warning] if alignment_warning else []),
        "alignment_note": alignment_note,
        "geo_note": geo_note,
        "processed_size": {"width": int(before_rgb.shape[1]), "height": int(before_rgb.shape[0])},
        "images": {"overlay_png": _png_base64(overlay), "difference_png": _png_base64(difference_rgb)},
        "report_markdown": report,
    }
