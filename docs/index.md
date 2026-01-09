<h1 style="display:flex;align-items:center;gap:16px;margin:0 0 8px 0;">
  <span>GeoFabric</span>
  <img
    src="https://raw.githubusercontent.com/marcostfermin/GeoFabric/main/docs/logo.svg"
    alt="GeoFabric Logo"
    width="56"
    height="56"
    style="margin-top:4px;"
  >
</h1>

GeoFabric is a pragmatic geospatial toolkit for ETL, analytics, and publishing—built around Parquet, DuckDB Spatial, and PMTiles.

## What you can do

- **ETL**: Pull/normalize subsets into (Geo)Parquet
- **Analytics**: Scalable spatial SQL via DuckDB + DuckDB Spatial
- **Viz / Publishing**: Notebook maps + PMTiles generation via tippecanoe

!!! tip "Start here"
    Go to **Getting Started** to install GeoFabric and run your first query.

## Key Features

- **Unified Query API** - Chainable, lazy query builder for geospatial data
- **Multiple Format Support** - Parquet, GeoJSON, GeoPackage, FlatGeoBuf, Shapefile, CSV
- **17+ Spatial Operations** - Buffer, simplify, transform, clip, dissolve, centroid, and more
- **Spatial Joins** - Join datasets with 6 predicates (intersects, within, contains, touches, crosses, overlaps)
- **K-Nearest Neighbors** - Find nearest features with optional distance filtering
- **Cloud Support** - Read directly from S3, GCS, and Azure Blob Storage
- **PostGIS Integration** - Query PostGIS databases directly
- **Programmatic Configuration** - Configure credentials for all platforms via API
- **PMTiles Export** - Generate vector tiles via tippecanoe
- **Geometry Type Detection** - Automatic handling of WKB_BLOB and native GEOMETRY types

## Quick Links

- [Getting Started](getting-started.md)
- [API Reference](api.md)
- [Complete API Reference](API_REFERENCE.md)
- [Authentication Guide](../examples/AUTHENTICATION.md)
- [GitHub Repository](https://github.com/marcostfermin/GeoFabric)
