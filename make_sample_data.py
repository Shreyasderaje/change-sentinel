"""Generate a small, clearly SYNTHETIC demo image pair for Change Sentinel.

The images are 100% synthetic patterns that loosely resemble an aerial
view of farmland (fields, a road, a water channel). They are NOT real
satellite imagery, cover no real location, and must only be used to
demonstrate the application's mechanics.

The "after" image adds two obvious changes to the "before" image:

* a dark rectangular structure (stands in for new construction), and
* a bare-soil patch (stands in for vegetation loss).

A second pair (``identical_before.png`` / ``identical_after.png``) is a
byte-identical copy pair, useful for demonstrating that identical
inputs produce no candidate regions.

Usage:

    python make_sample_data.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

WIDTH = 512
HEIGHT = 512
SEED = 42
OUTPUT_DIR = Path(__file__).resolve().parent / "sample_data"

WATERMARK_TEXT = "SYNTHETIC DEMO - NOT REAL SATELLITE IMAGERY"


def _textured_canvas():
    """Base scene: coloured field blocks, a road and a water channel."""
    canvas = np.zeros((HEIGHT, WIDTH, 3), dtype=np.int16)

    def fill(x, y, w, h, color):
        canvas[y : y + h, x : x + w] = color

    fill(0, 0, WIDTH, HEIGHT, (146, 128, 100))  # bare soil background
    fill(40, 60, 200, 140, (74, 122, 58))       # green field
    fill(270, 40, 180, 120, (56, 96, 48))       # darker green field
    fill(60, 240, 150, 110, (168, 150, 96))     # tan field
    fill(250, 260, 170, 130, (110, 118, 60))    # olive field
    fill(452, 40, 40, 340, (52, 88, 122))       # water channel
    fill(0, 396, WIDTH, 32, (96, 94, 92))       # road

    for start in range(10, WIDTH, 40):          # dashed centre line
        fill(start, 410, 20, 4, (205, 203, 196))

    rng = np.random.default_rng(SEED)
    noise = rng.integers(-5, 6, size=(HEIGHT, WIDTH, 3), dtype=np.int16)
    canvas = np.clip(canvas + noise, 0, 255).astype(np.uint8)
    return canvas


def _draw_watermark(pil_image):
    draw = ImageDraw.Draw(pil_image)
    try:
        font = ImageFont.load_default(size=16)
    except TypeError:  # Pillow < 10.1 has no size argument
        font = ImageFont.load_default()
    text_width = draw.textlength(WATERMARK_TEXT, font=font)
    position = (
        (pil_image.width - text_width) / 2,
        pil_image.height - 28,
    )
    draw.text(position, WATERMARK_TEXT, fill=(255, 255, 255), font=font)


def build_before():
    """Return the 'before' image as an RGB NumPy array."""
    canvas = _textured_canvas()
    image = Image.fromarray(canvas)
    _draw_watermark(image)  # identical on both images, cancels in comparison
    return np.asarray(image)


def build_after(before):
    """Return the 'after' image: the before image plus two added changes."""
    image = Image.fromarray(before.copy())
    draw = ImageDraw.Draw(image)

    # Change 1: new dark rectangular structure with a lighter roof edge.
    draw.rectangle((140, 96, 259, 179), fill=(34, 36, 42))
    draw.rectangle((140, 96, 259, 104), fill=(72, 74, 84))

    # Change 2: bare-soil patch inside the olive field (vegetation loss).
    draw.rectangle((300, 290, 369, 345), fill=(178, 156, 96))

    return np.asarray(image)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    before = build_before()
    after = build_after(before)

    outputs = {
        "before.png": before,
        "after.png": after,
        "identical_before.png": before,
        "identical_after.png": before,
    }
    for name, array in outputs.items():
        Image.fromarray(array).save(OUTPUT_DIR / name)
        print(f"Wrote {OUTPUT_DIR / name}")

    print(
        "\nNote: these are SYNTHETIC demonstration images. They do not "
        "depict any real location and are not real satellite imagery."
    )


if __name__ == "__main__":
    main()
