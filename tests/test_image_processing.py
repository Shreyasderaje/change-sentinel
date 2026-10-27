"""Tests for utils.image_processing."""

import io

import cv2
import numpy as np
import pytest
from PIL import Image

from utils import image_processing as ip


def make_rgb(height=256, width=256, color=(100, 120, 140), seed=0):
    """Deterministic noisy RGB test image with real texture."""
    rng = np.random.default_rng(seed)
    base = np.zeros((height, width, 3), dtype=np.int16)
    base[...] = color
    noise = rng.integers(-8, 9, size=(height, width, 3), dtype=np.int16)
    return np.clip(base + noise, 0, 255).astype(np.uint8)


def encode_png(array):
    buffer = io.BytesIO()
    Image.fromarray(array).save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


# --- loading ---------------------------------------------------------------

def test_load_rgb_image_decodes_png():
    array = make_rgb(32, 48)
    decoded = ip.load_rgb_image(encode_png(array))
    assert decoded.shape == (32, 48, 3)
    assert decoded.dtype == np.uint8


def test_load_rgb_image_rejects_garbage():
    with pytest.raises(ip.ImageValidationError):
        ip.load_rgb_image(io.BytesIO(b"this is not an image"))


def test_image_size_rejects_empty():
    with pytest.raises(ip.ImageValidationError):
        ip.image_size(np.zeros((0, 0, 3), dtype=np.uint8))


# --- resizing / pair preparation -------------------------------------------

def test_resize_image_preserves_aspect_ratio():
    image = make_rgb(800, 400)
    resized = ip.resize_image(image, max_size=200)
    assert resized.shape[0] == 200
    assert resized.shape[1] == 100


def test_resize_image_keeps_small_images_unchanged():
    image = make_rgb(100, 100)
    resized = ip.resize_image(image, max_size=1024)
    assert resized.shape == image.shape
    assert np.array_equal(resized, image)


def test_prepare_pair_same_aspect_different_sizes():
    before = make_rgb(600, 300)
    after = make_rgb(300, 150)
    out_before, out_after = ip.prepare_pair(before, after, max_size=256)
    assert out_before.shape == out_after.shape
    assert out_before.shape[0] == 256


def test_prepare_pair_rejects_incompatible_aspect():
    before = make_rgb(600, 300)  # 2:1
    after = make_rgb(300, 300)   # 1:1
    with pytest.raises(ip.ImageValidationError):
        ip.prepare_pair(before, after)


def test_prepare_pair_requires_both_images():
    with pytest.raises(ip.ImageValidationError):
        ip.prepare_pair(None, make_rgb(64, 64))


def test_compare_dimensions_warns_on_aspect_mismatch():
    notes = ip.compare_dimensions(make_rgb(100, 200), make_rgb(100, 100))
    assert notes and "aspect ratio" in notes[0]


def test_compare_dimensions_quiet_for_compatible_pair():
    assert ip.compare_dimensions(make_rgb(300, 200), make_rgb(600, 400)) == []


# --- alignment --------------------------------------------------------------

def test_try_align_corrects_small_translation():
    before = make_rgb(256, 256, seed=5)
    matrix = np.float32([[1, 0, 6], [0, 1, 4]])
    shifted = cv2.warpAffine(
        before, matrix, (256, 256), borderMode=cv2.BORDER_REFLECT
    )

    aligned, info = ip.try_align(before, shifted)

    assert info["status"] == "applied"
    assert abs(info["applied_shift_xy"][0]) == pytest.approx(6, abs=1.5)
    assert abs(info["applied_shift_xy"][1]) == pytest.approx(4, abs=1.5)
    error_before = float(np.mean(cv2.absdiff(shifted, before)))
    error_after = float(np.mean(cv2.absdiff(aligned, before)))
    assert error_after < error_before


def test_try_align_reports_unnecessary_for_identical_images():
    image = make_rgb(128, 128, seed=6)
    aligned, info = ip.try_align(image, image.copy())
    assert info["status"] == "unnecessary"
    assert np.array_equal(aligned, image)


# --- overlays / crops --------------------------------------------------------

def test_create_change_overlay_tints_and_draws_boxes():
    after = make_rgb(128, 128, seed=7)
    mask = np.zeros((128, 128), dtype=np.uint8)
    mask[40:80, 40:80] = 255
    regions = [{"bbox_xywh": (40, 40, 40, 40), "area_pixels": 1600}]
    overlay = ip.create_change_overlay(after, mask, regions)

    assert overlay.shape == after.shape
    assert not np.array_equal(overlay, after)
    # Interior tinted pixels differ from the source; untouched corner does not.
    assert not np.array_equal(overlay[60, 60], after[60, 60])
    assert np.array_equal(overlay[5, 5], after[5, 5])


def test_crop_region_clamps_to_image_bounds():
    image = make_rgb(64, 64, seed=8)
    crop = ip.crop_region(image, (50, 50, 40, 40), padding=10)
    assert 0 < crop.shape[0] <= 64 and 0 < crop.shape[1] <= 64


def test_difference_to_rgb_black_for_zero_difference():
    difference = np.zeros((32, 32), dtype=np.float32)
    rendered = ip.difference_to_rgb(difference)
    assert rendered.shape == (32, 32, 3)
    assert np.count_nonzero(rendered) == 0
