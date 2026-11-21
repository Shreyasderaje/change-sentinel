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

from io import BytesIO
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

from rasterio.enums import Resampling


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
    if coefficients[:6] == (1.0, 0.0, 0.0, 0.0, 1.0, 0.0):
        raise SpatialInputError(
            "missing_transform", f"{label} raster is missing a usable affine transform."
        )
    try:
        if HAS_RASTERIO:
            rasterio.crs.CRS.from_user_input(crs)
    except Exception:
        raise SpatialInputError(
            "invalid_crs", f"{label} raster has an invalid coordinate reference system."
        ) from None

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
    if a * e - b * d == 0.0:
        raise SpatialInputError(
            "missing_transform", f"{label} raster is missing a usable affine transform."
        )
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
def check_compatibility(
    before_info: dict,
    after_info: dict,
    before_is_raster: bool,
    after_is_raster: bool,
) -> dict:
    """Validate that two inputs are on the same geospatial pixel grid.

    This is a strict post-alignment check. Use :func:`preprocess_raster_pair`
    first when the rasters may differ in CRS, dimensions, resolution or extent.
    """
    if not isinstance(before_is_raster, bool) or not isinstance(after_is_raster, bool):
        raise TypeError("before_is_raster and after_is_raster must be booleans.")

    if before_is_raster != after_is_raster:
        raise SpatialInputError(
            "unsupported_input_pair",
            "A raster and an ordinary image cannot be assumed to share "
            "geographic coordinates.",
        )

    if not before_is_raster:
        # Both are ordinary images -- pixel‑space comparison is fine.
        return {"compatible": True}

    before = _validated_spatial_metadata(before_info, "Before")
    after = _validated_spatial_metadata(after_info, "After")
    before_crs, before_transform, before_width, before_height, before_bounds, _ = before
    after_crs, after_transform, after_width, after_height, after_bounds, _ = after

    if HAS_RASTERIO:
        try:
            before_crs = rasterio.crs.CRS.from_user_input(before_crs)
            after_crs = rasterio.crs.CRS.from_user_input(after_crs)
        except Exception:
            raise SpatialInputError("invalid_crs", "A raster has an invalid coordinate reference system.") from None
    if before_crs != after_crs:
        raise SpatialInputError("crs_mismatch", f"CRS mismatch: before is {before_crs}, after is {after_crs}")

    if (before_width, before_height) != (after_width, after_height):
        raise SpatialInputError(
            "dimension_mismatch",
            f"Dimension mismatch: before {before_width}x{before_height} vs after {after_width}x{after_height}",
        )

    before_x_res = math.hypot(before_transform[0], before_transform[3])
    before_y_res = math.hypot(before_transform[1], before_transform[4])
    after_x_res = math.hypot(after_transform[0], after_transform[3])
    after_y_res = math.hypot(after_transform[1], after_transform[4])

    tolerance = 1e-6

    if not (math.isclose(before_x_res, after_x_res, rel_tol=0.0, abs_tol=tolerance)
            and math.isclose(before_y_res, after_y_res, rel_tol=0.0, abs_tol=tolerance)):
        raise SpatialInputError(
            "resolution_mismatch",
            "Pixel resolution differs between before and after rasters.",
        )

    if any(not math.isclose(a, b, rel_tol=0.0, abs_tol=tolerance)
           for a, b in zip(before_bounds, after_bounds)):
        raise SpatialInputError(
            "extent_mismatch",
            "Spatial extent differs between before and after rasters.",
        )

    if any(not math.isclose(a, b, rel_tol=0.0, abs_tol=tolerance)
           for a, b in zip(before_transform, after_transform)):
        raise SpatialInputError(
            "transform_mismatch",
            "Affine grid alignment differs between before and after rasters.",
        )

    return {"compatible": True}


def _parse_crs(value, label="Target"):
    try:
        crs = rasterio.crs.CRS.from_user_input(value)
    except Exception:
        raise SpatialInputError("invalid_crs", f"{label} CRS is invalid.") from None
    if crs is None:
        raise SpatialInputError("invalid_crs", f"{label} CRS is invalid.")
    return crs


