"""Tests for raster grid validation, reprojection, and image passthrough."""

import io

import numpy as np
import pytest

import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_origin, from_bounds
from rasterio.warp import transform_bounds

from utils import geospatial
from utils.geospatial import check_compatibility, preprocess_raster_pair, reproject_raster


def geotiff_bytes(data, *, crs="EPSG:32643", transform=None, nodata=None, tags=None):
    """Create a TIFF from (bands, height, width) data or RGB (height,width,3)."""
    data = np.asarray(data)
    if data.ndim == 2:
        data = data[np.newaxis, ...]
    elif data.ndim == 3 and data.shape[-1] in (3, 4):
        data = data.transpose(2, 0, 1)
    if transform is None:
        transform = from_origin(760000.0, 1430000.0, 10.0, 10.0)
    with rasterio.MemoryFile() as memory:
        with memory.open(
            driver="GTiff", height=data.shape[1], width=data.shape[2],
            count=data.shape[0], dtype=data.dtype, crs=crs,
            transform=transform, nodata=nodata,
        ) as dataset:
            dataset.write(data)
            if tags:
                dataset.update_tags(**tags)
        return memory.read()


def read_tiff(payload):
    with rasterio.MemoryFile(payload) as memory, memory.open() as dataset:
        return dataset


def rgb(height=128, width=128, seed=7):
    rng = np.random.default_rng(seed)
    return rng.integers(0, 255, (height, width, 3), dtype=np.uint8)


def test_check_compatibility_preserves_ordinary_pairs_and_rejects_mixed():
    assert check_compatibility(None, None, False, False)["compatible"] is True
    with pytest.raises(geospatial.SpatialInputError) as err:
        check_compatibility(None, None, True, False)
    assert err.value.code == "unsupported_input_pair"


def test_same_grid_pair_is_preserved_without_reprojection(monkeypatch):
    payload = geotiff_bytes(rgb())
    monkeypatch.setattr(geospatial, "reproject_raster", lambda *a, **k: pytest.fail("unneeded reprojection"))
    result = preprocess_raster_pair(payload, payload)
    assert result["after"] == payload
    assert result["before"] == payload
    assert result["reference_info"]["width"] == 128
    assert "no reprojection" in result["note"]


@pytest.mark.parametrize(
    "shape,transform",
    [((3, 64, 64), from_origin(760000, 1430000, 20, 20)),
     ((3, 256, 256), from_origin(760000, 1430000, 5, 5))],
)
def test_different_dimensions_and_resolutions_align_to_before(shape, transform):
    before = geotiff_bytes(rgb(128, 128), transform=from_origin(760000, 1430000, 10, 10))
    after = geotiff_bytes(np.ones(shape, dtype=np.uint8), transform=transform)
    aligned = preprocess_raster_pair(before, after)
    with rasterio.MemoryFile(aligned["after"]) as memory, memory.open() as dataset:
        with rasterio.MemoryFile(before) as before_memory, before_memory.open() as reference:
            assert (dataset.width, dataset.height) == (reference.width, reference.height)
            assert dataset.transform == reference.transform
            assert dataset.crs == reference.crs


def test_different_crs_is_reprojected_not_rejected():
    before_transform = from_origin(760000, 1430000, 10, 10)
    before = geotiff_bytes(rgb(), crs="EPSG:32643", transform=before_transform)
    left, bottom, right, top = transform_bounds(
        "EPSG:32643", "EPSG:4326", 760000, 1428720, 761280, 1430000, densify_pts=21
    )
    after = geotiff_bytes(
        np.ones((3, 64, 64), dtype=np.uint8), crs="EPSG:4326",
        transform=from_bounds(left, bottom, right, top, 64, 64),
    )
    result = preprocess_raster_pair(before, after)
    with rasterio.MemoryFile(result["after"]) as memory, memory.open() as aligned:
        assert aligned.crs == CRS.from_epsg(32643)
        assert (aligned.width, aligned.height) == (128, 128)
        assert aligned.transform == before_transform


def test_reproject_preserves_all_bands_dtype_nodata_and_metadata():
    data = np.arange(4 * 32 * 32, dtype=np.uint16).reshape(4, 32, 32)
    data[:, 0, 0] = 65535
    source = geotiff_bytes(data, nodata=65535, tags={"sensor": "test-sensor"})
    target_transform = from_origin(760000, 1430000, 10, 10)
    output = reproject_raster(
        source, "EPSG:32643", target_transform, (10, 10),
        target_width=32, target_height=32, resampling="nearest",
    )
    with rasterio.MemoryFile(output) as memory, memory.open() as result:
        assert result.count == 4
        assert result.dtypes == ("uint16",) * 4
        assert result.nodata == 65535
        assert result.transform == target_transform
        assert (result.width, result.height) == (32, 32)
        assert result.tags()["sensor"] == "test-sensor"
        np.testing.assert_array_equal(result.read(), data)


@pytest.mark.parametrize("dimension_name", ["target_width", "target_height"])
def test_partial_target_dimensions_are_rejected(dimension_name):
    kwargs = {dimension_name: 64}
    with pytest.raises(geospatial.SpatialInputError, match="provided together") as err:
        reproject_raster(
            geotiff_bytes(rgb()), "EPSG:32643", from_origin(760000, 1430000, 10, 10),
            (10, 10), **kwargs,
        )
    assert err.value.code == "invalid_dimensions"


@pytest.mark.parametrize("method", ["nearest", "bilinear", "cubic", "mode", "average"])
def test_supported_resampling_methods(method):
    source = geotiff_bytes(rgb())
    output = reproject_raster(
        source, "EPSG:32643", from_origin(760000, 1430000, 10, 10), (10, 10),
        target_width=128, target_height=128, resampling=method,
    )
    with rasterio.MemoryFile(output) as memory, memory.open() as dataset:
        assert dataset.width == 128


