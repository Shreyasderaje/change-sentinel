"""Candidate change detection for aligned RGB image pairs.

This module implements classical image processing: pixel differencing,
Gaussian smoothing, thresholding, morphological cleanup and connected
component extraction. It is NOT a trained AI model, and its outputs are
candidate visual differences that require human verification.
"""

from __future__ import annotations

import cv2
import numpy as np


def detect_changes(
    before_rgb,
    after_rgb,
    threshold: float = 0.15,
    min_region_area: float = 50,
    smooth_kernel: int = 5,
):
    """Detect candidate visual changes between two aligned RGB images.

    Args:
        before_rgb: Earlier image as an (H, W, 3) uint8 RGB array.
        after_rgb: Later image as an (H, W, 3) uint8 RGB array.
        threshold: Difference intensity (0-1) above which a pixel is
            flagged as a candidate change.
        min_region_area: Minimum contour area (pixels) for a candidate
            region to be reported.
        smooth_kernel: Size of the Gaussian smoothing kernel applied to
            the raw difference map (must be an odd, positive integer).

    Returns:
        difference_map: Normalised difference intensity in [0, 1].
        mask: Binary mask (uint8, 0 or 255) of candidate changed pixels.
        regions: List of candidate region dictionaries with pixel
            bounding boxes and centroids (image coordinates only).
        stats: Summary statistics dictionary.

    This baseline uses classical image processing, not a trained AI
    model. Flagged pixels are candidates for human review, not
    confirmed real-world changes.
    """
    if before_rgb is None or after_rgb is None:
        raise ValueError("Both images are required.")

    if before_rgb.shape != after_rgb.shape:
        raise ValueError(
            "Images must have identical dimensions before comparison. "
            f"Got {before_rgb.shape} and {after_rgb.shape}."
        )

    if before_rgb.ndim != 3 or before_rgb.shape[2] != 3:
        raise ValueError("Expected RGB images with three channels.")

    if not 0 <= threshold <= 1:
        raise ValueError("Threshold must be between 0 and 1.")

    if smooth_kernel < 1 or smooth_kernel % 2 == 0:
        raise ValueError("smooth_kernel must be a positive odd integer.")

    before = before_rgb.astype(np.float32) / 255.0
    after = after_rgb.astype(np.float32) / 255.0

    difference = np.mean(np.abs(before - after), axis=2)
    difference = np.clip(difference, 0.0, 1.0)

    difference_map = cv2.GaussianBlur(difference, (smooth_kernel, smooth_kernel), 0)

    mask = (difference_map >= threshold).astype(np.uint8) * 255

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))

    # Close small gaps inside genuine regions, then remove isolated specks.
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)

    contours, _ = cv2.findContours(
        mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    regions = []
    for contour in contours:
        area = float(cv2.contourArea(contour))

        if area < min_region_area:
            continue

        moments = cv2.moments(contour)
        if moments["m00"] == 0:
            continue

        cx = int(moments["m10"] / moments["m00"])
        cy = int(moments["m01"] / moments["m00"])

        x, y, width, height = cv2.boundingRect(contour)

        region_mask = np.zeros(mask.shape, dtype=np.uint8)
        cv2.drawContours(region_mask, [contour], -1, 255, -1)
        region_mean_difference = float(cv2.mean(difference_map, mask=region_mask)[0])

        regions.append(
            {
                "area_pixels": area,
                "pixel_count": int(np.count_nonzero(region_mask)),
                "centroid_xy": (cx, cy),
                "bbox_xywh": (x, y, width, height),
                "mean_difference": region_mean_difference,
            }
        )

    regions.sort(key=lambda region: region["area_pixels"], reverse=True)

    total_pixels = int(mask.size)
    changed_pixels = int(np.count_nonzero(mask))

    stats = {
        "total_pixels": total_pixels,
        "changed_pixels": changed_pixels,
        "percent_flagged": (
            100.0 * changed_pixels / total_pixels if total_pixels else 0.0
        ),
        "candidate_region_count": len(regions),
        "mean_difference": float(np.mean(difference_map)),
        "max_difference": float(np.max(difference_map)),
    }

    return difference_map, mask, regions, stats