def _coerce_transform(value, label="Target"):
    try:
        if isinstance(value, rasterio.Affine):
            transform = value
        else:
            coefficients = tuple(value)
            if len(coefficients) != 6:
                raise ValueError
            transform = rasterio.Affine(*coefficients)
        values = tuple(float(v) for v in transform)[:6]
    except Exception:
        raise SpatialInputError("invalid_transform", f"{label} affine transform is invalid.") from None
    if len(values) != 6 or not all(math.isfinite(v) for v in values):
        raise SpatialInputError("invalid_transform", f"{label} affine transform is invalid.")
    if transform.a * transform.e - transform.b * transform.d == 0.0:
        raise SpatialInputError("invalid_transform", f"{label} affine transform is singular.")
    return transform


def _validate_resolution(resolution):
    try:
        if len(resolution) != 2:
            raise ValueError
        xres, yres = float(resolution[0]), float(resolution[1])
    except (TypeError, ValueError, IndexError):
        raise SpatialInputError("invalid_resolution", "Target resolution must contain two positive numbers.") from None
    if not math.isfinite(xres) or not math.isfinite(yres) or xres <= 0 or yres <= 0:
        raise SpatialInputError("invalid_resolution", "Target resolution must contain two positive finite numbers.")
    return xres, yres


def _resampling_method(name):
    if not isinstance(name, str):
        raise SpatialInputError("invalid_resampling", "Unsupported resampling method.")
    try:
        return {
            "nearest": Resampling.nearest,
            "bilinear": Resampling.bilinear,
            "cubic": Resampling.cubic,
            "mode": Resampling.mode,
            "average": Resampling.average,
        }[name.lower()]
    except (KeyError, AttributeError):
        raise SpatialInputError("invalid_resampling", f"Unsupported resampling method: {name}.") from None
