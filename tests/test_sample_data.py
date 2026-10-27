"""Tests for the bundled synthetic demo data (make_sample_data.py).

Verifies that the generated pair is detectable with the app's default
settings, and that the identical pair produces zero candidates.
"""

import numpy as np

import make_sample_data as msd
from utils import change_detection as cd


def test_demo_pair_contains_two_detectable_changes():
    before = msd.build_before()
    after = msd.build_after(before)

    assert before.shape == after.shape == (msd.HEIGHT, msd.WIDTH, 3)

    _, mask, regions, stats = cd.detect_changes(
        before, after, threshold=0.15, min_region_area=50
    )

    assert stats["candidate_region_count"] >= 2
    assert stats["changed_pixels"] > 2000

    bboxes = [r["bbox_xywh"] for r in regions]

    def detected(box):
        """A candidate region must overlap the planted change by >= 60%."""
        x0, y0, x1, y1 = box
        object_area = (x1 - x0) * (y1 - y0)
        for (bx, by, bw, bh) in bboxes:
            overlap_w = min(x1, bx + bw) - max(x0, bx)
            overlap_h = min(y1, by + bh) - max(y0, by)
            if overlap_w > 0 and overlap_h > 0:
                if overlap_w * overlap_h >= 0.6 * object_area:
                    return True
        return False

    # Morphology may erode a region by a pixel or two, so overlap is
    # checked rather than exact bounding-box coverage.
    assert detected((140, 96, 260, 180)), "structure not detected"
    assert detected((300, 290, 370, 346)), "bare-soil patch not detected"


def test_demo_identical_pair_produces_no_candidates():
    before = msd.build_before()
    _, mask, regions, stats = cd.detect_changes(before, before)

    assert stats["candidate_region_count"] == 0
    assert np.count_nonzero(mask) == 0
    assert regions == []


def test_watermark_present_and_cancels_out():
    before = msd.build_before()
    after = msd.build_after(before)
    # The watermark strip (bottom rows) must be identical in both images.
    strip_start = msd.HEIGHT - 30
    assert np.array_equal(before[strip_start:, :], after[strip_start:, :])
