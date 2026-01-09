# Getting Started

## Installation

```bash
# From pip
pip install geofabric

# From source
git clone https://github.com/marcostfermin/GeoFabric.git
cd GeoFabric
pip install -e "."

# Optional dependencies
pip install -e ".[viz]"
pip install -e ".[stac]"
pip install -e ".[all]"
pip install -e ".[dev,all]"
```

## Quick Start

```python
import geofabric as gf

ds = gf.open("file:///path/to/data.parquet")
roi = gf.roi.bbox(-74.10, 40.60, -73.70, 40.90)

q = ds.within(roi).select(["*"]).limit(1000)

q.to_parquet("out.parquet")
q.to_geojson("out.geojson")
q.to_geopackage("out.gpkg")

print(q.aggregate({"count": "*"}))

q.show()
q.to_pmtiles("out.pmtiles", layer="features", maxzoom=14)
```

### Open a Dataset

```python
import geofabric as gf

# Local file
ds = gf.open("file:///path/to/data.parquet")

# S3 (public bucket)
ds = gf.open("s3://bucket/data.parquet")

# GCS
ds = gf.open("gs://bucket/data.parquet")

# Azure Blob Storage
ds = gf.open("az://container/data.parquet")

# PostGIS
ds = gf.open("postgresql://user:pass@host/db?table=mytable")

# STAC catalog
ds = gf.open("stac://earth-search.aws.element84.com/v1?collection=sentinel-2-l2a")
```

### Configure Credentials

GeoFabric supports programmatic configuration for all cloud platforms:

```python
import geofabric as gf

# S3 credentials
gf.configure_s3(
    access_key_id="AKIA...",
    secret_access_key="...",
    region="us-east-1"
)

# PostGIS defaults (allows shorter connection strings)
gf.configure_postgis(
    host="db.example.com",
    user="myuser",
    password="mypassword",
    sslmode="require"  # SSL mode for secure connections
)

# Azure Blob Storage
gf.configure_azure(
    account_name="mystorageaccount",
    account_key="..."
)

# STAC catalogs
gf.configure_stac(
    api_key="your-api-key",
    default_catalog="https://planetarycomputer.microsoft.com/api/stac/v1"
)

# HTTP settings (proxy, timeout, SSL)
gf.configure_http(
    proxy="http://corporate-proxy:8080",
    timeout=60,
    verify_ssl=True
)

# Now use gf.open() with configured credentials
ds = gf.open("s3://my-private-bucket/data.parquet?anonymous=false")
ds = gf.open("az://container/data.parquet")
ds = gf.open("postgresql:///mydb?table=public.buildings")

# Reset all configuration
gf.reset_config()
```

See the [Authentication Guide](../examples/AUTHENTICATION.md) for detailed setup instructions.

### Query and Filter

```python
# Define a region of interest
roi = gf.roi.bbox(-74.10, 40.60, -73.70, 40.90)

# Build a query
q = ds.within(roi).select(["id", "name", "geometry"]).limit(1000)

# Add WHERE clause
q = ds.query().where("type = 'building'").limit(500)
```

### Export Data

```python
# Various output formats
q.to_parquet("out.parquet")
q.to_geojson("out.geojson")
q.to_geopackage("out.gpkg")
q.to_flatgeobuf("out.fgb")
q.to_csv("out.csv")

# Vector tiles (requires tippecanoe)
q.to_pmtiles("out.pmtiles", layer="features", maxzoom=14)
```

### Spatial Operations

```python
# Geometry transformations
q.buffer(distance=100, unit="meters")
q.simplify(tolerance=0.001)
q.transform(to_srid=3857)
q.centroid()
q.convex_hull()
q.dissolve(by="category")

# Add computed columns
q.with_area()
q.with_length()
q.with_bounds()
q.with_distance_to("POINT(0 0)")
```

### Spatial Joins

```python
buildings = gf.open("file:///buildings.parquet")
parcels = gf.open("file:///parcels.parquet")

# Join buildings to parcels
joined = buildings.query().sjoin(
    parcels.query(),
    predicate="intersects",
    how="inner"
)

# K-nearest neighbors
nearest = buildings.query().nearest(parcels.query(), k=3)
```

### Visualization

```python
# Requires viz extras: pip install -e ".[viz]"
q.show()
```

## CLI Usage

```bash
# Show help
gf --help

# Query data
gf sql file:///data.parquet "SELECT COUNT(*) FROM data"

# Extract subset
gf pull file:///data.parquet out.parquet --where "type='building'" --limit 1000

# Dataset info
gf info file:///data.parquet
gf stats file:///data.parquet
gf validate file:///data.parquet

# Spatial operations
gf buffer file:///data.parquet out.parquet --distance 100 --unit meters
gf simplify file:///data.parquet out.parquet --tolerance 0.001
gf transform file:///data.parquet out.parquet --to-srid 3857
gf dissolve file:///data.parquet out.parquet --by category
```

## Overture Maps

```python
from geofabric.sources.overture import Overture

# Download Overture data (requires AWS CLI)
ov = Overture(release="2025-12-17.0", theme="base", type_="infrastructure")
local_dir = ov.download("./data/overture")

# Query downloaded data
ds = gf.open(local_dir)
sample = ds.query().limit(10000)
sample.to_parquet("sample.parquet")
```
