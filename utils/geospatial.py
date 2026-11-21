"""Optional geospatial support for Change Sentinel.

Real-world coordinates are produced ONLY when all of the following hold:

* the uploaded file is a georeferenced raster (e.g. GeoTIFF), AND
* the optional ``rasterio`` dependency is installed, AND
* the file actually carries a coordinate reference system and a valid
  affine transform.

For ordinary JPG/PNG uploads there is no geographic metadata, so every
function here returns ``None`` with an explanatory note. The
application never invents latitude/longitude values, and it never
substitutes default geographic bounds for real metadata.
"""

from __future__ import annotations

import os
import math
import tempfile

import numpy as np

try:
    import rasterio
    from rasterio import warp as _rio_warp

    HAS_RASTERIO = True
    RASTERIO_IMPORT_ERROR = None
except Exception as exc:  # ImportError, or a broken GDAL/PROJ install
    HAS_RASTERIO = False
    RASTERIO_IMPORT_ERROR = str(exc)


def rasterio_available() -> bool:
    """Whether the optional rasterio dependency could be imported."""
    return HAS_RASTERIO


class SpatialInputError(ValueError):
    """Raised when a pair cannot safely be treated as spatially comparable."""

    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def _validated_spatial_metadata(info, label):
    if not isinstance(info, dict):
        raise SpatialInputError(
            "missing_georeference",
            f"{label} raster must have a readable CRS and affine transform.",
        )

    crs = info.get("crs_obj")
    if crs is None:
        crs = info.get("crs")
    if crs is None or (isinstance(crs, str) and not crs.strip()):
        raise SpatialInputError(
            "missing_crs", f"{label} raster is missing a coordinate reference system."
        )

    transform = info.get("transform")
    try:
        coefficients = tuple(float(value) for value in transform)
    except (TypeError, ValueError):
        coefficients = ()
    if len(coefficients) < 6 or not all(
        math.isfinite(value) for value in coefficients[:6]
    ):
        raise SpatialInputError(
            "missing_transform",
            f"{label} raster is missing a usable affine transform.",
        )

    try:
        width = int(info["width"])
        height = int(info["height"])
        bounds = tuple(float(value) for value in info["bounds"])
    except (KeyError, TypeError, ValueError, OverflowError):
        raise SpatialInputError(
            "invalid_metadata",
            f"{label} raster has invalid dimensions or spatial bounds.",
        )
    if (
        width <= 0
        or height <= 0
        or len(bounds) != 4
        or not all(math.isfinite(value) for value in bounds)
        or info["width"] != width
        or info["height"] != height
    ):
        raise SpatialInputError(
            "invalid_metadata",
            f"{label} raster has invalid dimensions or spatial bounds.",
        )

    a, b, c, d, e, f = coefficients[:6]
    corner_coordinates = [
        (c, f),
        (a * width + c, d * width + f),
        (b * height + c, e * height + f),
        (a * width + b * height + c, d * width + e * height + f),
    ]
    expected_bounds = (
        min(point[0] for point in corner_coordinates),
        min(point[1] for point in corner_coordinates),
        max(point[0] for point in corner_coordinates),
        max(point[1] for point in corner_coordinates),
    )
    return crs, coefficients[:6], width, height, bounds, expected_bounds


