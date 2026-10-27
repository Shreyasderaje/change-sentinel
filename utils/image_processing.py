"""Image loading, preprocessing, alignment and visualisation helpers.

All functions in this module operate on plain RGB NumPy arrays and use
image pixel coordinates only. Nothing here performs geographic
reprojection, and nothing here can prove that two images show the same
location on the ground.
"""

from __future__ import annotations

import cv2
import numpy as np
from PIL import Image

DEFAULT_MAX_SIZE = 1024
SUPPORTED_FORMATS = ["jpg", "jpeg", "png", "tif", "tiff"]


class ImageValidationError(ValueError):
    """Raised when an image cannot be decoded or prepared for comparison."""


def load_rgb_image(uploaded_file):
    """Read an uploaded image (path or file-like object) as an RGB array."""
    try:
        image = Image.open(uploaded_file)
        image.load()
        return np.asarray(image.convert("RGB"))
    except Exception as exc:
        raise ImageValidationError(
            "The image could not be decoded. Please upload a valid "
            "JPG, JPEG, PNG or TIFF file."
        ) from exc


def image_size(image):
    """Return (height, width) of an array image, raising on empty input."""
    if image is None or getattr(image, "ndim", 0) < 2 or image.size == 0:
        raise ImageValidationError("The image is empty.")
    height, width = image.shape[:2]
    return int(height), int(width)


def resize_image(image, max_size: int = DEFAULT_MAX_SIZE):
    """Downscale so the longest side is at most ``max_size`` (aspect kept)."""
    height, width = image_size(image)

    if max(height, width) <= max_size:
        return image.copy()

    scale = max_size / float(max(height, width))
    new_width = max(1, int(round(width * scale)))
    new_height = max(1, int(round(height * scale)))

    return cv2.resize(
        image,
        (new_width, new_height),
        interpolation=cv2.INTER_AREA,
    )


def compare_dimensions(before, after):
    """Return human-readable warnings about a raw image pair.

    These checks run before resizing so the user is warned early that a
    pair may be incompatible. Equal dimensions do NOT prove that two
    images depict the same area.
    """
    height_b, width_b = before.shape[:2]
    height_a, width_a = after.shape[:2]
    ratio_b = width_b / float(height_b)
    ratio_a = width_a / float(height_a)

    notes = []
    if abs(ratio_b - ratio_a) / max(ratio_b, ratio_a) > 0.02:
        notes.append(
            "The two images have different aspect ratios "
            f"(before: {ratio_b:.3f}, after: {ratio_a:.3f}). They may not "
            "cover the same area, or one of them may be cropped or rotated."
        )
    longest_b = max(height_b, width_b)
    longest_a = max(height_a, width_a)
    if longest_b >= 4 * longest_a or longest_a >= 4 * longest_b:
        notes.append(
            "The two images have very different pixel resolutions. They "
            "will be resampled to a common size, which can exaggerate or "
            "hide real differences between the scenes."
        )
    return notes


def prepare_pair(before, after, max_size: int = DEFAULT_MAX_SIZE):
    """Resize two images to a common processing size (aspect preserved).

    This function does not prove that the images depict the same
    geographic scene or that they are aligned. Raises
    :class:`ImageValidationError` when their dimensions are incompatible
    after resizing.
    """
    if before is None or after is None:
        raise ImageValidationError("Both images are required.")

    before = resize_image(before, max_size)
    after = resize_image(after, max_size)

    if before.shape != after.shape:
        raise ImageValidationError(
            "The images have incompatible dimensions after resizing "
            f"(before: {before.shape[1]}x{before.shape[0]} px, "
            f"after: {after.shape[1]}x{after.shape[0]} px). Provide images "
            "with compatible aspect ratios that cover the same area."
        )

    return before, after


