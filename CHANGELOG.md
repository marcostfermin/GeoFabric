# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive input validation for spatial operations (BufferOp, SimplifyOp, DensifyOp)
- New spatial operations: `boundary()`, `explode()`, `densify()`, `point_on_surface()`, `reverse()`, `flip_coordinates()`
- Geometry measurement methods: `with_area()`, `with_length()`, `with_perimeter()`, `with_bounds()`
- Geometry info methods: `with_geometry_type()`, `with_num_points()`, `with_is_valid()`
- Distance calculation: `with_distance_to(wkt)` for distance to reference geometry
- Coordinate extraction: `with_x()`, `with_y()`, `with_coordinates()` for point coordinates
- Geometry aggregation: `collect()` to gather geometries into MultiGeometry
- Symmetric difference: `symmetric_difference(wkt)` for XOR operation
- Dissolve/aggregate operation with `dissolve(by=...)` for merging geometries
- Spatial join support with `sjoin()` method (predicates: intersects, within, contains, touches, crosses, overlaps)
- K-nearest neighbor queries with `nearest()` method with automatic `_right` suffix for conflicting columns
- CRS transformation with `transform()` method
- Geometry repair with `make_valid()` method
- New CLI commands: `sample`, `stats`, `buffer`, `simplify`, `transform`, `centroid`, `convex-hull`, `dissolve`, `add-area`, `add-length`
- Progress tracking utilities: `ProgressTracker` and `progress_bar()`
- Retry logic with exponential backoff for network operations
- `NetworkError` and `MissingDependencyError` exception types
- `__all__` exports for all public modules
- GitHub Actions CI/CD pipeline
- Pre-commit hooks configuration
- Integration tests for real data sources (S3, Azure, PostGIS, STAC, Files)
- Sample Overture Maps data for offline testing
- PMTiles export testing with tippecanoe
- Comprehensive test suite with 727 tests

### Changed
- Improved exception specificity (using specific exception types instead of broad `Exception`)
- DuckDB spatial extension now lazy-loaded for better startup performance
- Better error messages for missing dependencies
- `_geom_expr()` helper for automatic GEOMETRY vs WKB_BLOB type detection
- All spatial methods now dynamically detect geometry column type
- `nearest()` method automatically renames conflicting columns with `_right` suffix

### Fixed
- Graceful handling of DuckDB spatial extension loading failures
- Azure config parameter names (`azure_account_name` instead of incorrect `azure_storage_account_name`)
- PostGIS duplicate database attach error handling
- Geometry type handling for GeoParquet files (GEOMETRY vs WKB_BLOB)
- S3/Azure spatial operations now work correctly with native GEOMETRY types

## [1.0.0] - 2025-01-09

### Added
- Initial release
- Core Query API for geospatial data processing
- DuckDB engine for SQL execution
- Support for Parquet, GeoJSON, GeoPackage, FlatGeoBuf, Shapefile formats
- ROI (Region of Interest) filtering with bbox, WKT, GeoJSON
- Overture Maps data download helper
- PMTiles output via tippecanoe
- Plugin system for sources, engines, and sinks
- CLI tool (`gf`) for common operations
- Visualization support with lonboard (optional)

[Unreleased]: https://github.com/marcostfermin/GeoFabric/compare/v0.1.0...HEAD
[1.0.0]: https://github.com/marcostfermin/GeoFabric/releases/tag/v1.0.0
