<h1 style="display: flex; align-items: center; gap: 16px; margin: 0 0 8px 0;">
  <span>GeoFabric</span>
  <img
    src="docs/logo.svg"
    alt="GeoFabric Logo"
    width="56"
    height="56"
    style="margin-top: 4px;"
  >
</h1>

[![PyPI version](https://badge.fury.io/py/geofabric.svg)](https://badge.fury.io/py/geofabric)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

GeoFabric is a pragmatic geospatial toolkit for ETL, analytics, and publishing—built around Parquet, DuckDB Spatial, and PMTiles.
- **ETL**: Pull/normalize subsets into (Geo)Parquet
- **Analytics**: Scalable spatial SQL via DuckDB + DuckDB Spatial
- **Viz / Publishing**: Quick notebook maps + PMTiles generation via tippecanoe

## Features

- **Unified Query API** - Chainable, lazy query builder for geospatial data
- **Multiple Format Support** - Parquet, GeoJSON, GeoPackage, FlatGeoBuf, Shapefile, CSV
- **17+ Spatial Operations** - Buffer, simplify, transform, clip, erase, boundary, densify, dissolve, centroid, convex hull, and more
- **Geometry Measurements** - Area, length, perimeter, bounds, distance calculations
- **Coordinate Extraction** - Extract X/Y coordinates from geometries
- **Spatial Joins** - Efficient joins with 6 predicates (intersects, within, contains, touches, crosses, overlaps)
- **K-Nearest Neighbors** - Find nearest features with optional distance filtering
- **Cloud Support** - Read directly from S3, GCS, and Azure Blob Storage
- **Programmatic Configuration** - Configure credentials for all platforms via API
- **PostGIS Integration** - Query PostGIS databases directly
- **Overture Maps** - Built-in helper for downloading Overture data
- **PMTiles Export** - Generate vector tiles via tippecanoe
- **Validation** - Geometry validation and repair utilities
- **CLI Tool** - 16 commands for common operations
- **Auto-generated Docs** - API documentation deployed to GitHub Pages

## Architecture

```mermaid
flowchart TB
  %% =========================
  %% USER ENTRY POINTS
  %% =========================
  subgraph U["User entry points"]
    direction LR
    U1["Python API"]
    U2["CLI"]
    U3["Notebook viz"]
  end

  %% =========================
  %% THIN CORE (ORCHESTRATION)
  %% =========================
  C["GeoFabric core<br/>lazy query orchestration"]

  %% =========================
  %% EXECUTION BACKEND
  %% =========================
  subgraph E["Execution backend"]
    direction TB
    E1["Query planning / SQL generation"]
    E2["DuckDB + DuckDB Spatial"]
  end

  %% =========================
  %% DATA SOURCES
  %% =========================
  subgraph S["Data sources"]
    direction TB
    S1["Local files"]
    S2["S3 / GCS / Azure"]
    S3["PostGIS"]
    S4["STAC / Overture"]
  end

  %% =========================
  %% OUTPUTS
  %% =========================
  subgraph O["Outputs"]
    direction TB
    O1["Parquet (GeoParquet)"]
    O2["Vector formats<br/>GeoJSON · GPKG · FlatGeoBuf · CSV"]
    O3["PMTiles (tippecanoe)"]
  end

  %% =========================
  %% SUPPORT SERVICES
  %% =========================
  subgraph P["Support services"]
    direction LR
    P1["Validation / repair"]
    P2["Caching"]
    P3["Configuration"]
    P4["Plugin registry"]
  end

  %% =========================
  %% TRUE EXECUTION FLOW
  %% =========================
  U --> C
  S --> C
  C --> E1
  E1 --> E2
  E2 --> O

  P -.-> C
```

## Installation

### From PyPI (coming soon)
```bash
pip install geofabric
```

### From Source
```bash
git clone https://github.com/marcostfermin/GeoFabric.git
cd GeoFabric
pip install -e "."
```

### With Optional Dependencies
```bash
# Visualization support (geopandas + lonboard)
pip install -e ".[viz]"

# STAC catalog support
pip install -e ".[stac]"

# All optional dependencies
pip install -e ".[all]"

# Development dependencies
pip install -e ".[dev,all]"
```

## Quick Start

```python
import geofabric as gf

# Open a dataset
ds = gf.open("file:///path/to/data.parquet")

# Define a region of interest
roi = gf.roi.bbox(-74.10, 40.60, -73.70, 40.90)

# Build a query
q = ds.within(roi).select(["*"]).limit(1000)

# Export to various formats
q.to_parquet("out.parquet")
q.to_geojson("out.geojson")
q.to_geopackage("out.gpkg")

# Run analytics
print(q.aggregate({"count": "*"}))

# Visualize in notebooks (requires viz extras)
q.show()

# Generate vector tiles (requires tippecanoe)
q.to_pmtiles("out.pmtiles", layer="features", maxzoom=14)
```

## Spatial Operations

```python
import geofabric as gf

ds = gf.open("file:///data.parquet")
q = ds.query()

# Geometry transformations
q.buffer(distance=100, unit="meters")  # Buffer with unit conversion
q.simplify(tolerance=0.001)            # Simplify geometries
q.transform(to_srid=3857)              # Transform CRS
q.boundary()                           # Extract boundaries
q.centroid()                           # Get centroids
q.convex_hull()                        # Convex hulls
q.envelope()                           # Bounding boxes
q.densify(max_distance=100)            # Add vertices
q.make_valid()                         # Repair invalid geometries
q.dissolve(by="category")              # Merge geometries by attribute
q.collect()                            # Gather into MultiGeometry
q.explode()                            # Split multi-geometries

# Add computed columns
q.with_area()                          # Add area column
q.with_length()                        # Add length/perimeter
q.with_bounds()                        # Add minx, miny, maxx, maxy
q.with_distance_to("POINT(0 0)")       # Distance to reference
q.with_coordinates()                   # Add X, Y columns
q.with_geometry_type()                 # Add geometry type
q.with_num_points()                    # Add vertex count
q.with_is_valid()                      # Add validity check
```

## Spatial Joins

```python
import geofabric as gf

buildings = gf.open("file:///buildings.parquet")
parcels = gf.open("file:///parcels.parquet")

# Spatial join
joined = buildings.query().sjoin(
    parcels.query(),
    predicate="intersects",
    how="inner"
)

# K-nearest neighbors
nearest = buildings.query().nearest(
    parcels.query(),
    k=3,
    max_distance=1000
)
```

## Overture Maps Integration

```python
from geofabric.sources.overture import Overture
import geofabric as gf

# Download Overture data (requires AWS CLI)
ov = Overture(release="2025-12-17.0", theme="base", type_="infrastructure")
local_dir = ov.download("./data/overture_infra")

# Query the downloaded data
ds = gf.open(local_dir)
sample = ds.query().limit(10000)
sample.to_parquet("overture_sample.parquet")
```

## CLI Usage

```bash
# Show help
gf --help

# Run SQL queries
gf sql file:///tmp/x.parquet "SELECT COUNT(*) FROM data"

# Pull subset of data
gf pull file:///data.parquet out.parquet --where "type='building'" --limit 1000

# Show dataset info
gf info file:///data.parquet

# Validate geometries
gf validate file:///data.parquet

# Show first N rows
gf head file:///data.parquet --n 20

# Sample random rows
gf sample file:///data.parquet sample.parquet --n 1000

# Show statistics
gf stats file:///data.parquet

# Buffer geometries
gf buffer file:///data.parquet buffered.parquet --distance 100 --unit meters

# Simplify geometries
gf simplify file:///data.parquet simplified.parquet --tolerance 0.001

# Transform CRS
gf transform file:///data.parquet transformed.parquet --to-srid 3857

# Compute centroids
gf centroid file:///data.parquet centroids.parquet

# Compute convex hulls
gf convex-hull file:///data.parquet hulls.parquet

# Dissolve geometries by attribute
gf dissolve file:///data.parquet dissolved.parquet --by category

# Add area column
gf add-area file:///data.parquet with_area.parquet --column-name area_sqm

# Add length/perimeter column
gf add-length file:///data.parquet with_length.parquet --column-name perimeter

# Download Overture data
gf overture download --release 2025-12-17.0 --theme base --type infrastructure --dest ./data
```

## Supported Data Sources

| Source | URI Format | Example |
|--------|------------|---------|
| Local Files | `file:///path` | `file:///data/buildings.parquet` |
| S3 | `s3://bucket/key` | `s3://my-bucket/data.parquet` |
| GCS | `gs://bucket/key` | `gs://my-bucket/data.parquet` |
| Azure | `az://container/path` | `az://mycontainer/data.parquet` |
| PostGIS | `postgresql://...` | `postgresql://user:pass@host/db?table=schema.table` |
| STAC | `stac://...` | `stac://catalog-url/collection` |

## Credential Configuration

GeoFabric supports both programmatic configuration and environment variables:

```python
import geofabric as gf

# Programmatic configuration (takes precedence)
gf.configure_s3(
    access_key_id="AKIA...",
    secret_access_key="...",
    region="us-east-1"
)
gf.configure_postgis(host="db.example.com", user="user", password="pass")
gf.configure_azure(account_name="...", account_key="...")

# Now use gf.open() with configured credentials
ds = gf.open("s3://my-bucket/data.parquet?anonymous=false")
```

See [Authentication Guide](examples/AUTHENTICATION.md) and [API Reference](docs/API_REFERENCE.md) for details.

## Plugin System

GeoFabric supports plugins via Python entry points:

- `geofabric.sources` - Data source plugins
- `geofabric.engines` - Query engine plugins
- `geofabric.sinks` - Output sink plugins

See [src/geofabric/registry.py](src/geofabric/registry.py) for implementation details.

## Development

```bash
# Clone and install
git clone https://github.com/marcostfermin/GeoFabric.git
cd GeoFabric
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,all]"

# Install pre-commit hooks
pre-commit install

# Run tests
pytest

# Run tests with coverage
pytest --cov=geofabric --cov-report=term-missing

# Run linting
ruff check src/

# Run type checking
mypy src/geofabric
```

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a list of changes.
