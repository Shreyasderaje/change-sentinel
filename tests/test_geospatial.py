"""Tests for the optional georeferenced-GeoTIFF path.

These tests only run when the optional ``rasterio`` dependency is
installed (see README — it is not a core requirement). They build a
small synthetic georeferenced raster in memory and verify that:

* the georeference is read from the file's real metadata,
* pixel coordinates convert to plausible WGS84 lon/lat values,
* regions are annotated with geographic coordinates,
* the Folium map builder accepts the annotated regions,
* an ordinary PNG (no metadata) never yields coordinates.
"""

import io

import numpy as np
import pytest

from utils import change_detection as cd
from utils import geospatial
from utils import map_generation as mapgen

# Location of the synthetic raster: roughly central Bangalore in UTM 43N.
UTM43_ORIGIN_EASTING = 760000.0
UTM43_ORIGIN_NORTHING = 1430000.0


def make_rgb(height=128, width=128, seed=0):
    rng = np.random.default_rng(seed)
    base = np.zeros((height, width, 3), dtype=np.int16)
    base[...] = (100, 120, 140)
    noise = rng.integers(-8, 9, size=(height, width, 3), dtype=np.int16)
    return np.clip(base + noise, 0, 255).astype(np.uint8)


def geotiff_bytes(array, crs="EPSG:32643", transform=None):
    """Encode an RGB array as a georeferenced GeoTIFF in memory."""
    import rasterio
    from rasterio.transform import from_origin

    if transform is None:
        transform = from_origin(
            UTM43_ORIGIN_EASTING, UTM43_ORIGIN_NORTHING, 10.0, 10.0
        )
    buffer = io.BytesIO()
    with rasterio.MemoryFile() as memory:
        with memory.open(
            driver="GTiff",
            height=array.shape[0],
            width=array.shape[1],
            count=3,
            dtype="uint8",
            crs=crs,
            transform=transform,
        ) as dataset:
            dataset.write(array[:, :, 0], 1)
            dataset.write(array[:, :, 1], 2)
            dataset.write(array[:, :, 2], 3)
        buffer.write(memory.read())
    return buffer.getvalue()


def spatial_info(
    *,
    crs="EPSG:32643",
    width=128,
    height=128,
    transform=(10.0, 0.0, 760000.0, 0.0, -10.0, 1430000.0),
):
    """Build georeference metadata without requiring the optional rasterio package."""
    a, b, c, d, e, f = transform
    corners = [
        (c, f),
        (a * width + c, d * width + f),
        (b * height + c, e * height + f),
        (a * width + b * height + c, d * width + e * height + f),
    ]
    return {
        "crs": crs,
        "crs_obj": crs,
        "transform": transform,
        "width": width,
        "height": height,
        "bounds": (
            min(point[0] for point in corners),
            min(point[1] for point in corners),
            max(point[0] for point in corners),
            max(point[1] for point in corners),
        ),
    }


def test_spatial_contract_accepts_identical_georeferenced_grids():
    result = geospatial.validate_spatial_pair(
        spatial_info(),
        spatial_info(),
        before_is_raster=True,
        after_is_raster=True,
    )

    assert result["mode"] == "geospatial"
    assert result["georeferenced"] is True


def test_spatial_contract_keeps_ordinary_images_in_explicit_pixel_mode():
    result = geospatial.validate_spatial_pair(
        None,
        None,
        before_is_raster=False,
        after_is_raster=False,
    )

    assert result["mode"] == "pixel"
    assert result["georeferenced"] is False
    assert "no shared geographic coordinates are assumed" in result["note"]


def test_spatial_contract_rejects_mixed_raster_and_ordinary_image():
    with pytest.raises(geospatial.SpatialInputError) as exc_info:
        geospatial.validate_spatial_pair(
            spatial_info(),
            None,
            before_is_raster=True,
            after_is_raster=False,
        )

    assert exc_info.value.code == "unsupported_input_pair"
    assert "cannot be assumed to share geographic coordinates" in str(exc_info.value)


@pytest.mark.parametrize(
    ("info", "code", "message"),
    [
        (None, "missing_georeference", "CRS and affine transform"),
        (
            {key: value for key, value in spatial_info().items() if key != "crs_obj" and key != "crs"},
            "missing_crs",
            "coordinate reference system",
        ),
        (
            {key: value for key, value in spatial_info().items() if key != "transform"},
            "missing_transform",
            "affine transform",
        ),
    ],
)
def test_spatial_contract_rejects_rasters_without_required_metadata(
    info, code, message
):
    with pytest.raises(geospatial.SpatialInputError) as exc_info:
        geospatial.validate_spatial_pair(
            info,
            spatial_info(),
            before_is_raster=True,
            after_is_raster=True,
        )

    assert exc_info.value.code == code
    assert message in str(exc_info.value)


def test_spatial_contract_reports_crs_mismatch():
    with pytest.raises(geospatial.SpatialInputError) as exc_info:
        geospatial.validate_spatial_pair(
            spatial_info(crs="EPSG:32643"),
            spatial_info(crs="EPSG:32644"),
            before_is_raster=True,
            after_is_raster=True,
        )

    assert exc_info.value.code == "spatial_mismatch"
    assert "CRS differs" in str(exc_info.value)


def test_spatial_contract_reports_dimension_and_extent_mismatches():
    with pytest.raises(geospatial.SpatialInputError) as exc_info:
        geospatial.validate_spatial_pair(
            spatial_info(width=128),
            spatial_info(width=64),
            before_is_raster=True,
            after_is_raster=True,
        )

    assert exc_info.value.code == "spatial_mismatch"
    assert "raster dimensions differ" in str(exc_info.value)
    assert "spatial extent differs" in str(exc_info.value)


