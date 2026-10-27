"""Markdown report generation for Change Sentinel.

The report is honest by design: it always labels its outputs as
candidate visual differences, states the detection method and settings,
and uses geographic coordinates only when they were genuinely derived
from input metadata.
"""

from __future__ import annotations

LIMITATIONS = [
    "Results indicate **candidate visual differences** between the two "
    "images. They do **not** establish the cause, legality, or significance "
    "of any change.",
    "The detection method is classical image processing (pixel differencing "
    "with smoothing, thresholding and morphological cleanup). It is **not** "
    "a trained AI model, and no detection accuracy has been measured.",
    "Inputs are ordinary RGB images: no true NDVI or multispectral analysis "
    "is performed (real NDVI requires a near-infrared band).",
    "Differences can be caused by illumination changes, seasons, clouds, "
    "shadows, compression artefacts, sensor differences or image "
    "misalignment — all of which can produce false positives.",
    "Percentages in this report refer to **image pixels**, not to real-world "
    "land area. Real-world area requires valid geospatial metadata.",
    "This tool does not automatically declare any development illegal, "
    "identify a threat, or confirm that an event occurred.",
]

RECOMMENDED_NEXT_STEP = (
    "Review each candidate region visually and verify findings against "
    "appropriate source imagery, ground information or other evidence "
    "before drawing any conclusions."
)


def _format_region_rows(regions, include_geo):
    rows = []
    for region in regions:
        x, y, width, height = region["bbox_xywh"]
        cx, cy = region["centroid_xy"]
        row = (
            f"| {region.get('region_id', '?')} "
            f"| {x}, {y}, {width}, {height} "
            f"| {cx}, {cy} "
            f"| {region.get('area_pixels', 0):.0f} "
            f"| {region.get('pixel_count', 0)} "
            f"| {region.get('mean_difference', 0.0):.3f} "
        )
        if include_geo:
            lonlat = region.get("centroid_lonlat")
            row += f"| {lonlat[0]:.6f}, {lonlat[1]:.6f} " if lonlat else "| — "
        row += "|"
        rows.append(row)
    return rows


def build_report(
    *,
    generated_at,
    source_note,
    before_label,
    after_label,
    file_note,
    threshold,
    min_region_area,
    max_size,
    alignment_note,
    stats,
    regions,
    geo_note,
    max_regions_listed: int = 50,
):
    """Build the full Markdown report as a string."""
    lines = []
    add = lines.append

    add("# Change Sentinel Detection Report")
    add("")
    add(f"*Generated: {generated_at}*")
    add("")
    add("## Summary")
    add(
        "A comparison was performed on the supplied image pair to identify "
        "candidate visual changes. This report is a decision-support aid "
        "for human verification; it does not confirm that any real-world "
        "change occurred."
    )
    add("")
    add("## Inputs")
    add(f"- Before image: {before_label or 'not provided'}")
    add(f"- After image: {after_label or 'not provided'}")
    add(f"- Source: {source_note}")
    add(f"- Files: {file_note}")
    add("")
    add("## Detection Method")
    add(
        "- Method: Pixel-level RGB difference (mean absolute difference per "
        "pixel), Gaussian smoothing, intensity thresholding and "
        "morphological cleanup."
    )
    add(
        "- This baseline uses **classical image processing, not a trained "
        "AI model**."
    )
    add(f"- Threshold: {threshold:.2f} (0-1 scale of difference intensity)")
    add(f"- Minimum candidate region area: {min_region_area:.0f} pixels")
    add(
        f"- Maximum processed image dimension: {max_size} px "
        "(aspect ratio preserved)"
    )
    add(f"- Alignment: {alignment_note}")
    add("")
    add("## Metrics")
    add(f"- Total processed pixels: {stats['total_pixels']:,}")
    add(f"- Pixels flagged: {stats['changed_pixels']:,}")
    add(f"- Percentage of pixels flagged: {stats['percent_flagged']:.4f}%")
    add(f"- Candidate regions: {stats['candidate_region_count']}")
    add(f"- Mean difference intensity: {stats['mean_difference']:.4f}")
    add(f"- Maximum difference intensity: {stats['max_difference']:.4f}")
    add("")
    add("## Candidate Regions")

    include_geo = any(region.get("centroid_lonlat") for region in regions)
    if regions:
        header = (
            "| ID | Bounding box x, y, w, h (px) | Centroid x, y (px) "
            "| Area (px) | Pixels | Mean diff |"
        )
        separator = "| --- | --- | --- | --- | --- | --- |"
        if include_geo:
            header += " Centroid lon, lat |"
            separator += " --- |"
        add(header)
        add(separator)
        listed = regions[:max_regions_listed]
        lines.extend(_format_region_rows(listed, include_geo))
        if len(regions) > max_regions_listed:
            add("")
            add(
                f"*…and {len(regions) - max_regions_listed} further candidate "
                "region(s) not listed individually.*"
            )
    else:
        add(
            "No candidate regions met the detection criteria for this "
            "image pair and threshold."
        )

    add("")
    add("### Coordinate system")
    add(geo_note)
    add("")
    add("## Limitations")
    for limitation in LIMITATIONS:
        add(f"- {limitation}")
    add("")
    add("## Recommended Next Step")
    add(RECOMMENDED_NEXT_STEP)
    add("")

    return "\n".join(lines)
