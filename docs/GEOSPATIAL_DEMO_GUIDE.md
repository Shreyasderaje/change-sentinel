# Geospatial Demo Guide

## 1. Supported Geospatial Input Formats

The Change Sentinel geospatial module supports the following input formats:

- **GeoTIFF** (`*.tif`, `*.tiff`): Fully georeferenced rasters with coordinate reference system (CRS) and affine transform metadata. These are the primary format for change detection analysis when `rasterio` is installed.
- **Ordinary JPG/PNG** (`*.jpg`, `*.jpeg`, `*.png`): Image files without intrinsic geographic metadata. When uploaded as standalone images, the geospatial functions return `None` with an explanatory note. The application never invents latitude/longitude values or substitutes default geographic bounds for real metadata.

> **Important**: Only GeoTIFF files carrying genuine coordinate reference system and affine transform metadata produce real-world coordinates. Ordinary raster image formats are treated as pixel‑space only.

The module uses the optional `rasterio` library (built on GDAL/Proj) to read georeferenced metadata. If `rasterio` is not installed, geospatial operations raise `RuntimeError` and no coordinates can be produced.

## 2. CRS and Affine Transform Requirements

For a raster to be accepted as a valid geospatial input, it must satisfy all of the following:

- **Coordinate Reference System (CRS)**: The raster must have a readable CRS. The `read_georeference()` function checks for a `crs` field and a `crs_obj` object. If either is missing or empty, a `SpatialInputError` with code `missing_crs` is raised.

- **Affine Transform**: The raster must have a valid 6‑parameter affine transform `(a, b, c, d, e, f)` represented as:
  ```
   [ a  b  c ]
   [ d  e  f ]
   [ 0  0  1 ]
  ```
  where `(c, f)` is the top‑left corner, and the transform maps pixel coordinates to geographic coordinates. The transform coefficients must all be finite and the full set of six coefficients must be present; otherwise a `SpatialInputError` with code `missing_transform` is raised.

- **Dimensions and Bounds**: The raster must have positive width and height, and valid finite spatial bounds derived from the transform and image dimensions. If width, height, or bounds are invalid or inconsistent, a `SpatialInputError` with code `invalid_metadata` is raised.

These validations are performed by `_validated_spatial_metadata()` and `check_compatibility()` in `utils/geospatial.py`.

## 3. Raster Resolution and Alignment

Spatial resolution is derived from the affine transform:

- **X‑resolution**: `math.hypot(transform[0], transform[1])` (ground distance per pixel in the x direction)
- **Y‑resolution**: `math.hypot(transform[3], transform[4])` (ground distance per pixel in the y direction)

The `preprocess_raster_pair()` function uses the **before** raster as the reference grid and resamples the **after** raster to match:

- Same CRS
- Same affine transform (origin, pixel size, orientation)
- Same width and height
- Same extent (computed from bounds)

The reprojection uses `reproject_raster()`, which supports both nearest‑neighbor and bilinear resampling (default: bilinear for continuous data, nearest for categorical).

> **Note**: The before raster is never modified; the after raster is warped to align perfectly with it. If the two rasters have different resolutions, the reprojection will change the number of pixels accordingly.

## 4. BEFORE Image as the Reference Grid

In change‑detection workflows, the **before** image serves as the reference grid:

1. `preprocess_raster_pair(before_bytes, after_bytes)` reads the georeference from both rasters.
2. `check_compatibility()` validates that the pair is compatible (same CRS, same dimensions, no mixed types).
3. The after raster is reprojected to match the before raster's CRS, transform, resolution, and extent.
4. The function returns a dictionary containing:
   - `before`: the original before bytes (unchanged)
   - `after`: the reprojected after bytes
   - `reference_info`: the metadata dict from the before raster
   - `note`: descriptive string indicating the alignment was performed

This design ensures that all change analysis is anchored to the original reference, preserving its geospatial context.

## 5. Ordinary JPG/PNG versus GeoTIFF Handling

| Aspect | GeoTIFF | Ordinary JPG/PNG |
|---|---|---|
| **Geographic metadata** | CRS and affine transform stored in file header | None |
| `read_georeference()` result | Returns dict with `crs`, `transform`, `width`, `height`, `bounds` | Returns `(None, "note about no georeference")` |
| `validate_spatial_pair()` | Accepts if both are georeferenced | Places images in explicit pixel‑mode (`mode="pixel"`) |
| Real-world coordinates | Produced via `pixel_to_lonlat()` | Never produced; functions return `None` |
| Use case | Change detection with geographic alignment | Visual comparison without geographic anchoring |

