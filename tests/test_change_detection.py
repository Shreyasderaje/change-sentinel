"""Tests for utils.change_detection.

Covers the two key acceptance scenarios:
* identical images produce no meaningful differences;
* an added object produces a detectable candidate region.
"""

import numpy as np
import pytest

from utils import change_detection as cd


def make_rgb(height=256, width=256, color=(100, 120, 140), seed=0):
    """Deterministic noisy RGB test image with real texture."""
    rng = np.random.default_rng(seed)
    base = np.zeros((height, width, 3), dtype=np.int16)
    base[...] = color
    noise = rng.integers(-8, 9, size=(height, width, 3), dtype=np.int16)
    return np.clip(base + noise, 0, 255).astype(np.uint8)


def test_identical_images_produce_no_differences():
    image = make_rgb(seed=1)
    difference_map, mask, regions, stats = cd.detect_changes(image, image)

    assert np.count_nonzero(mask) == 0
    assert stats["changed_pixels"] == 0
    assert stats["percent_flagged"] == 0.0
    assert stats["candidate_region_count"] == 0
    assert regions == []
    assert float(stats["max_difference"]) == 0.0
    assert float(np.max(np.abs(difference_map))) == 0.0


def test_added_object_is_detected():
    before = make_rgb(seed=2)
    after = before.copy()
    # Add a dark 70x80 "building" on the textured background.
    after[80:150, 100:180] = (25, 25, 30)

    difference_map, mask, regions, stats = cd.detect_changes(
        before, after, threshold=0.15, min_region_area=50
    )

    assert stats["changed_pixels"] > 0
    assert stats["candidate_region_count"] >= 1

    # The object's bounding box must be covered by a candidate region.
    covered = any(
        x <= 100 and y <= 80 and x + width >= 180 and y + height >= 150
        for (x, y, width, height) in (r["bbox_xywh"] for r in regions)
    )
    assert covered, f"No region covers the added object: {regions}"

    # Some region centroid should fall inside the object.
    inside = any(
        100 <= cx <= 180 and 80 <= cy <= 150
        for (cx, cy) in (r["centroid_xy"] for r in regions)
    )
    assert inside, f"No region centroid lies inside the object: {regions}"


def test_percent_flagged_matches_mask():
    before = make_rgb(seed=3)
    after = before.copy()
    after[40:100, 40:110] = (200, 200, 200)

    _, mask, _, stats = cd.detect_changes(before, after)

    assert stats["changed_pixels"] == int(np.count_nonzero(mask))
    assert stats["total_pixels"] == mask.size
    expected = 100.0 * np.count_nonzero(mask) / mask.size
    assert stats["percent_flagged"] == pytest.approx(expected)


def test_threshold_changes_detection_output():
    before = make_rgb(seed=4)
    after = before.copy()
    after[60:120, 60:120] = (200, 200, 200)

    _, _, _, low_stats = cd.detect_changes(before, after, threshold=0.05)
    _, _, _, high_stats = cd.detect_changes(before, after, threshold=0.50)

    assert low_stats["changed_pixels"] > high_stats["changed_pixels"]
    assert high_stats["changed_pixels"] < int(60 * 60)  # strong object mostly gone


def test_min_region_area_filters_small_regions():
    before = make_rgb(seed=5)
    after = before.copy()
    after[30:40, 30:38] = (220, 220, 220)  # tiny 10x8 patch

    _, _, regions_large, stats_large = cd.detect_changes(
        before, after, threshold=0.15, min_region_area=200
    )
    _, _, regions_small, _ = cd.detect_changes(
        before, after, threshold=0.15, min_region_area=10
    )

    assert stats_large["candidate_region_count"] == len(regions_large)
    assert len(regions_small) >= len(regions_large)
    assert all(r["area_pixels"] >= 200 for r in regions_large)
    assert len(regions_small) >= 1


def test_regions_sorted_by_area_descending():
    before = make_rgb(seed=6)
    after = before.copy()
    after[20:80, 20:80] = (30, 30, 35)        # 60x60 object
    after[150:190, 150:190] = (30, 30, 35)    # 40x40 object

    _, _, regions, _ = cd.detect_changes(before, after, threshold=0.15)
    areas = [r["area_pixels"] for r in regions]
    assert areas == sorted(areas, reverse=True)


def test_detect_changes_input_validation():
    image = make_rgb(64, 64, seed=7)

    with pytest.raises(ValueError):
        cd.detect_changes(image, image[:32])
    with pytest.raises(ValueError):
        cd.detect_changes(image, np.zeros((64, 64), dtype=np.uint8))
    with pytest.raises(ValueError):
        cd.detect_changes(None, image)
    with pytest.raises(ValueError):
        cd.detect_changes(image, image, threshold=1.5)
    with pytest.raises(ValueError):
        cd.detect_changes(image, image, threshold=-0.1)
    with pytest.raises(ValueError):
        cd.detect_changes(image, image, smooth_kernel=4)