def test_spatial_contract_reports_resolution_and_alignment_mismatches():
    before = spatial_info()
    after = spatial_info(
        transform=(20.0, 0.0, 760000.0, 0.0, -20.0, 1430000.0)
    )

    with pytest.raises(geospatial.SpatialInputError) as exc_info:
        geospatial.validate_spatial_pair(
            before,
            after,
            before_is_raster=True,
            after_is_raster=True,
        )

    assert exc_info.value.code == "spatial_mismatch"
    assert "pixel resolution differs" in str(exc_info.value)
    assert "spatial extent differs" in str(exc_info.value)
    assert "affine grid alignment differs" in str(exc_info.value)


def test_spatial_contract_rejects_origin_shift_with_same_resolution():
    before = spatial_info()
    after = spatial_info(
        transform=(10.0, 0.0, 760010.0, 0.0, -10.0, 1430000.0)
    )

    with pytest.raises(geospatial.SpatialInputError) as exc_info:
        geospatial.validate_spatial_pair(
            before,
            after,
            before_is_raster=True,
            after_is_raster=True,
        )

    assert "spatial extent differs" in str(exc_info.value)
    assert "affine grid alignment differs" in str(exc_info.value)


@pytest.mark.skipif(
    not geospatial.rasterio_available(),
    reason="optional dependency 'rasterio' is not installed",
)
def test_georeference_is_read_from_metadata():
    array = make_rgb(seed=20)
    info, note = geospatial.read_georeference(geotiff_bytes(array))

    assert info is not None, note
    assert info["crs"] == "EPSG:32643"
    assert info["crs_is_geographic"] is False
    assert info["width"] == 128 and info["height"] == 128
    # 10 m pixels starting at the UTM origin.
    left, bottom, right, top = info["bounds"]
    assert left == pytest.approx(UTM43_ORIGIN_EASTING)
    assert top == pytest.approx(UTM43_ORIGIN_NORTHING)
    assert "Georeferenced raster detected" in note


@pytest.mark.skipif(
    not geospatial.rasterio_available(),
    reason="optional dependency 'rasterio' is not installed",
)
def test_pixel_to_lonlat_is_accurate():
    array = make_rgb(seed=21)
    info, _ = geospatial.read_georeference(geotiff_bytes(array))

    # UTM 43N easting ~760,000 m / northing ~1,430,000 m at 10 m/px
    # corresponds to roughly 77.4E, 12.93N (near Bangalore).
    lon0, lat0 = geospatial.pixel_to_lonlat(0, 0, info)
    assert 77.3 < lon0 < 77.5
    assert 12.9 < lat0 < 13.0

    # Ten pixels east (100 m) must increase longitude; ten pixels south
    # (100 m) must decrease latitude.
    lon_east, _ = geospatial.pixel_to_lonlat(10, 0, info)
    _, lat_south = geospatial.pixel_to_lonlat(0, 10, info)
    assert lon_east > lon0
    assert lat_south < lat0


@pytest.mark.skipif(
    not geospatial.rasterio_available(),
    reason="optional dependency 'rasterio' is not installed",
)
def test_regions_annotated_with_geographic_coordinates():
    before = make_rgb(seed=22)
    after = before.copy()
    after[30:90, 40:110] = (25, 25, 30)

    info, _ = geospatial.read_georeference(geotiff_bytes(before))
    _, _, regions, _ = cd.detect_changes(before, after)
    annotated = geospatial.annotate_regions(regions, info)

    assert annotated
    for region in annotated:
        assert region["centroid_lonlat"] is not None
        lon, lat = region["centroid_lonlat"]
        assert -180 <= lon <= 180 and -90 <= lat <= 90
        assert region["bbox_lonlat"] is not None


@pytest.mark.skipif(
    not geospatial.rasterio_available(),
    reason="optional dependency 'rasterio' is not installed",
)
def test_folium_map_builds_for_annotated_regions():
    before = make_rgb(seed=23)
    after = before.copy()
    after[30:90, 40:110] = (25, 25, 30)

    info, _ = geospatial.read_georeference(geotiff_bytes(before))
    _, _, regions, _ = cd.detect_changes(before, after)
    annotated = geospatial.annotate_regions(regions, info)

    if mapgen.folium_available():
        fmap = mapgen.build_change_map(annotated, info)
        assert fmap is not None
    else:
        assert mapgen.build_change_map(annotated, info) is None


@pytest.mark.skipif(
    not geospatial.rasterio_available(),
    reason="optional dependency 'rasterio' is not installed",
)
def test_untagged_raster_yields_no_coordinates():
    """A TIFF without a CRS must NOT produce geographic coordinates."""
    array = make_rgb(seed=24)
    import rasterio
    from rasterio.transform import from_origin

    with rasterio.MemoryFile() as memory:
        with memory.open(
            driver="GTiff",
            height=array.shape[0],
            width=array.shape[1],
            count=3,
            dtype="uint8",
            transform=from_origin(0.0, 0.0, 10.0, 10.0),
        ) as dataset:
            dataset.write(array[:, :, 0], 1)
            dataset.write(array[:, :, 1], 2)
            dataset.write(array[:, :, 2], 3)
        payload = memory.read()

    assert payload is not None
    info, note = geospatial.read_georeference(payload)
    assert info is None
    assert "coordinate reference system" in note


def test_plain_png_never_yields_georeference():
    from PIL import Image

    buffer = io.BytesIO()
    Image.fromarray(make_rgb(seed=25)).save(buffer, format="PNG")
    info, note = geospatial.read_georeference(buffer.getvalue())
    assert info is None
    assert note  # an explanatory note is always provided