def reproject_raster(
    file_bytes: bytes,
    target_crs,
    target_transform,
    target_resolution: tuple[float, float],
    *,
    resampling: str = "bilinear",
    target_width: int | None = None,
    target_height: int | None = None,
) -> bytes:
    """Reproject a GeoTIFF to a new CRS, transform, and resolution.

    Parameters
    ----------
    file_bytes : bytes
        Input GeoTIFF file bytes.
    target_crs : rasterio.crs.CRS or str
        Target coordinate reference system.
    target_transform : tuple[float, ...]
        Target affine transform (6 coefficients).
    target_resolution : tuple[float, float]
        Target (x, y) pixel resolution.
    resampling : {"nearest", "bilinear"}, optional
        Resampling method. Use ``"nearest"`` for categorical data and
        ``"bilinear"`` for continuous data. Defaults to ``"bilinear"``.

    Returns
    -------
    bytes
        Reprojected GeoTIFF file bytes.
    """
    if not HAS_RASTERIO:
        raise RuntimeError("rasterio is not available")
    from rasterio.io import MemoryFile
    target_crs_obj = _parse_crs(target_crs)
    anchor_transform = _coerce_transform(target_transform)
    xres, yres = _validate_resolution(target_resolution)
    method = _resampling_method(resampling)
    for name, dimension in (("target_width", target_width), ("target_height", target_height)):
        if dimension is not None and (not isinstance(dimension, int) or isinstance(dimension, bool) or dimension <= 0):
            raise SpatialInputError("invalid_dimensions", f"{name} must be a positive integer.")
    if (target_width is None) != (target_height is None):
        raise SpatialInputError(
            "invalid_dimensions",
            "target_width and target_height must be provided together.",
        )

    try:
        with MemoryFile(file_bytes) as source_mem, MemoryFile() as destination_mem:
            with source_mem.open() as src:
                if src.crs is None:
                    raise SpatialInputError("missing_crs", "Source raster is missing a coordinate reference system.")
                if src.transform is None or src.transform.is_identity:
                    raise SpatialInputError("missing_transform", "Source raster is missing a usable affine transform.")
                source_coefficients = tuple(float(value) for value in src.transform)[:6]
                if not all(math.isfinite(value) for value in source_coefficients):
                    raise SpatialInputError(
                        "invalid_transform",
                        "Source raster affine transform contains non-finite coefficients.",
                    )
                a, b, _c, d, e, _f = source_coefficients
                if a * e - b * d == 0.0:
                    raise SpatialInputError(
                        "invalid_transform",
                        "Source raster affine transform is singular.",
                    )
                _parse_crs(src.crs, "Source")
                if src.count <= 0 or src.width <= 0 or src.height <= 0:
                    raise SpatialInputError("invalid_metadata", "Source raster has invalid dimensions or bands.")

                # Scale the supplied grid basis to the requested pixel sizes while
                # preserving its origin and rotation/shear orientation.
                xlen = math.hypot(anchor_transform.a, anchor_transform.d)
                ylen = math.hypot(anchor_transform.b, anchor_transform.e)
                if xlen <= 0 or ylen <= 0:
                    raise SpatialInputError("invalid_transform", "Target affine transform has invalid pixel vectors.")
                if target_width is not None and target_height is not None:
                    # Exact-grid callers (notably pair preprocessing) supply
                    # dimensions and an affine transform that is authoritative.
                    grid = anchor_transform
                else:
                    grid = rasterio.Affine(
                        anchor_transform.a * xres / xlen,
                        anchor_transform.b * yres / ylen,
                        anchor_transform.c,
                        anchor_transform.d * xres / xlen,
                        anchor_transform.e * yres / ylen,
                        anchor_transform.f,
                    )
                if target_width is None or target_height is None:
                    try:
                        bounds = _rio_warp.transform_bounds(src.crs, target_crs_obj, *src.bounds, densify_pts=21)
                        inverse = ~grid
                        corners = [inverse * (x, y) for x in (bounds[0], bounds[2]) for y in (bounds[1], bounds[3])]
                        col0, row0 = math.floor(min(p[0] for p in corners)), math.floor(min(p[1] for p in corners))
                        col1, row1 = math.ceil(max(p[0] for p in corners)), math.ceil(max(p[1] for p in corners))
                    except Exception:
                        raise SpatialInputError("invalid_transform", "Could not calculate a target grid from the supplied CRS and transform.") from None
                    width = target_width if target_width is not None else col1 - col0
                    height = target_height if target_height is not None else row1 - row0
                    output_transform = grid * rasterio.Affine.translation(col0, row0)
                else:
                    width, height = target_width, target_height
                    output_transform = grid
                if width <= 0 or height <= 0:
                    raise SpatialInputError("invalid_dimensions", "Calculated target raster dimensions are invalid.")

                profile = src.profile.copy()
                profile.update(
                    driver="GTiff", width=width, height=height, count=src.count,
                    crs=target_crs_obj, transform=output_transform,
                )
                with destination_mem.open(**profile) as dst:
                    for band_index in range(1, src.count + 1):
                        _rio_warp.reproject(
                            source=rasterio.band(src, band_index),
                            destination=rasterio.band(dst, band_index),
                            src_transform=src.transform,
                            src_crs=src.crs,
                            src_nodata=src.nodata,
                            dst_transform=output_transform,
                            dst_crs=target_crs_obj,
                            dst_nodata=src.nodata,
                            resampling=method,
                        )
                    dst.update_tags(**src.tags())
                    for band_index in range(1, src.count + 1):
                        dst.update_tags(band_index, **src.tags(band_index))
                    dst.descriptions = src.descriptions
                    dst.units = src.units
            return destination_mem.read()
    except SpatialInputError:
        raise
    except Exception as exc:
        raise SpatialInputError("invalid_raster", f"Could not reproject raster: {exc}") from None


def _inspect_input(file_bytes: bytes):
    """Return (is_raster, metadata); distinguish geospatial rasters from images."""
    from PIL import Image
    from rasterio.io import MemoryFile

    try:
        with MemoryFile(file_bytes) as mem, mem.open() as dataset:
            is_raster = dataset.driver not in {"PNG", "JPEG", "WEBP"}
            if not is_raster:
                return False, None
            return True, {
                "crs": dataset.crs,
                "crs_obj": dataset.crs,
                "transform": dataset.transform,
                "width": dataset.width,
                "height": dataset.height,
                "bounds": tuple(dataset.bounds),
            }
    except Exception:
        pass
    try:
        with Image.open(BytesIO(file_bytes)) as image:
            image.verify()
        return False, None
    except Exception:
        raise SpatialInputError("invalid_input", "Input is neither a supported raster nor an ordinary image.") from None
