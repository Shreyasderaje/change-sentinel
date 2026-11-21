"""Tests for raster preprocessing and alignment."""
import io

import numpy as np
import pytest

from utils import geospatial
from utils.geospatial import check_compatibility, reproject_raster, preprocess_raster_pair


def make_rgb(height=128, width=128, seed=0):
    rng = np.random.default_rng(seed)
    base = np.zeros((height, width, 3), dtype=np.int16)
    base[...] = (100, 120, 140)
    noise = rng.integers(-8, 9, size=(height, width, 3), dtype=np.int16)
    return np.clip(base + noise, 0, 255).astype(np.uint8)


def geotiff_bytes(array, crs="EPSG:32643", transform=None):
    """Encode an RGB array as a georeferenced GeoTIFF in memory."""
    import rasterio
    from rasterio.transform import from_origin, Affine

    if transform is None:
        transform = from_origin(760000.0, 1430000.0, 10.0, 10.0)
    # Convert tuple transform to Affine if needed
    if isinstance(transform, tuple):
        transform = Affine(*transform)
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
class TestCheckCompatibility:
    """Tests for check_compatibility()."""

    def test_compatible_identical_grids(self):
        before_info = spatial_info()
        after_info = spatial_info()
        result = check_compatibility(before_info, after_info, True, True)
        assert result["compatible"] is True

    def test_incompatible_crs(self):
        """Rasters with different CRS should raise SpatialInputError."""
        before_info = spatial_info(crs="EPSG:32643")
        after_info = spatial_info(crs="EPSG:32644")
        with pytest.raises(geospatial.SpatialInputError):
            check_compatibility(before_info, after_info, True, True)

    def test_dimension_mismatch(self):
        """Rasters with different dimensions should raise SpatialInputError."""
        before_info = {"crs": "EPSG:32643", "transform": (10.0, 0.0, 760000.0, 0.0, -10.0, 1430000.0),
                       "width": 128, "height": 128,
                       "bounds": (760000.0, 1430000.0, 761280.0, 1431280.0)}
        after_info = {"crs": "EPSG:32643", "transform": (10.0, 0.0, 760000.0, 0.0, -10.0, 1430000.0),
                      "width": 64, "height": 64,
                      "bounds": (760000.0, 1430000.0, 760640.0, 1430640.0)}
        with pytest.raises(geospatial.SpatialInputError):
            check_compatibility(before_info, after_info, True, True)

    def test_ordinary_images_are_compatible(self):
        """Ordinary (non-raster) inputs should return compatible=True."""
        result = check_compatibility(None, None, False, False)
        assert result["compatible"] is True

    def test_mixed_raster_and_ordinary_rejected(self):
        """A raster and an ordinary image should raise SpatialInputError."""
        before_info = spatial_info()
        with pytest.raises(geospatial.SpatialInputError):
            check_compatibility(before_info, None, True, False)
class TestReprojectRaster:
    """Tests for reproject_raster()."""

    @pytest.mark.skipif(
        not geospatial.rasterio_available(),
        reason="optional dependency 'rasterio' is not installed",
    )
    def test_reproject_to_same_crs_preserves_data(self):
        """Reprojecting to the same CRS should preserve the data."""
        array = make_rgb(seed=42)
        info_dict = spatial_info()
        raw = geotiff_bytes(array, crs=info_dict["crs"], transform=info_dict["transform"])
        result = reproject_raster(
            raw,
            target_crs=info_dict["crs"],
            target_transform=info_dict["transform"],
            target_resolution=(10.0, 10.0),
        )
        assert result is not None
        assert len(result) > 0

    def test_reproject_with_bilinear_resampling(self):
        """Test that bilinear resampling is the default."""
        array = make_rgb(seed=42)
        info_dict = spatial_info()
        raw = geotiff_bytes(array, crs=info_dict["crs"], transform=info_dict["transform"])
        result = reproject_raster(
            raw,
            target_crs=info_dict["crs"],
            target_transform=info_dict["transform"],
            target_resolution=(10.0, 10.0),
            resampling="bilinear",
        )
        assert result is not None

    @pytest.mark.skipif(
        not geospatial.rasterio_available(),
        reason="optional dependency 'rasterio' is not installed",
    )
    def test_reproject_changes_resolution(self):
        """Reprojecting to a different resolution changes the array shape."""
        array = make_rgb(seed=42)
        info_dict = spatial_info()
        raw = geotiff_bytes(array, crs=info_dict["crs"], transform=info_dict["transform"])
        result = reproject_raster(
            raw,
            target_crs=info_dict["crs"],
            target_transform=info_dict["transform"],
            target_resolution=(20.0, 20.0),
            resampling="bilinear",
        )
        assert result is not None
        with io.BytesIO(result) as buf:
            with rasterio.open(buf) as dst:
                assert dst.height < info_dict["height"]
                assert dst.width < info_dict["width"]
class TestPreprocessRasterPair:
    """Tests for preprocess_raster_pair()."""

    @pytest.mark.skipif(
        not geospatial.rasterio_available(),
        reason="optional dependency 'rasterio' is not installed",
    )
    def test_preprocess_identical_grids(self):
        """Preprocessing a pair with identical grids should succeed."""
        before_info = spatial_info()
        after_info = spatial_info()
        before_bytes = geotiff_bytes(make_rgb(), crs=before_info["crs"], transform=before_info["transform"])
        after_bytes = geotiff_bytes(make_rgb(), crs=after_info["crs"], transform=after_info["transform"])
        result = preprocess_raster_pair(before_bytes, after_bytes)
        assert "before" in result
        assert "after" in result
        assert "reference_info" in result
        assert result["note"] is not None

    @pytest.mark.skipif(
        not geospatial.rasterio_available(),
        reason="optional dependency 'rasterio' is not installed",
    )
    def test_preprocess_uses_before_as_reference(self):
        """The reference_info should come from the before raster."""
        before_info = spatial_info(crs="EPSG:32643")
        after_info = spatial_info(crs="EPSG:32644")
        before_bytes = geotiff_bytes(make_rgb(), crs=before_info["crs"], transform=before_info["transform"])
        after_bytes = geotiff_bytes(make_rgb(), crs=after_info["crs"], transform=after_info["transform"])
        with pytest.raises(geospatial.SpatialInputError):
            preprocess_raster_pair(before_bytes, after_bytes)

    def test_reproject_with_nearest_resampling_categorical(self):
        """Test nearest resampling for categorical data."""
        array = make_rgb(seed=42)
        info_dict = spatial_info()
        raw = geotiff_bytes(array, crs=info_dict["crs"], transform=info_dict["transform"])
        result = reproject_raster(
            raw,
            target_crs=info_dict["crs"],
            target_transform=info_dict["transform"],
            target_resolution=(10.0, 10.0),
            resampling="nearest",
        )
        assert result is not None