The code explicitly avoids inventing coordinates for non‑georeferenced images (see `utils/geospatial.py` lines 10‑13).

## 6. Three Practical Demo Scenarios
### Scenario 1: Infrastructure Expansion

- **Inputs**: A before‑GeoTIFF showing the site before construction, and an after‑GeoTIFF after the new facility was built.
- **Process**: Both files are uploaded, `preprocess_raster_pair()` aligns the after image to the before grid. The aligned pair can then be processed with `detect_changes()` to identify pixel‑level differences between the two datasets.
- **Output**: Annotated regions with pixel‑bounding boxes and centroids in image coordinates. *Note: Change detection identifies pixel differences; geographic labels (e.g., "building") require valid georeferenced data and additional analysis not provided by this module.*

### Scenario 2: Road and Terrain Changes

- **Inputs**: Two GeoTIFFs captured in different seasons or after a storm event, showing the same road corridor.
- **Process**: The pair is preprocessed to a common grid via `preprocess_raster_pair()`. Change detection (`detect_changes()`) can highlight pixel‑level differences between the two datasets.
- **Output**: Region annotations indicate geographic coordinates for detected change areas. *Note: The system flags pixel differences; specific classifications (e.g., "road repair," "erosion") require additional analysis beyond the scope of this module.*

### Scenario 3: Flood Impact

- **Inputs**: A before‑GeoTIFF (dry conditions) and an after‑GeoTIFF (post‑flood) of the same watershed.
- **Process**: After preprocessing with `preprocess_raster_pair()`, change detection (`detect_changes()`) flags inundated pixels compared to the dry reference.
- **Output**: Mapped regions showing changed pixels, each tagged with centroid coordinates in image space. *Note: The system identifies pixel-level changes; flood‑depth estimation and "flooded" change‑type classification are not implemented (see Section 7). The system does not classify changed pixels as flooded areas.*

## 7. Current Limitations and Future Enhancements

### Current Limitations (implemented features)

- **Rasterio dependency**: All geospatial operations require the optional `rasterio` package (GDAL/Proj). If it is not installed, functions raise `RuntimeError` and no coordinates can be produced.
- **Mixed‑type pairs rejected**: A pair consisting of one GeoTIFF and one ordinary JPG/PNG raises `SpatialInputError` because the grids cannot be made compatible.
- **CRS mismatch raises error**: `check_compatibility()` raises `SpatialInputError` when rasters have different CRS. The `preprocess_raster_pair()` function requires matching CRS; if rasters differ in CRS, they cannot be processed as a pair without an explicit reprojection step external to this module.
- **Only GeoTIFF supported for real coordinates**: Ordinary JPG/PNG files are treated as pixel‑space only; no geographic coordinates are generated.
- **Resolution must match after reprojection**: If the before and after rasters have fundamentally different resolutions, the reprojection may produce a grid that loses fine detail or introduces resampling artifacts.
- **Single‑band handling**: The current code assumes RGB or single‑band data; multi‑band non‑RGB data may require additional handling.

### Planned enhancements (not yet implemented)

- **Support for additional formats**: Cloud‑Optimized GeoTIFF (COG)
- **Batch processing**: A CLI or API endpoint to process multiple raster pairs in sequence.
- **Advanced resampling options**: Support for cubic convolution and other resampling methods beyond nearest/bilinear.
- **Automatic CRS detection and transformation**: When rasters differ only in CRS, automatically reproject to a common CRS without raising an error.
- **Flood‑depth estimation**: Incorporate DEM differencing to convert inundation masks into depth estimates.
- **Change‑type classification**: Machine‑learning‑based categorization of changes (e.g., construction vs. vegetation loss vs. flooding).
- **Web‑based viewer**: Integrated Folium/Leaflet map viewer embedded in the UI for interactive exploration of annotated regions.

---

*Generated from the source code in `utils/geospatial.py` and `utils/change_detection.py` and the test suite in `tests/test_geospatial.py` / `tests/test_raster_preprocessing.py`. This guide reflects the implemented behavior as of the current codebase.*