"""Interactive map building (optional feature).

Requires the optional ``folium`` package and is only called when a valid
georeference exists. The map is never populated with invented or
illustrative coordinates.
"""

from __future__ import annotations

try:
    import folium

    HAS_FOLIUM = True
    FOLIUM_IMPORT_ERROR = None
except Exception as exc:  # ImportError or a broken install
    HAS_FOLIUM = False
    FOLIUM_IMPORT_ERROR = str(exc)


def folium_available() -> bool:
    """Whether the optional folium dependency could be imported."""
    return HAS_FOLIUM


def build_change_map(regions, georef):
    """Build a folium map showing candidate region footprints.

    Args:
        regions: Region dicts annotated by ``geospatial.annotate_regions``.
        georef: Georeference info from ``geospatial.read_georeference``.

    Returns a ``folium.Map`` or ``None`` when folium is missing, no
    georeference exists, or no region carries valid geographic bounds.
    """
    if not HAS_FOLIUM or not georef:
        return None

    mapped = [region for region in regions if region.get("bbox_lonlat")]
    if not mapped:
        return None

    all_lats = []
    all_lons = []
    for region in mapped:
        lon0, lat0, lon1, lat1 = region["bbox_lonlat"]
        all_lats.extend([lat0, lat1])
        all_lons.extend([lon0, lon1])

    fmap = folium.Map(
        location=(sum(all_lats) / len(all_lats), sum(all_lons) / len(all_lons)),
        zoom_start=14,
        tiles="OpenStreetMap",
        control_scale=True,
    )

    for region in mapped:
        lon0, lat0, lon1, lat1 = region["bbox_lonlat"]
        centroid = region.get("centroid_lonlat")
        popup_html = (
            f"<b>Candidate region #{region.get('region_id', '?')}</b><br>"
            f"Bounding box (px): {region['bbox_xywh'][0]}, {region['bbox_xywh'][1]}, "
            f"{region['bbox_xywh'][2]}, {region['bbox_xywh'][3]}<br>"
            f"Area: {region.get('area_pixels', 0):.0f} px<br>"
            f"Mean diff: {region.get('mean_difference', 0.0):.3f}<br>"
        )
        if centroid:
            popup_html += (
                f"Centroid (lon, lat): {centroid[0]:.6f}, {centroid[1]:.6f}<br>"
            )
        popup_html += "<i>Candidate visual difference — needs human review.</i>"

        folium.Rectangle(
            bounds=[[lat0, lon0], [lat1, lon1]],
            color="#ff3b30",
            weight=2,
            fill=True,
            fill_color="#ff3b30",
            fill_opacity=0.25,
            popup=folium.Popup(popup_html, max_width=280),
        ).add_to(fmap)

        if centroid:
            folium.Marker(
                location=(centroid[1], centroid[0]),
                tooltip=f"Candidate region #{region.get('region_id', '?')}",
            ).add_to(fmap)

    padding = 0.001
    fmap.fit_bounds(
        [
            [min(all_lats) - padding, min(all_lons) - padding],
            [max(all_lats) + padding, max(all_lons) + padding],
        ]
    )
    return fmap
