"""HTTP-level tests for the FastAPI adapter and existing image pipeline."""

import io

import numpy as np
from fastapi.testclient import TestClient
from PIL import Image

from api import app

client = TestClient(app)


def png_bytes(image):
    buffer = io.BytesIO()
    Image.fromarray(image).save(buffer, format="PNG")
    return buffer.getvalue()


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_analyze_returns_real_pipeline_results_and_previews():
    before = np.full((128, 128, 3), 120, dtype=np.uint8)
    after = before.copy()
    after[30:90, 40:100] = 20
    response = client.post(
        "/analyze",
        files={
            "before": ("before.png", png_bytes(before), "application/octet-stream"),
            "after": ("after.png", png_bytes(after), "application/octet-stream"),
        },
        data={"before_label": "earlier", "after_label": "later"},
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["stats"]["candidate_region_count"] >= 1
    assert result["regions"][0]["bbox_xywh"]
    assert result["images"]["overlay_png"]
    assert result["images"]["difference_png"]
    assert "classical image processing" in result["report_markdown"]
    assert "human review" in result["disclaimer"]


def test_analyze_rejects_invalid_image_and_incompatible_aspect_ratio():
    invalid = client.post(
        "/analyze",
        files={"before": ("before.png", b"not an image"), "after": ("after.png", png_bytes(np.zeros((32, 32, 3), dtype=np.uint8)))},
    )
    assert invalid.status_code == 400
    incompatible = client.post(
        "/analyze",
        files={
            "before": ("before.png", png_bytes(np.zeros((32, 32, 3), dtype=np.uint8))),
            "after": ("after.png", png_bytes(np.zeros((32, 64, 3), dtype=np.uint8))),
        },
    )
    assert incompatible.status_code == 422
    assert "incompatible dimensions" in incompatible.json()["detail"]


def test_analyze_rejects_invalid_settings():
    image = png_bytes(np.zeros((32, 32, 3), dtype=np.uint8))
    response = client.post(
        "/analyze",
        files={"before": ("before.png", image), "after": ("after.png", image)},
        data={"threshold": "1.5"},
    )
    assert response.status_code == 422
