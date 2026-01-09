# GeoFabric Examples

This directory contains example scripts demonstrating GeoFabric's capabilities for geospatial ETL, analytics, and publishing.

## Prerequisites

```bash
# Install GeoFabric with all optional dependencies
pip install -e ".[all]"

# For PMTiles export, install tippecanoe
# macOS: brew install tippecanoe
# Linux: See https://github.com/felt/tippecanoe

# For cloud sources, install AWS CLI (for S3/Overture)
pip install awscli
```

## Authentication

GeoFabric supports **programmatic configuration** and **environment variables** for all cloud platforms. See **[AUTHENTICATION.md](AUTHENTICATION.md)** for detailed setup instructions.

### Quick Configuration

```python
import geofabric as gf

# Configure credentials programmatically (takes precedence over env vars)
gf.configure_s3(access_key_id="...", secret_access_key="...", region="us-east-1")
gf.configure_postgis(host="db.example.com", user="user", password="pass")
gf.configure_azure(account_name="...", account_key="...")

# Now use gf.open() with configured credentials
ds = gf.open("s3://my-bucket/data.parquet?anonymous=false")
```

### Supported Platforms

- **Amazon S3** - Programmatic or AWS credentials via environment/CLI/IAM roles
- **Google Cloud Storage** - Programmatic or application default credentials
- **Azure Blob Storage** - Programmatic or environment variables
- **PostGIS** - Programmatic defaults or full connection strings
- **STAC Catalogs** - Programmatic API keys/headers or usually public
- **Overture Maps** - Public data, no authentication required

## Example Scripts

### Core Functionality

| Script | Description |
|--------|-------------|
| [01_basic_usage.py](01_basic_usage.py) | Opening datasets, building queries, filtering data |
| [02_spatial_operations.py](02_spatial_operations.py) | Buffer, simplify, transform, clip, dissolve, and more |
| [03_computed_columns.py](03_computed_columns.py) | Adding area, length, bounds, coordinates, and geometry info |
| [04_spatial_joins.py](04_spatial_joins.py) | Spatial joins with predicates and K-nearest neighbors |
| [05_export_formats.py](05_export_formats.py) | Exporting to Parquet, GeoJSON, GeoPackage, PMTiles, etc. |
| [06_validation_stats.py](06_validation_stats.py) | Geometry validation and dataset statistics |
| [07_cloud_sources.py](07_cloud_sources.py) | Reading from S3, GCS, and PostGIS |
| [08_overture_maps.py](08_overture_maps.py) | Downloading and processing Overture Maps data |
| [09_cli_examples.sh](09_cli_examples.sh) | Command-line interface usage examples |

### Real-World Workflows

See **[workflows/](workflows/)** for 33 focused workflow examples organized by category:

| Category | Examples |
|----------|----------|
| Data Preparation | data_cleaning, data_quality_full, crs_standardization, coordinate_flip, parcel_subdivision |
| Spatial Analysis | buffer_and_measure, spatial_enrichment, join_and_filter, boundary_operations, ring_buffer_analysis, flood_exposure, environmental_impact |
| Proximity & Distance | nearest_facility, service_area_tiers, transit_accessibility, delivery_optimization |
| Geometry Operations | point_extraction, geometry_metrics, viewshed_prep, envelope_index, poi_clustering |
| Export & Publishing | web_mapping_pipeline, attribute_summary, road_density |
| Cloud Sources | cloud_to_local, postgis_sync, overture_extract, multi_source_integration |
| Urban Planning | real_estate_proximity, retail_site_selection, urban_heat_island |
| Emergency & Risk | emergency_coverage, flood_risk_overture |

## Quick Start

```python
import geofabric as gf

# Open a local Parquet file
ds = gf.open("file:///path/to/data.parquet")

# Define a region of interest (New York City area)
roi = gf.roi.bbox(-74.10, 40.60, -73.70, 40.90)

# Build and execute a query
result = (
    ds.query()
    .within(roi)
    .select(["id", "name", "geometry"])
    .limit(1000)
    .to_geopandas()
)

print(f"Retrieved {len(result)} features")
```

## Running Examples

```bash
# Run a core example
python examples/01_basic_usage.py

# Run CLI examples
bash examples/09_cli_examples.sh

# Run a workflow example
python examples/workflows/buffer_and_measure.py
```

## Sample Data

Examples use placeholder paths. Replace with your own data:

| Source | URI Format | Example |
|--------|------------|---------|
| Local files | `file:///path` | `file:///data/buildings.parquet` |
| S3 | `s3://bucket/key` | `s3://my-bucket/data.parquet` |
| GCS | `gs://bucket/key` | `gs://my-bucket/data.parquet` |
| Azure | `az://container/path` | `az://mycontainer/data.parquet` |
| PostGIS | `postgresql://...` | `postgresql://user:pass@host/db?table=schema.table` |
| STAC | `stac://catalog/...` | `stac://earth-search.aws.element84.com/v1?collection=sentinel-2-l2a` |

## Example Workflow Pattern

Most workflows follow this pattern:

```python
import geofabric as gf

# 1. Load data sources
buildings = gf.open("file:///data/buildings.parquet")
parcels = gf.open("file:///data/parcels.parquet")

# 2. Define region of interest
roi = gf.roi.bbox(-74.10, 40.60, -73.70, 40.90)

# 3. Filter and transform
query = (
    buildings.query()
    .within(roi)                              # Spatial filter
    .where("type = 'commercial'")             # Attribute filter
    .buffer(distance=50, unit="meters")       # Spatial operation
    .with_area(col_name="buffered_area")      # Computed column
)

# 4. Spatial join with other data
enriched = query.sjoin(
    parcels.query().within(roi),
    predicate="intersects",
    how="inner",
)

# 5. Export results
enriched.to_parquet("output/analysis.parquet")
enriched.to_geojson("output/analysis.geojson")
enriched.to_pmtiles("output/analysis.pmtiles", layer="results")
```

## Documentation

- [Getting Started Guide](../docs/getting-started.md)
- [API Reference](../docs/api.md)
- [Authentication Guide](AUTHENTICATION.md)
- [Workflow Examples](workflows/)
- [GitHub Repository](https://github.com/marcostfermin/GeoFabric)
