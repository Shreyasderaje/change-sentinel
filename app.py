"""Change Sentinel — Satellite Imagery Change-Detection Dashboard.

A prototype decision-support tool: upload two images of the same area
taken at different times, review candidate visual differences, and
download a Markdown report.

Important honesty notes baked into this app:

* Outputs are *candidate* visual differences, never confirmed changes.
* Detection is classical image processing, not a trained AI model.
* RGB inputs only — no true NDVI (that requires a near-infrared band).
* Geographic coordinates are shown ONLY when the input is a
  georeferenced raster whose metadata can be read; ordinary JPG/PNG
  uploads show image pixel coordinates. Coordinates are never invented.

Run with:

    streamlit run app.py
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import io
from pathlib import Path

import pandas as pd
import streamlit as st

from utils import change_detection as cd
from utils import geospatial
from utils import image_processing as ip
from utils import map_generation as mapgen
from utils import report_generation as rg

APP_NAME = "Change Sentinel"
MAX_REGION_CROPS_SHOWN = 12

SAMPLE_DATA_DIR = Path(__file__).resolve().parent / "sample_data"

DISCLAIMER = (
    "All results are **candidate visual differences** produced by classical "
    "image processing. They are not confirmed real-world changes, say "
    "nothing about legality or cause, and require verification by a "
    "qualified human analyst."
)


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def show_image(image, caption=None):
    """Version-tolerant full-width image display."""
    try:
        st.image(image, caption=caption, width="stretch")
    except Exception:
        st.image(image, caption=caption, use_container_width=True)


def file_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def reset_analysis():
    st.session_state.pop("analysis", None)


def get_analysis():
    return st.session_state.get("analysis")


def load_bytes(uploaded_file):
    data = uploaded_file.getvalue()
    return data, Path(uploaded_file.name).suffix.lower().lstrip(".")


# ---------------------------------------------------------------------------
# Analysis pipeline
# ---------------------------------------------------------------------------

def run_analysis(
    before_bytes,
    after_bytes,
    before_ext,
    after_ext,
    before_name,
    after_name,
    before_label,
    after_label,
    source_note,
):
    """Validate, preprocess, detect and store results in session state."""
    max_size = st.session_state["max_size"]
    threshold = st.session_state["threshold"]
    min_area = st.session_state["min_region_area"]
    align_enabled = st.session_state["attempt_alignment"]

    try:
        before_raw = ip.load_rgb_image(io.BytesIO(before_bytes))
    except ip.ImageValidationError as exc:
        st.error(f"Before image: {exc}")
        return
    try:
        after_raw = ip.load_rgb_image(io.BytesIO(after_bytes))
    except ip.ImageValidationError as exc:
        st.error(f"After image: {exc}")
        return

    warnings = ip.compare_dimensions(before_raw, after_raw)
    for note in warnings:
        st.warning(note)

    try:
        before, after = ip.prepare_pair(before_raw, after_raw, max_size=max_size)
    except ip.ImageValidationError as exc:
        st.error(str(exc))
        return

    # --- Georeferencing: only from real metadata, never invented. -------
    georef = None
    geo_note = (
        "No geographic metadata is available for these inputs. All "
        "coordinates are **image pixel coordinates** (origin: top-left). "
        "No latitude/longitude values have been invented."
    )
    geo_bytes = before_bytes if before_ext in ("tif", "tiff") else None
    if geo_bytes is not None:
        georef, geo_note = geospatial.read_georeference(geo_bytes)
    elif before_ext in ("tif", "tiff"):
        geo_note = "rasterio is not installed, so GeoTIFF georeference metadata cannot be read."
    st.session_state["georef"] = georef
    st.session_state["geo_note"] = geo_note

    # --- Optional global alignment (validated, never silently applied) --
    alignment_note = "Not attempted (global translation alignment was disabled)."
    align_warning = None
    if align_enabled:
        aligned, info = ip.try_align(before, after)
        alignment_note = info.get("message", str(info))
        if info["status"] == "applied":
            after = aligned
        elif info["status"] == "unreliable":
            align_warning = info["message"]

    with st.spinner("Detecting candidate changes…"):
        difference_map, mask, regions, stats = cd.detect_changes(
            before,
            after,
            threshold=threshold,
            min_region_area=min_area,
        )
        regions = geospatial.annotate_regions(regions, georef)
        overlay = ip.create_change_overlay(after, mask, regions)
        difference_rgb = ip.difference_to_rgb(difference_map)

    analysis = {
        "before": before,
        "after": after,
        "difference_rgb": difference_rgb,
        "overlay": overlay,
        "mask": mask,
        "difference_map": difference_map,
        "regions": regions,
        "stats": stats,
        "threshold": threshold,
        "min_region_area": min_area,
        "max_size": max_size,
        "alignment_note": alignment_note,
        "before_label": before_label,
        "after_label": after_label,
        "before_name": before_name,
        "after_name": after_name,
        "source_note": source_note,
        "before_size": (int(before_raw.shape[1]), int(before_raw.shape[0])),
        "after_size": (int(after_raw.shape[1]), int(after_raw.shape[0])),
        "warnings": warnings,
        "align_warning": align_warning,
        "georef": georef,
        "geo_note": geo_note,
        "generated_at": _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "input_hash": file_sha256(before_bytes + after_bytes),
    }
    st.session_state["analysis"] = analysis
    st.success(
        "Analysis complete — open the **Detection Results**, **Candidate "
        "Regions**, **Map** and **Report** tabs."
    )


def run_demo(kind: str):
    """Load a bundled synthetic demo pair and analyse it immediately."""
    if kind == "change":
        names = ("before.png", "after.png")
        note = "Bundled synthetic demo pair (a structure and a bare-soil patch were added)."
    else:
        names = ("identical_before.png", "identical_after.png")
        note = "Bundled synthetic demo pair (byte-identical images — expect no candidates)."

    before_path = SAMPLE_DATA_DIR / names[0]
    after_path = SAMPLE_DATA_DIR / names[1]
    if not (before_path.exists() and after_path.exists()):
        st.error(
            "Sample data files are missing. Run `python make_sample_data.py` "
            "to regenerate them."
        )
        return

    before_label = f"Synthetic demo — BEFORE ({names[0]}, not real satellite imagery)"
    after_label = f"Synthetic demo — AFTER ({names[1]}, not real satellite imagery)"
    run_analysis(
        before_path.read_bytes(),
        after_path.read_bytes(),
        "png",
        "png",
        names[0],
        names[1],
        before_label,
        after_label,
        note,
    )


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

def render_sidebar():
    with st.sidebar:
        st.header(f"🛰️ {APP_NAME}")
        st.caption(
            "Satellite / aerial imagery change-detection review dashboard "
            "(prototype)."
        )

        st.subheader("Demo data")
        st.caption(
            "Loads bundled images that are **synthetic** — they mimic an "
            "aerial view but are not real satellite imagery."
        )
        if st.button("Load synthetic demo pair (with changes)", width="stretch"):
            reset_analysis()
            run_demo("change")
        if st.button("Load identical pair (no changes)", width="stretch"):
            reset_analysis()
            run_demo("identical")

        st.divider()

        st.subheader("Detection settings")
        st.session_state["threshold"] = st.slider(
            "Sensitivity threshold",
            min_value=0.01,
            max_value=0.60,
            value=0.15,
            step=0.01,
            help=(
                "Difference intensity (0-1) above which a pixel is flagged. "
                "Lower values flag more pixels; higher values flag fewer."
            ),
        )
        st.session_state["min_region_area"] = st.slider(
            "Minimum candidate region area (px)",
            min_value=10,
            max_value=1000,
            value=50,
            step=10,
            help="Smaller connected areas are discarded as noise.",
        )
        st.session_state["max_size"] = st.select_slider(
            "Maximum processed image dimension (px)",
            options=[512, 768, 1024, 1536, 2048],
            value=1024,
            help="Larger images are downscaled to this size (aspect preserved).",
        )
        st.session_state["attempt_alignment"] = st.checkbox(
            "Attempt automatic alignment (experimental)",
            value=False,
            help=(
                "Estimate and correct a global image shift via phase "
                "correlation. The correction is only applied when it "
                "measurably reduces the difference between the images."
            ),
        )

        st.divider()
        st.subheader("About this prototype")
        st.markdown(
            "- Method: **classical image processing** (pixel differencing, "
            "thresholding, morphology) — not a trained AI model.\n"
            "- Inputs are RGB; no true NDVI is computed (that needs a "
            "near-infrared band).\n"
            "- Coordinates are image pixels unless a georeferenced GeoTIFF "
            "is uploaded (requires the optional `rasterio` package).\n"
            "- Geographic coordinates are never invented."
        )


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

def render_upload_tab():
    st.subheader("Upload images")
    st.markdown(
        "Upload an **earlier** image and a **later** image of the "
        "**same area**. Supported formats: JPG, JPEG, PNG and GeoTIFF."
    )

    col_before, col_after = st.columns(2)

    with col_before:
        st.markdown("**Before image (earlier date)**")
        before_file = st.file_uploader(
            "Before image",
            type=ip.SUPPORTED_FORMATS,
            key="before_uploader",
        )
        before_label = st.text_input(
            "Label or date (optional)",
            key="before_label",
            placeholder="e.g. 2025-01-15",
        )

    with col_after:
        st.markdown("**After image (later date)**")
        after_file = st.file_uploader(
            "After image",
            type=ip.SUPPORTED_FORMATS,
            key="after_uploader",
        )
        after_label = st.text_input(
            "Label or date (optional)",
            key="after_label",
            placeholder="e.g. 2025-06-20",
        )

    st.checkbox(
        "I confirm both images cover the same area of interest",
        key="same_area_confirmed",
    )

    before_bytes = before_ext = after_bytes = after_ext = None
    before_raw = after_raw = None

    if before_file is not None:
        before_bytes, before_ext = load_bytes(before_file)
        try:
            before_raw = ip.load_rgb_image(io.BytesIO(before_bytes))
            height, width = before_raw.shape[:2]
            st.caption(f"Decoded: {width} x {height} px (RGB)")
            show_image(before_raw, caption="Before (preview)")
        except ip.ImageValidationError as exc:
            st.error(f"Before image: {exc}")

    if after_file is not None:
        after_bytes, after_ext = load_bytes(after_file)
        try:
            after_raw = ip.load_rgb_image(io.BytesIO(after_bytes))
            height, width = after_raw.shape[:2]
            st.caption(f"Decoded: {width} x {height} px (RGB)")
            show_image(after_raw, caption="After (preview)")
        except ip.ImageValidationError as exc:
            st.error(f"After image: {exc}")

    if before_raw is not None and after_raw is not None:
        for note in ip.compare_dimensions(before_raw, after_raw):
            st.warning(note)
        if file_sha256(before_bytes) == file_sha256(after_bytes):
            st.info(
                "Both uploads are byte-identical, so no differences will be "
                "found. That is expected if you are testing the tool — not "
                "if the two files were meant to be different scenes."
            )

    if not st.session_state.get("same_area_confirmed"):
        st.info("Please confirm that both images cover the same area before analysing.")
        st.button("Analyze images", disabled=True, type="primary")
        return

    if before_bytes is None or after_bytes is None:
        st.info("Upload both a before image and an after image to continue.")
        st.button("Analyze images", disabled=True, type="primary")
        return

    if st.button("Analyze images", type="primary"):
        reset_analysis()
        run_analysis(
            before_bytes,
            after_bytes,
            before_ext,
            after_ext,
            before_file.name,
            after_file.name,
            st.session_state.get("before_label", ""),
            st.session_state.get("after_label", ""),
            "Uploaded by the user via the web interface",
        )


def _stale_analysis_note(analysis):
    """Warn when uploads changed since the stored analysis was produced."""
    current = st.session_state.get("analysis")
    if current is None:
        return
    before_file = st.session_state.get("before_uploader")
    after_file = st.session_state.get("after_uploader")
    if before_file is None and after_file is None:
        return
    try:
        digest = file_sha256(before_file.getvalue() + after_file.getvalue())
    except Exception:
        return
    if digest != analysis.get("input_hash"):
        st.caption(
            "⚠️ The uploaded files changed since this analysis was produced. "
            "Press **Analyze images** again to refresh the results."
        )


def render_results_tab():
    st.subheader("Detection results")
    analysis = get_analysis()
    if analysis is None:
        st.info("No analysis yet — upload two images in the **Upload Images** tab, or use a demo pair in the sidebar.")
        return

    _stale_analysis_note(analysis)

    st.info(DISCLAIMER)

    stats = analysis["stats"]
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Candidate regions", f"{stats['candidate_region_count']}")
    col2.metric("Pixels flagged", f"{stats['changed_pixels']:,}")
    col3.metric("% pixels flagged", f"{stats['percent_flagged']:.3f}%")
    col4.metric("Mean diff intensity", f"{stats['mean_difference']:.4f}")
    col5.metric("Max diff intensity", f"{stats['max_difference']:.4f}")
    st.caption(
        "Percentages refer to **image pixels**, not to real-world land area. "
        "Threshold: "
        f"{analysis['threshold']:.2f}; minimum region area: "
        f"{analysis['min_region_area']:.0f} px; processed size: "
        f"{analysis['before'].shape[1]} x {analysis['before'].shape[0]} px."
    )

    for note in analysis["warnings"]:
        st.warning(note)
    if analysis.get("align_warning"):
        st.warning(analysis["align_warning"])

    row1 = st.columns(2)
    with row1[0]:
        show_image(analysis["before"], caption=f"Before — {analysis['before_label'] or analysis['before_name']}")
    with row1[1]:
        show_image(analysis["after"], caption=f"After — {analysis['after_label'] or analysis['after_name']}")

    row2 = st.columns(2)
    with row2[0]:
        show_image(
            analysis["difference_rgb"],
            caption="Difference intensity (brighter = larger visual difference)",
        )
    with row2[1]:
        show_image(
            analysis["overlay"],
            caption="Candidate change overlay (red = flagged pixels, boxes = candidate regions)",
        )

    st.caption(f"Alignment: {analysis['alignment_note']}")


def render_regions_tab():
    st.subheader("Candidate regions")
    analysis = get_analysis()
    if analysis is None:
        st.info("No analysis yet — run one from the **Upload Images** tab or load a demo pair.")
        return

    regions = analysis["regions"]
    st.info(DISCLAIMER)
    st.caption(
        "All positions are **image pixel coordinates** (origin: top-left "
        "corner). They are not latitude/longitude — see the Map tab for "
        "geographic coordinates when they are genuinely available."
    )

    if not regions:
        st.success(
            "No candidate regions met the criteria. Identical or very "
            "similar images legitimately produce zero candidates."
        )
        return

    rows = []
    for region in regions:
        x, y, width, height = region["bbox_xywh"]
        cx, cy = region["centroid_xy"]
        row = {
            "Region": region.get("region_id"),
            "BBox x (px)": x,
            "BBox y (px)": y,
            "Width (px)": width,
            "Height (px)": height,
            "Centroid x (px)": cx,
            "Centroid y (px)": cy,
            "Area (px)": round(region["area_pixels"], 1),
            "Mean diff": round(region["mean_difference"], 3),
        }
        if region.get("centroid_lonlat"):
            row["Centroid lon, lat"] = f"{region['centroid_lonlat'][0]:.6f}, {region['centroid_lonlat'][1]:.6f}"
        rows.append(row)
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

    st.markdown("#### Visual inspection")
    shown = regions[:MAX_REGION_CROPS_SHOWN]
    for region in shown:
        x, y, width, height = region["bbox_xywh"]
        region_id = region.get("region_id", "?")
        with st.expander(
            f"Region #{region_id} — bbox (x={x}, y={y}, w={width}, h={height}), "
            f"area ≈ {region['area_pixels']:.0f} px"
        ):
            crop_before = ip.crop_region(analysis["before"], region["bbox_xywh"])
            crop_after = ip.crop_region(analysis["after"], region["bbox_xywh"])
            cols = st.columns(2)
            with cols[0]:
                show_image(crop_before, caption="Before (crop)")
            with cols[1]:
                show_image(crop_after, caption="After (crop)")

    if len(regions) > MAX_REGION_CROPS_SHOWN:
        st.caption(
            f"Showing the {MAX_REGION_CROPS_SHOWN} largest of "
            f"{len(regions)} candidate regions. The full list is in the report."
        )


def render_map_tab():
    st.subheader("Geographic view")
    analysis = get_analysis()
    if analysis is None:
        st.info("No analysis yet — run one from the **Upload Images** tab or load a demo pair.")
        return

    georef = analysis.get("georef")
    regions = analysis["regions"]

    if georef is None:
        st.info(analysis.get("geo_note", "No geographic metadata is available for these inputs."))
        st.markdown(
            "**Why no map?** Ordinary JPG/PNG files carry no geographic "
            "metadata, and this application never invents latitude/longitude "
            "values or substitutes a default location. To get a real map:"
        )
        st.markdown(
            "1. Upload a **georeferenced GeoTIFF** (with a valid CRS and "
            "affine transform), and\n"
            "2. install the optional geospatial extras: "
            "`pip install rasterio folium streamlit-folium` (see README)."
        )
        if regions:
            st.markdown(
                "Meanwhile, candidate region positions are listed in image "
                "pixel coordinates in the **Candidate Regions** tab, and "
                "drawn on the image in the **Detection Results** tab."
            )
        return

    st.success(analysis.get("geo_note", ""))

    if not mapgen.folium_available():
        st.warning(
            "The file is georeferenced, but the optional `folium` package is "
            f"not installed, so the interactive map cannot be rendered "
            f"({mapgen.FOLIUM_IMPORT_ERROR}). Install it with: "
            "`pip install folium streamlit-folium`."
        )
        return

    fmap = mapgen.build_change_map(regions, georef)
    if fmap is None:
        st.warning(
            "No candidate region has valid geographic bounds, so there is "
            "nothing to draw on the map."
        )
        return

    try:
        from streamlit_folium import st_folium
    except ImportError:
        st.warning(
            "The optional `streamlit-folium` package is not installed, so "
            "the interactive map cannot be rendered. Install it with: "
            "`pip install streamlit-folium`."
        )
        return

    try:
        st_folium(fmap, height=520, width="stretch")
    except TypeError:
        # Older streamlit-folium builds only understand use_container_width.
        st_folium(fmap, height=520, use_container_width=True)

    st.caption(
        "Rectangles show candidate region footprints derived from the "
        "input file's own georeference metadata. They are candidates "
        "for human review, not confirmed changes."
    )


def render_report_tab():
    st.subheader("Report")
    analysis = get_analysis()
    if analysis is None:
        st.info("No analysis yet — run one from the **Upload Images** tab or load a demo pair.")
        return

    st.info(DISCLAIMER)

    report = rg.build_report(
        generated_at=analysis["generated_at"],
        source_note=analysis["source_note"],
        before_label=analysis["before_label"],
        after_label=analysis["after_label"],
        file_note=(
            f"{analysis['before_name']} ({analysis['before_size'][0]}x{analysis['before_size'][1]} px), "
            f"{analysis['after_name']} ({analysis['after_size'][0]}x{analysis['after_size'][1]} px)"
        ),
        threshold=analysis["threshold"],
        min_region_area=analysis["min_region_area"],
        max_size=analysis["max_size"],
        alignment_note=analysis["alignment_note"],
        stats=analysis["stats"],
        regions=analysis["regions"],
        geo_note=analysis["geo_note"],
    )

    with st.expander("Preview report", expanded=True):
        st.markdown(report)

    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    st.download_button(
        "Download Markdown report",
        data=report,
        file_name=f"change_sentinel_report_{stamp}.md",
        mime="text/markdown",
        type="primary",
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    st.set_page_config(
        page_title=f"{APP_NAME} — Change Detection",
        page_icon="🛰️",
        layout="wide",
    )

    st.title(f"🛰️ {APP_NAME}")
    st.caption(
        "Compare two images of the same area, review **candidate** visual "
        "changes, and export a report. Prototype — outputs require human "
        "verification."
    )

    render_sidebar()

    tab_upload, tab_results, tab_regions, tab_map, tab_report = st.tabs(
        [
            "📤 Upload Images",
            "📊 Detection Results",
            "🔎 Candidate Regions",
            "🗺️ Map",
            "📄 Report",
        ]
    )

    with tab_upload:
        render_upload_tab()
    with tab_results:
        render_results_tab()
    with tab_regions:
        render_regions_tab()
    with tab_map:
        render_map_tab()
    with tab_report:
        render_report_tab()

    st.divider()
    st.caption(DISCLAIMER)


if __name__ == "__main__":
    main()