def preprocess_raster_pair(
    before_bytes: bytes,
    after_bytes: bytes,
) -> dict:
    """Preprocess a raster pair for geospatial change detection.

    Uses the ``before`` raster as the default reference grid. The ``after``
    raster is reprojected/resampled to match the before raster's CRS, transform,
    resolution, and extent. Nodata and geospatial metadata are preserved.

    Parameters
    ----------
    before_bytes : bytes
        GeoTIFF bytes for the earlier (before) image.
    after_bytes : bytes
        GeoTIFF bytes for the later (after) image.

    Returns
    -------
    dict
        ``{
            "before": <bytes of before raster (unchanged)>,
            "after": <bytes of after raster reprojected to before's grid>,
            "reference_info": <metadata dict from read_georeference of before>,
            "note": <descriptive string>
        }``

    Raises
    ------
    SpatialInputError
        If the pair is mixed (one raster, one ordinary image) or if the rasters
        cannot be made compatible.
    RuntimeError
        If rasterio is not available.
    """
    if not HAS_RASTERIO:
        raise RuntimeError("rasterio is not available")
    before_is_raster, before_info = _inspect_input(before_bytes)
    after_is_raster, after_info = _inspect_input(after_bytes)
    if before_is_raster != after_is_raster:
        raise SpatialInputError("unsupported_input_pair", "A raster and an ordinary image cannot be compared as a pair.")
    if not before_is_raster:
        return {
            "before": before_bytes, "after": after_bytes, "reference_info": None,
            "note": "Both inputs are ordinary images; preserved unchanged for pixel-space comparison.",
        }
    before_info = _validated_spatial_metadata(before_info, "Before")
    after_info = _validated_spatial_metadata(after_info, "After")
    # Use the actual before grid as the exact output reference, regardless of
    # after's CRS, dimensions, resolution or coverage.
    with rasterio.MemoryFile(before_bytes) as mem, mem.open() as ref:
        reference_crs = ref.crs
        reference_transform = ref.transform
        width, height = ref.width, ref.height
        resolution = (math.hypot(reference_transform.a, reference_transform.d), math.hypot(reference_transform.b, reference_transform.e))
    same_grid = (
        before_info[0] == after_info[0]
        and before_info[1] == after_info[1]
        and before_info[2:4] == after_info[2:4]
    )
    if same_grid:
        after_processed = after_bytes
        note = "Pair already shares the before raster grid; no reprojection was needed."
    else:
        after_processed = reproject_raster(
            after_bytes, target_crs=reference_crs, target_transform=reference_transform,
            target_resolution=resolution, resampling="bilinear", target_width=width, target_height=height,
        )
        note = "Pair preprocessed: after raster reprojected to the exact before raster grid."
    after_aligned_is_raster, after_aligned_info = _inspect_input(after_processed)
    if not after_aligned_is_raster:
        raise SpatialInputError("invalid_raster", "Aligned after input is not a readable geospatial raster.")
    check_compatibility(
        {"crs_obj": reference_crs, "transform": reference_transform, "width": width, "height": height,
         "bounds": tuple(rasterio.transform.array_bounds(height, width, reference_transform))},
        after_aligned_info, True, True,
    )
    with rasterio.MemoryFile(before_bytes) as mem, mem.open() as reference:
        reference_info = {
            "crs": reference.crs.to_string(), "crs_obj": reference.crs,
            "crs_is_geographic": bool(reference.crs.is_geographic), "transform": reference.transform,
            "width": reference.width, "height": reference.height,
            "bounds": tuple(float(value) for value in reference.bounds),
        }
    return {"before": before_bytes, "after": after_processed, "reference_info": reference_info, "note": note}