def estimate_translation(before_rgb, after_rgb):
    """Estimate a global translation between two equal-size RGB images.

    Uses phase correlation on grayscale copies with a Hann window to
    suppress edge effects. Returns ``(dx, dy, response)`` where
    ``response`` is a rough confidence measure (higher is better).
    Raises :class:`ImageValidationError` when no reliable estimate can
    be made.
    """
    if before_rgb.shape != after_rgb.shape:
        raise ImageValidationError(
            "Alignment requires both images to have identical dimensions."
        )

    window = cv2.createHanningWindow(
        (before_rgb.shape[1], before_rgb.shape[0]), cv2.CV_32F
    )
    before_gray = cv2.cvtColor(before_rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    after_gray = cv2.cvtColor(after_rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)

    (dx, dy), response = cv2.phaseCorrelate(before_gray, after_gray, window)
    return float(dx), float(dy), float(response)


def try_align(
    before_rgb,
    after_rgb,
    max_shift_pixels: int = 64,
    min_response: float = 0.05,
):
    """Try to align ``after`` onto ``before`` with a global translation.

    Both candidate shift signs are evaluated and the warp that actually
    reduces the mean absolute difference is kept, so alignment is never
    silently assumed to have succeeded.

    Returns ``(aligned_after_or_None, info)`` where ``info`` always
    contains a ``status`` key:

    * ``"unnecessary"`` — images are already aligned (< 0.5 px shift).
    * ``"applied"`` — a translation warp measurably reduced the error.
    * ``"unreliable"`` — the estimate or the correction failed validation;
      ``aligned`` is ``None`` and the caller should warn the user.
    """
    dx, dy, response = estimate_translation(before_rgb, after_rgb)
    magnitude = (dx**2 + dy**2) ** 0.5
    info = {
        "estimated_shift_xy": (round(dx, 2), round(dy, 2)),
        "response": round(response, 4),
    }

    if magnitude < 0.5:
        info["status"] = "unnecessary"
        info["message"] = "Images are already aligned (estimated shift < 0.5 px)."
        return after_rgb.copy(), info

    if magnitude > max_shift_pixels or response < min_response:
        info["status"] = "unreliable"
        info["message"] = (
            "Automatic alignment was not confident (estimated shift "
            f"({dx:.1f}, {dy:.1f}) px, response {response:.3f}). Results may "
            "contain alignment-induced false positives; treat them with care."
        )
        return None, info

    baseline_error = float(np.mean(cv2.absdiff(after_rgb, before_rgb)))
    candidates = []
    for shift_x, shift_y in ((-dx, -dy), (dx, dy)):
        matrix = np.float32([[1, 0, shift_x], [0, 1, shift_y]])
        warped = cv2.warpAffine(
            after_rgb,
            matrix,
            (after_rgb.shape[1], after_rgb.shape[0]),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_REFLECT,
        )
        error = float(np.mean(cv2.absdiff(warped, before_rgb)))
        candidates.append((error, warped, (shift_x, shift_y)))

    candidates.sort(key=lambda item: item[0])
    best_error, best_image, best_shift = candidates[0]

    if best_error >= baseline_error:
        info["status"] = "unreliable"
        info["message"] = (
            "Automatic alignment did not reduce the difference between the "
            "images, so no correction was applied. Results may contain "
            "alignment-induced false positives."
        )
        return None, info

    info["status"] = "applied"
    info["applied_shift_xy"] = (round(best_shift[0], 2), round(best_shift[1], 2))
    info["error_before"] = round(baseline_error, 3)
    info["error_after"] = round(best_error, 3)
    info["message"] = (
        "Global translation alignment applied via phase correlation "
        f"(shift {best_shift[0]:.1f}, {best_shift[1]:.1f} px; mean absolute "
        f"difference {baseline_error:.2f} -> {best_error:.2f})."
    )
    return best_image, info


def create_change_overlay(
    after_rgb,
    mask,
    regions,
    mask_color=(255, 45, 45),
    box_color=(255, 200, 0),
    alpha: float = 0.45,
    show_labels: bool = True,
):
    """Return the after-image with candidate regions highlighted.

    Flagged pixels are tinted and bounding boxes with region numbers are
    drawn in image pixel space, so the overlay is easy to tell apart
    from the untouched image.
    """
    overlay = after_rgb.copy()

    if mask is not None and np.any(mask > 0):
        tint = np.array(mask_color, dtype=np.float32)
        mask_bool = mask > 0
        blended = (
            tint[None, None, :] * alpha + overlay[mask_bool].astype(np.float32) * (1.0 - alpha)
        )
        overlay[mask_bool] = np.clip(blended, 0, 255).astype(np.uint8)

    for index, region in enumerate(regions, start=1):
        x, y, width, height = region["bbox_xywh"]
        cv2.rectangle(overlay, (x, y), (x + width, y + height), box_color, 2)
        if show_labels:
            label = f"#{index}"
            (text_w, text_h), _ = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
            )
            text_y = max(text_h + 6, y)
            box_top = max(0, text_y - text_h - 6)
            cv2.rectangle(
                overlay,
                (x, box_top),
                (x + text_w + 6, text_y),
                box_color,
                -1,
            )
            cv2.putText(
                overlay,
                label,
                (x + 3, text_y - 3),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 0),
                1,
                cv2.LINE_AA,
            )

    return overlay


def difference_to_rgb(difference_map, colormap=cv2.COLORMAP_INFERNO):
    """Render a 0-1 difference intensity map as a coloured RGB image."""
    max_value = float(np.max(difference_map)) if difference_map.size else 0.0
    if max_value <= 0.0:
        return np.zeros((*difference_map.shape, 3), dtype=np.uint8)
    scaled = np.clip(difference_map / max_value * 255.0, 0, 255).astype(np.uint8)
    coloured = cv2.applyColorMap(scaled, colormap)
    return cv2.cvtColor(coloured, cv2.COLOR_BGR2RGB)


def crop_region(image, bbox_xywh, padding: int = 10):
    """Crop a region (with padding) from an image, clamped to its bounds."""
    height, width = image.shape[:2]
    x, y, box_w, box_h = bbox_xywh
    x0 = max(0, int(x) - padding)
    y0 = max(0, int(y) - padding)
    x1 = min(width, int(x) + int(box_w) + padding)
    y1 = min(height, int(y) + int(box_h) + padding)
    return image[y0:y1, x0:x1].copy()
