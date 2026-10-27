"""Tests for utils.report_generation and geospatial guards."""

import numpy as np

from utils import change_detection as cd
from utils import geospatial
from utils import report_generation as rg


def make_rgb(height=128, width=128, seed=0):
    rng = np.random.default_rng(seed)
    base = np.zeros((height, width, 3), dtype=np.int16)
    base[...] = (100, 120, 140)
    noise = rng.integers(-8, 9, size=(height, width, 3), dtype=np.int16)
    return np.clip(base + noise, 0, 255).astype(np.uint8)


def build_fixture():
    """Run detection on a synthetic pair and return the report inputs."""
    before = make_rgb(seed=10)
    after = before.copy()
    after[30:90, 40:110] = (25, 25, 30)
    _, _, regions, stats = cd.detect_changes(before, after)
    regions = geospatial.annotate_regions(regions, None)
    return stats, regions


def test_report_contains_required_sections():
    stats, regions = build_fixture()
    report = rg.build_report(
        generated_at="2026-10-27 12:00:00",
        source_note="Uploaded by the user via the web interface",
        before_label="2025-01-15",
        after_label="2025-06-20",
        file_note="before.png (128x128 px), after.png (128x128 px)",
        threshold=0.15,
        min_region_area=50,
        max_size=1024,
        alignment_note="Not attempted.",
        stats=stats,
        regions=regions,
        geo_note="No geographic metadata was available.",
    )

    for fragment in (
        "# Change Sentinel Detection Report",
        "## Inputs",
        "## Detection Method",
        "## Metrics",
        "## Candidate Regions",
        "## Limitations",
        "## Recommended Next Step",
        "2025-01-15",
        "0.15",
        f"{stats['total_pixels']:,}",
        f"{stats['changed_pixels']:,}",
        "classical image processing",
        "not a trained AI model",
        "human verification",
    ):
        assert fragment in report, f"Missing fragment: {fragment}"


def test_report_labels_pixel_coordinates_without_geo():
    stats, regions = build_fixture()
    report = rg.build_report(
        generated_at="2026-10-27 12:00:00",
        source_note="test",
        before_label="",
        after_label="",
        file_note="test files",
        threshold=0.15,
        min_region_area=50,
        max_size=1024,
        alignment_note="Not attempted.",
        stats=stats,
        regions=regions,
        geo_note="No geographic metadata was available.",
    )

    # Image coordinates are listed; no fabricated latitude/longitude pairs.
    x, y, _, _ = regions[0]["bbox_xywh"]
    assert f"{x}, {y}" in report
    assert "No geographic metadata was available" in report
    assert "lon, lat |" not in report


def test_report_lists_geo_coordinates_when_present():
    stats, regions = build_fixture()
    for region in regions:
        region["centroid_lonlat"] = (77.5946, 12.9716)
    report = rg.build_report(
        generated_at="2026-10-27 12:00:00",
        source_note="test",
        before_label="",
        after_label="",
        file_note="test files",
        threshold=0.15,
        min_region_area=50,
        max_size=1024,
        alignment_note="Not attempted.",
        stats=stats,
        regions=regions,
        geo_note="Coordinates derived from the file's CRS (EPSG:4326).",
    )
    assert "77.594600" in report
    assert "12.971600" in report


def test_report_without_regions():
    stats = {
        "total_pixels": 100,
        "changed_pixels": 0,
        "percent_flagged": 0.0,
        "candidate_region_count": 0,
        "mean_difference": 0.0,
        "max_difference": 0.0,
    }
    report = rg.build_report(
        generated_at="2026-10-27 12:00:00",
        source_note="test",
        before_label="",
        after_label="",
        file_note="test files",
        threshold=0.15,
        min_region_area=50,
        max_size=1024,
        alignment_note="Not attempted.",
        stats=stats,
        regions=[],
        geo_note="No geographic metadata was available.",
    )
    assert "No candidate regions met the detection criteria" in report


# --- geospatial guards: no coordinates may be invented ----------------------

def test_geospatial_unavailable_returns_none():
    info, note = geospatial.read_georeference(b"not a tiff")
    if not geospatial.rasterio_available():
        assert info is None
        assert "rasterio" in note
    else:
        assert info is None  # garbage bytes can never yield a georeference


def test_annotate_regions_without_georef_has_no_coordinates():
    regions = [
        {
            "area_pixels": 100.0,
            "pixel_count": 100,
            "centroid_xy": (10, 10),
            "bbox_xywh": (5, 5, 10, 10),
            "mean_difference": 0.2,
        }
    ]
    annotated = geospatial.annotate_regions(regions, None)
    assert annotated[0]["region_id"] == 1
    assert annotated[0]["centroid_lonlat"] is None
    assert annotated[0]["bbox_lonlat"] is None