def validate_spatial_pair(
    before_info,
    after_info,
    *,
    before_is_raster,
    after_is_raster,
    tolerance=1e-6,
):
    """Validate whether two inputs share the same raster grid.

    Ordinary image pairs are explicitly classified as pixel-space only;
    their geographic relationship is not inferred. A spatial comparison
    requires two georeferenced rasters with matching CRS, dimensions,
    resolution, extent, and affine grid alignment. This function validates
    metadata only; it does not reproject, resample, or align either raster.

    ``before_info`` and ``after_info`` are values returned by
    :func:`read_georeference`. Set the ``*_is_raster`` flags from the actual
    input formats so an unreferenced raster is not mistaken for an ordinary
    image with no geographic metadata.
    """
    if not isinstance(before_is_raster, bool) or not isinstance(after_is_raster, bool):
        raise TypeError("before_is_raster and after_is_raster must be booleans.")
    if not math.isfinite(tolerance) or tolerance < 0:
        raise ValueError("tolerance must be a finite, non-negative number.")

    if before_is_raster != after_is_raster:
        raise SpatialInputError(
            "unsupported_input_pair",
            "A raster and an ordinary image cannot be assumed to share "
            "geographic coordinates.",
        )
    if not before_is_raster:
        return {
            "mode": "pixel",
            "georeferenced": False,
            "note": (
                "Both inputs are ordinary images. They are compared in pixel "
                "space only; no shared geographic coordinates are assumed."
            ),
        }

    before = _validated_spatial_metadata(before_info, "Before")
    after = _validated_spatial_metadata(after_info, "After")
    before_crs, before_transform, before_width, before_height, before_bounds, before_expected_bounds = before
    after_crs, after_transform, after_width, after_height, after_bounds, after_expected_bounds = after

    for label, bounds, expected_bounds in (
        ("Before", before_bounds, before_expected_bounds),
        ("After", after_bounds, after_expected_bounds),
    ):
        if any(
            not math.isclose(actual, expected, rel_tol=0.0, abs_tol=tolerance)
            for actual, expected in zip(bounds, expected_bounds)
        ):
            raise SpatialInputError(
                "invalid_metadata",
                f"{label} raster bounds do not match its affine transform and dimensions.",
            )

    mismatches = []
    if before_crs != after_crs:
        mismatches.append("CRS differs")
    if (before_width, before_height) != (after_width, after_height):
        mismatches.append("raster dimensions differ")

    before_x_resolution = math.hypot(before_transform[0], before_transform[3])
    before_y_resolution = math.hypot(before_transform[1], before_transform[4])
    after_x_resolution = math.hypot(after_transform[0], after_transform[3])
    after_y_resolution = math.hypot(after_transform[1], after_transform[4])
    if not (
        math.isclose(
            before_x_resolution, after_x_resolution, rel_tol=0.0, abs_tol=tolerance
        )
        and math.isclose(
            before_y_resolution, after_y_resolution, rel_tol=0.0, abs_tol=tolerance
        )
    ):
        mismatches.append("pixel resolution differs")

    if any(
        not math.isclose(a, b, rel_tol=0.0, abs_tol=tolerance)
        for a, b in zip(before_bounds, after_bounds)
    ):
        mismatches.append("spatial extent differs")
    if any(
        not math.isclose(a, b, rel_tol=0.0, abs_tol=tolerance)
        for a, b in zip(before_transform, after_transform)
    ):
        mismatches.append("affine grid alignment differs")

    if mismatches:
        raise SpatialInputError(
            "spatial_mismatch",
            "Before and after rasters are not on the same spatial grid: "
            + "; ".join(mismatches)
            + ". Reproject/resample them to a common grid before comparison.",
        )

    return {
        "mode": "geospatial",
        "georeferenced": True,
        "note": (
            "Both inputs have matching CRS, dimensions, resolution, spatial "
            "extent, and affine grid alignment."
        ),
    }


def _with_temp_tiff(file_bytes: bytes):
    """Context helper: write bytes to a temp .tif file and yield its path."""
    handle = tempfile.NamedTemporaryFile(suffix=".tif", delete=False)
    try:
        handle.write(file_bytes)
        handle.close()
        yield handle.name
    finally:
        try:
            os.unlink(handle.name)
        except OSError:
            pass


