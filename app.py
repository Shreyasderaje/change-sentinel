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
VIEWS = [
    "📤  Upload Images",
    "📊  Detection Results",
    "⌕  Candidate Regions",
    "🗺️  Map View",
    "▤  Analysis Report",
]

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


def _sync_navigation(source, target):
    """Keep the compact top navigation and sidebar navigation in sync."""
    st.session_state[target] = st.session_state[source]


def inject_glass_theme():
    """Apply the local Earth backdrop and shared glass-dashboard styling."""
    image_path = Path(__file__).resolve().parent / "static" / "earth-at-night.png"
    if not image_path.is_file():
        raise FileNotFoundError(f"Required local dashboard background is missing: {image_path}")
    background = "/app/static/earth-at-night.png"
    st.markdown(
        f"""<style>
        :root {{
          --cs-ink: #f3f8ff; --cs-muted: #a9bdd4; --cs-dim: #7891ae;
          --cs-cyan: #63d9ff; --cs-blue: #398dff; --cs-border: rgba(110,190,255,.22);
          --cs-glass: rgba(8,24,48,.68); --cs-glass-strong: rgba(8,25,51,.86);
        }}
        html, body {{ color: var(--cs-ink); background: #030b18; }}
        [data-testid="stAppViewContainer"] {{
          position:relative; min-height:100vh; background-color:#030b18;
          background-image:url("{background}"); background-size:cover;
          background-position:center 44%; background-attachment:fixed;
        }}
        [data-testid="stAppViewContainer"]::before {{
          content:""; position:fixed; inset:0; z-index:0; pointer-events:none;
          background:linear-gradient(110deg,rgba(2,9,22,.44),rgba(3,12,29,.22) 55%,rgba(3,12,28,.38));
        }}
        [data-testid="stHeader"] {{ background:rgba(4,13,27,.28); }}
        [data-testid="stMain"] {{ position:relative; z-index:1; background:transparent; }}
        [data-testid="stMainBlockContainer"] {{ max-width:1540px; padding-top:1.6rem; padding-bottom:2rem; }}
        [data-testid="stSidebar"] {{ position:relative; z-index:2; height:100vh!important; height:100dvh!important; max-height:100dvh!important; overflow:hidden!important; background:rgba(4,15,33,.48); border-right:1px solid rgba(104,190,255,.24); }}
        [data-testid="stSidebarContent"] {{ box-sizing:border-box; height:100%; max-height:100dvh; min-height:0; overflow-y:auto!important; overflow-x:hidden; overscroll-behavior-y:contain; -webkit-overflow-scrolling:touch; scrollbar-gutter:stable; padding-top:.65rem; padding-bottom:calc(2rem + env(safe-area-inset-bottom)); background:linear-gradient(180deg,rgba(5,20,43,.70),rgba(5,16,34,.68)); backdrop-filter:blur(22px); -webkit-backdrop-filter:blur(22px); }}
        [data-testid="stSidebar"] h2:first-of-type {{ display:none; }}
        [data-testid="stVerticalBlockBorderWrapper"] {{ border:1px solid var(--cs-border)!important; border-radius:20px!important; background:linear-gradient(145deg,rgba(14,38,69,.74),rgba(7,22,45,.67))!important; box-shadow:0 14px 36px rgba(0,7,22,.26),inset 0 1px rgba(255,255,255,.055); backdrop-filter:blur(18px); -webkit-backdrop-filter:blur(18px); transition:border-color .2s ease,box-shadow .2s ease,transform .2s ease; }}
        [data-testid="stVerticalBlockBorderWrapper"]:hover {{ border-color:rgba(91,205,255,.38)!important; box-shadow:0 16px 40px rgba(0,7,22,.32),0 0 22px rgba(35,144,255,.08),inset 0 1px rgba(255,255,255,.07); }}
        h1,h2,h3,h4 {{ color:#f4f8ff!important; letter-spacing:-.025em; }}
        h1 {{ font-size:clamp(2rem,3vw,3.1rem)!important; font-weight:720!important; }}
        h2 {{ font-size:1.55rem!important; }} h3 {{ font-size:1.15rem!important; }}
        p,li,[data-testid="stMarkdownContainer"] {{ color:#dce8f7; }}
        [data-testid="stCaptionContainer"], [data-testid="stWidgetLabel"] p {{ color:var(--cs-muted)!important; }}
        [data-testid="stMetric"] {{ padding:16px 18px; border:1px solid rgba(104,190,255,.19); border-radius:16px; background:linear-gradient(145deg,rgba(17,47,82,.67),rgba(8,25,49,.72)); box-shadow:inset 0 1px rgba(255,255,255,.045); }}
        [data-testid="stMetricLabel"] {{ color:var(--cs-muted)!important; }} [data-testid="stMetricValue"] {{ color:#f4f9ff!important; }}
        [data-testid="stImage"] img {{ border-radius:13px; border:1px solid rgba(125,190,255,.20); }}
        [data-testid="stFileUploader"] section {{ border:1px dashed rgba(99,192,255,.46); border-radius:14px; background:rgba(9,28,53,.56); transition:border-color .2s,background .2s; }}
        [data-testid="stFileUploader"] section:hover {{ border-color:var(--cs-cyan); background:rgba(12,43,75,.7); }}
        [data-testid="stTextInput"] input, [data-testid="stNumberInput"] input {{ background:rgba(4,17,36,.70); color:var(--cs-ink); border:1px solid rgba(117,177,229,.27); border-radius:10px; }}
        [data-testid="stTextInput"] input:focus {{ border-color:var(--cs-cyan); box-shadow:0 0 0 2px rgba(69,188,255,.16); }}
        [data-testid="stButton"] button, [data-testid="stDownloadButton"] button {{ border:1px solid rgba(116,190,255,.28); background:rgba(16,44,77,.68); color:#eaf6ff; border-radius:11px; min-height:2.65rem; transition:transform .18s ease,border-color .18s ease,box-shadow .18s ease,filter .18s ease; }}
        [data-testid="stButton"] button:hover, [data-testid="stDownloadButton"] button:hover {{ border-color:rgba(99,217,255,.76); box-shadow:0 0 18px rgba(42,160,255,.20); transform:translateY(-1px); color:#fff; }}
        [data-testid="stButton"] button:active, [data-testid="stDownloadButton"] button:active {{ transform:translateY(0) scale(.99); }}
        [data-testid="stButton"] button[kind="primary"], [data-testid="stDownloadButton"] button[kind="primary"] {{ color:white; border:1px solid rgba(122,224,255,.65); background:linear-gradient(100deg,#176cff,#12b8ed); box-shadow:0 8px 24px rgba(18,117,255,.28),inset 0 1px rgba(255,255,255,.24); font-weight:700; }}
        [data-testid="stAlert"] {{ border-radius:13px; background:rgba(7,28,52,.80); border:1px solid rgba(111,182,241,.23); }}
        [data-testid="stDataFrame"] {{ border:1px solid rgba(110,190,255,.20); border-radius:12px; overflow:hidden; }}
        [data-testid="stExpander"] {{ border:1px solid rgba(110,190,255,.20); border-radius:13px; background:rgba(8,24,46,.58); }}
        [data-testid="stRadio"] > div {{ gap:.35rem; }}
        [data-testid="stRadio"] label {{ border:1px solid rgba(107,174,227,.18); border-radius:12px; padding:.55rem .75rem; background:rgba(8,27,52,.43); transition:all .18s ease; }}
        [data-testid="stRadio"] label:hover {{ border-color:rgba(98,208,255,.48); background:rgba(25,71,112,.46); }}
        [data-testid="stRadio"] label:has(input:checked) {{ border-color:rgba(80,203,255,.70); background:linear-gradient(100deg,rgba(26,102,217,.44),rgba(14,155,195,.30)); box-shadow:0 0 18px rgba(31,145,255,.15),inset 0 1px rgba(255,255,255,.1); }}
        [data-testid="stRadio"] input {{ accent-color:#48cfff; }}
        [data-testid="stSlider"] [role="slider"] {{ background:#65d9ff; }}
        [data-testid="stCheckbox"] label {{ color:#e6f1ff!important; }}
        [data-testid="stMarkdownContainer"] a {{ color:#72d8ff; }}
        [data-testid="stMarkdownContainer"] code {{ background:rgba(2,14,30,.70); color:#aee8ff; }}
        .cs-brand {{ display:flex;align-items:center;gap:13px;margin:.3rem 0 .2rem; }}
        .cs-brand-icon {{ width:54px;height:54px;display:grid;place-items:center;border-radius:17px;background:linear-gradient(145deg,rgba(26,117,225,.42),rgba(21,203,226,.15));border:1px solid rgba(113,218,255,.48);box-shadow:0 0 28px rgba(23,134,255,.25),inset 0 1px rgba(255,255,255,.19);font-size:27px; }}
        .cs-eyebrow {{ color:#75d9ff;font-size:.74rem;letter-spacing:.16em;text-transform:uppercase;font-weight:700; }}
        .cs-subtitle {{ color:#b7cbe0;font-size:1.02rem;margin:.35rem 0 .35rem; }}
        .cs-badges {{ display:flex;flex-wrap:wrap;gap:8px;margin:.7rem 0 1rem; }}
        .cs-badge {{ padding:6px 11px;border-radius:999px;border:1px solid rgba(107,196,255,.29);background:rgba(8,33,60,.62);color:#ccecff;font-size:.76rem;letter-spacing:.02em; }}
        .cs-badge.status {{ border-color:rgba(59,224,178,.34);color:#8cf2d1;background:rgba(7,65,60,.34); }}
        .cs-note {{ color:#b9cde2;font-size:.88rem;line-height:1.55; }}
        .cs-fade {{ animation:cs-fade-in .42s ease both; }}
        @keyframes cs-fade-in {{ from {{opacity:0;transform:translateY(6px)}} to {{opacity:1;transform:translateY(0)}} }}
        @media(max-width:900px) {{ [data-testid="stMainBlockContainer"] {{padding:1rem 1rem 1.5rem}} [data-testid="stMetric"] {{padding:12px}} }}
        @media(max-width:640px) {{ [data-testid="stMainBlockContainer"] {{padding:.8rem .7rem 1.2rem}} [data-testid="stRadio"] > div {{gap:.15rem;flex-wrap:wrap}} [data-testid="stRadio"] label {{padding:.42rem .48rem;font-size:.78rem}} .cs-brand-icon {{width:46px;height:46px}} }}
        @media(prefers-reduced-motion:reduce) {{ *,*::before,*::after {{animation-duration:.01ms!important;animation-iteration-count:1!important;scroll-behavior:auto!important;transition-duration:.01ms!important}} }}
        </style>""",
        unsafe_allow_html=True,
    )


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
        st.markdown(
            '<div class="cs-brand"><div class="cs-brand-icon">🛰️</div>'
            '<div><div style="font-size:1.08rem;font-weight:750;color:#f4f8ff">Change Sentinel</div>'
            '<div style="font-size:.76rem;color:#a9bdd4">Geospatial intelligence</div></div></div>',
            unsafe_allow_html=True,
        )
        st.header(f"🛰️ {APP_NAME}")
        st.caption(
            "Satellite / aerial imagery change-detection review dashboard "
            "(prototype)."
        )

        st.markdown("---")
        st.markdown("**WORKSPACE**")
        st.radio(
            "Workspace navigation",
            VIEWS,
            key="sidebar_nav",
            label_visibility="collapsed",
            on_change=_sync_navigation,
            args=("sidebar_nav", "main_nav"),
        )
        st.markdown("---")
        st.subheader("Synthetic demo data")
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
    st.subheader("Upload image pair")
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

    with st.container(border=True):
        st.markdown("#### Preview comparison")
        st.caption("A side-by-side view of the actual decoded uploads. No imagery is substituted.")
        if before_raw is not None and after_raw is not None:
            preview_before, preview_after = st.columns(2)
            with preview_before:
                show_image(before_raw, caption="Before image")
            with preview_after:
                show_image(after_raw, caption="After image")
        else:
            st.markdown(
                '<div class="cs-note">Upload both source images to see the comparison preview here. '
                'Synthetic demo imagery is available from the sidebar and is clearly labeled.</div>',
                unsafe_allow_html=True,
            )

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
        page_title=f"{APP_NAME} - Change Detection",
        page_icon="🛰️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_glass_theme()
    st.session_state.setdefault("sidebar_nav", VIEWS[0])
    st.session_state.setdefault("main_nav", st.session_state["sidebar_nav"])
    st.markdown(
        '<div class="cs-fade"><div class="cs-brand"><div class="cs-brand-icon">&#128752;</div><div>'
        '<div class="cs-eyebrow">Space &amp; Defence Tech</div>'
        '<h1 style="margin:2px 0 0;font-size:clamp(2rem,3vw,3.1rem)">Change Sentinel</h1>'
        '</div></div><div class="cs-subtitle">AI-Powered Satellite Imagery Change Detection</div>'
        '<div class="cs-note">Compare two captures of the same area, inspect candidate visual differences, '
        'and prepare a traceable report for human review.</div>'
        '<div class="cs-badges"><span class="cs-badge">Space &amp; Defence Tech</span>'
        '<span class="cs-badge">HackFront India 2026</span>'
        '<span class="cs-badge status">&#9679; Prototype - Human review required</span></div></div>',
        unsafe_allow_html=True,
    )
    render_sidebar()
    st.radio(
        "Dashboard navigation", VIEWS, horizontal=True, key="main_nav",
        label_visibility="collapsed", on_change=_sync_navigation,
        args=("main_nav", "sidebar_nav"),
    )
    selected = st.session_state["main_nav"]
    if selected == VIEWS[0]:
        render_upload_tab()
    elif selected == VIEWS[1]:
        render_results_tab()
    elif selected == VIEWS[2]:
        render_regions_tab()
    elif selected == VIEWS[3]:
        render_map_tab()
    else:
        render_report_tab()
    st.divider()
    st.caption(DISCLAIMER)

if __name__ == "__main__":
    main()