def test_bilinear_resamples_between_resolutions():
    source = geotiff_bytes(rgb(64, 64), transform=from_origin(760000, 1430000, 20, 20))
    output = reproject_raster(
        source, "EPSG:32643", from_origin(760000, 1430000, 10, 10), (10, 10),
        target_width=128, target_height=128, resampling="bilinear",
    )
    with rasterio.MemoryFile(output) as memory, memory.open() as dataset:
        assert (dataset.width, dataset.height) == (128, 128)


def test_dimensions_derived_on_grid_anchored_to_transform():
    source = geotiff_bytes(rgb(40, 60), transform=from_origin(760003, 1430007, 10, 10))
    output = reproject_raster(
        source, "EPSG:32643", from_origin(760000, 1430010, 20, 20), (20, 20)
    )
    with rasterio.MemoryFile(output) as memory, memory.open() as dataset:
        assert dataset.width > 0 and dataset.height > 0
        assert (dataset.transform.c - 760000) % 20 == pytest.approx(0)
        assert (1430010 - dataset.transform.f) % 20 == pytest.approx(0)


def test_rotated_sheared_target_grid_preserves_transform_and_dimensions():
    target_transform = rasterio.Affine(10, 2, 760000, 1, -10, 1430000)
    output = reproject_raster(
        geotiff_bytes(rgb(32, 32)), "EPSG:32643", target_transform,
        (np.hypot(10, 1), np.hypot(2, -10)), target_width=23, target_height=17,
    )
    with rasterio.MemoryFile(output) as memory, memory.open() as dataset:
        assert dataset.transform == target_transform
        assert (dataset.width, dataset.height) == (23, 17)


@pytest.mark.parametrize(
    "transform",
    [rasterio.Affine(1, 0, 0, 0, 0, 0),
     rasterio.Affine(float("nan"), 0, 0, 0, -1, 0)],
)
def test_source_singular_or_nonfinite_affine_is_rejected(transform):
    source = geotiff_bytes(rgb(8, 8), transform=transform)
    with pytest.raises(geospatial.SpatialInputError) as err:
        reproject_raster(source, "EPSG:32643", from_origin(0, 80, 1, 1), (1, 1))
    assert err.value.code == "invalid_transform"


@pytest.mark.parametrize(
    "kwargs,code",
    [({"resampling": "lanczos"}, "invalid_resampling"),
     ({"target_crs": "not-a-real-crs"}, "invalid_crs"),
     ({"target_resolution": (0, 10)}, "invalid_resolution"),
     ({"target_transform": rasterio.Affine(0, 0, 0, 0, 0, 0)}, "invalid_transform")],
)
def test_invalid_reproject_parameters_raise_spatial_input_error(kwargs, code):
    source = geotiff_bytes(rgb())
    args = {
        "target_crs": "EPSG:32643",
        "target_transform": from_origin(760000, 1430000, 10, 10),
        "target_resolution": (10, 10),
    }
    args.update(kwargs)
    with pytest.raises(geospatial.SpatialInputError) as err:
        reproject_raster(source, **args)
    assert err.value.code == code


def test_reproject_rejects_missing_source_crs_and_transform():
    payload = geotiff_bytes(rgb(), crs=None)
    with pytest.raises(geospatial.SpatialInputError) as err:
        reproject_raster(payload, "EPSG:32643", from_origin(0, 0, 10, 10), (10, 10))
    assert err.value.code == "missing_crs"
    with rasterio.MemoryFile() as memory:
        with memory.open(
            driver="GTiff", height=16, width=16, count=1, dtype="uint8", crs="EPSG:32643"
        ) as dataset:
            dataset.write(np.zeros((1, 16, 16), dtype=np.uint8))
        no_transform = memory.read()
    with pytest.raises(geospatial.SpatialInputError) as err:
        reproject_raster(no_transform, "EPSG:32643", from_origin(0, 0, 10, 10), (10, 10))
    assert err.value.code == "missing_transform"


def test_invalid_resampling_rejected():
    with pytest.raises(geospatial.SpatialInputError) as err:
        reproject_raster(
            geotiff_bytes(rgb()), "EPSG:32643", from_origin(760000, 1430000, 10, 10),
            (10, 10), resampling="invented",
        )
    assert err.value.code == "invalid_resampling"


def test_mixed_raster_and_image_rejected_and_images_passthrough():
    from PIL import Image

    image_io = io.BytesIO()
    Image.fromarray(rgb()).save(image_io, format="PNG")
    image = image_io.getvalue()
    with pytest.raises(geospatial.SpatialInputError) as err:
        preprocess_raster_pair(geotiff_bytes(rgb()), image)
    assert err.value.code == "unsupported_input_pair"
    result = preprocess_raster_pair(image, image)
    assert result["before"] == image and result["after"] == image
    assert result["reference_info"] is None


def test_preprocess_requires_geospatial_metadata():
    unreferenced = geotiff_bytes(rgb(), crs=None)
    with pytest.raises(geospatial.SpatialInputError) as err:
        preprocess_raster_pair(unreferenced, unreferenced)
    assert err.value.code == "missing_crs"


def test_strict_compatibility_checks_affine_grid_alignment():
    before = {
        "crs": "EPSG:32643", "transform": from_origin(0, 100, 10, 10),
        "width": 10, "height": 10, "bounds": (0, 0, 100, 100),
    }
    after = {
        "crs": "EPSG:32643", "transform": from_origin(1, 101, 10, 10),
        "width": 10, "height": 10, "bounds": (1, 1, 101, 101),
    }
    with pytest.raises(geospatial.SpatialInputError):
        check_compatibility(before, after, True, True)