def read_georeference(file_bytes: bytes):
    """Read the georeference metadata of a raster file.

    Returns ``(info, note)``. ``info`` is a dict with the affine
    transform, CRS and bounds when usable georeferencing exists, and
    ``None`` otherwise (with ``note`` explaining why).
    """
    if not HAS_RASTERIO:
        return None, (
            "Geographic coordinates are unavailable: the optional 'rasterio' "
            "package is not installed. Upload a georeferenced GeoTIFF and "
            "install rasterio to enable real geographic output."
        )

    for path in _with_temp_tiff(file_bytes):
        try:
            with rasterio.open(path) as dataset:
                if dataset.crs is None:
                    return None, (
                        "The raster does not carry a coordinate reference "
                        "system, so no geographic coordinates can be derived. "
                        "Image pixel coordinates will be shown instead."
                    )
                transform = dataset.transform
                if transform is None or transform.is_identity:
                    return None, (
                        "The raster carries a coordinate reference system but "
                        "no usable affine transform, so pixel positions cannot "
                        "be converted to geographic coordinates."
                    )
                info = {
                    "crs": dataset.crs.to_string(),
                    "crs_obj": dataset.crs,
                    "crs_is_geographic": bool(dataset.crs.is_geographic),
                    "transform": transform,
                    "width": int(dataset.width),
                    "height": int(dataset.height),
                    "bounds": tuple(float(v) for v in dataset.bounds),
                }
            return info, (
                f"Georeferenced raster detected (CRS: {info['crs']}). "
                "Coordinates below are derived from the file's own metadata "
                "and converted to WGS84 (EPSG:4326); their accuracy depends "
                "on the source data."
            )
        except Exception as exc:
            return None, (
                "The file could not be read as a georeferenced raster, so no "
                f"geographic coordinates will be derived ({exc})."
            )

    return None, "Georeference could not be read."


def read_rgb_raster(file_bytes: bytes):
    """Read a multi-band raster as an 8-bit RGB array, or return None.

    Ordinary 8-bit RGB images decode fine with Pillow; this path exists
    for GeoTIFFs whose band layout or bit depth Pillow handles poorly.
    """
    if not HAS_RASTERIO:
        return None

    for path in _with_temp_tiff(file_bytes):
        try:
            with rasterio.open(path) as dataset:
                if dataset.count >= 3:
                    bands = [
                        dataset.read(index).astype(np.float32) for index in (1, 2, 3)
                    ]
                elif dataset.count == 1:
                    band = dataset.read(1).astype(np.float32)
                    bands = [band, band, band]
                else:
                    return None

                stacked = np.dstack(bands)
                data_max = float(np.max(stacked))
                if data_max <= 0.0:
                    return None
                if data_max <= 255.0 and stacked.max() <= 255.0:
                    scaled = stacked
                else:
                    low, high = np.percentile(stacked, (2.0, 98.0))
                    if high <= low:
                        high = data_max
                        low = 0.0
                    scaled = (stacked - low) / max(high - low, 1e-9) * 255.0
                return np.clip(scaled, 0, 255).astype(np.uint8)
        except Exception:
            return None

    return None


def pixel_to_lonlat(x: float, y: float, info):
    """Convert an image pixel (x, y) to (lon, lat) using the file's transform.

    Returns ``None`` when no valid georeference is available. Pixel
    centres (+0.5) are used, matching GDAL's pixel-corner convention.
    """
    if not info or not HAS_RASTERIO:
        return None
    try:
        map_x, map_y = info["transform"] * (float(x) + 0.5, float(y) + 0.5)
        lons, lats = _rio_warp.transform(
            info["crs_obj"], "EPSG:4326", [map_x], [map_y]
        )
        lon, lat = float(lons[0]), float(lats[0])
        if not (-180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0):
            return None
        return lon, lat
    except Exception:
        return None


def annotate_regions(regions, info):
    """Return copies of ``regions`` annotated with geographic coordinates.

    When ``info`` is None, every geographic field is None and the
    original pixel coordinates remain the only reference.
    """
    annotated = []
    for index, region in enumerate(regions, start=1):
        item = dict(region)
        item["region_id"] = index
        item["centroid_lonlat"] = None
        item["bbox_lonlat"] = None

        if info:
            item["centroid_lonlat"] = pixel_to_lonlat(
                region["centroid_xy"][0], region["centroid_xy"][1], info
            )
            x, y, width, height = region["bbox_xywh"]
            corners = [
                (x, y),
                (x + width, y),
                (x, y + height),
                (x + width, y + height),
            ]
            points = [pixel_to_lonlat(cx, cy, info) for cx, cy in corners]
            if all(points):
                lons = [point[0] for point in points]
                lats = [point[1] for point in points]
                item["bbox_lonlat"] = (
                    min(lons),
                    min(lats),
                    max(lons),
                    max(lats),
                )

        annotated.append(item)
    return annotated
