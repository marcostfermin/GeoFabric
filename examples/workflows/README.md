# GeoFabric Workflow Examples

Focused, realistic workflows demonstrating specific feature combinations. Each file is a complete, runnable example targeting a single use case.

## Workflows

### Data Preparation & Cleaning

| File | Features | Use Case |
|------|----------|----------|
| [data_cleaning.py](data_cleaning.py) | validate + make_valid + filter | Clean messy source data |
| [data_quality_full.py](data_quality_full.py) | validate + repair + transform + metadata | Production data pipeline |
| [crs_standardization.py](crs_standardization.py) | transform + make_valid + bounds | Standardize mixed CRS data |
| [coordinate_flip.py](coordinate_flip.py) | flip_coordinates + bounds | Fix swapped lat/lon |
| [parcel_subdivision.py](parcel_subdivision.py) | explode + with_area + filter | Split multi-geometries |

### Spatial Analysis

| File | Features | Use Case |
|------|----------|----------|
| [buffer_and_measure.py](buffer_and_measure.py) | buffer + with_area + perimeter | Create safety zones |
| [spatial_enrichment.py](spatial_enrichment.py) | sjoin + computed columns | Add parcel info to buildings |
| [join_and_filter.py](join_and_filter.py) | sjoin + where + select | Filter by spatial relationship |
| [boundary_operations.py](boundary_operations.py) | clip + dissolve + boundary | Extract city neighborhoods |
| [ring_buffer_analysis.py](ring_buffer_analysis.py) | sequential buffers + erase | Create distance rings |
| [flood_exposure.py](flood_exposure.py) | sjoin + clip + with_area | Calculate flood zone exposure |
| [environmental_impact.py](environmental_impact.py) | transform + buffer + sjoin + clip | Environmental buffer analysis |

### Proximity & Distance

| File | Features | Use Case |
|------|----------|----------|
| [nearest_facility.py](nearest_facility.py) | nearest + distance + CSV | Find closest hospitals |
| [service_area_tiers.py](service_area_tiers.py) | multi-buffer + sjoin | Analyze coverage by distance |
| [transit_accessibility.py](transit_accessibility.py) | centroid + nearest + KNN | Score transit access |
| [delivery_optimization.py](delivery_optimization.py) | buffer + nearest + sjoin | Delivery zone planning |

### Geometry Operations

| File | Features | Use Case |
|------|----------|----------|
| [point_extraction.py](point_extraction.py) | centroid + coordinates + bounds | Create points from polygons |
| [geometry_metrics.py](geometry_metrics.py) | area + length + num_points | Add geometry measurements |
| [viewshed_prep.py](viewshed_prep.py) | point_on_surface + coordinates | Prepare points for analysis |
| [envelope_index.py](envelope_index.py) | envelope + bounds + CSV | Create bounding box catalog |
| [poi_clustering.py](poi_clustering.py) | buffer + collect + convex_hull | Group nearby POIs |

### Data Export & Publishing

| File | Features | Use Case |
|------|----------|----------|
| [web_mapping_pipeline.py](web_mapping_pipeline.py) | transform + simplify + PMTiles | Prepare for web maps |
| [attribute_summary.py](attribute_summary.py) | where + describe + aggregate | Summarize by category |
| [road_density.py](road_density.py) | with_length + sjoin + dissolve | Calculate density metrics |

### Cloud & External Sources

| File | Features | Use Case |
|------|----------|----------|
| [cloud_to_local.py](cloud_to_local.py) | S3 + filter + exports | Extract cloud data subset |
| [postgis_sync.py](postgis_sync.py) | PostGIS + transform + cache | Sync database locally |
| [overture_extract.py](overture_extract.py) | Overture + simplify + PMTiles | Extract Overture for city |
| [multi_source_integration.py](multi_source_integration.py) | S3 + PostGIS + local + sjoin | Combine multiple sources |

### Urban Planning & Real Estate

| File | Features | Use Case |
|------|----------|----------|
| [real_estate_proximity.py](real_estate_proximity.py) | buffer + sjoin + centroid + PMTiles | Properties near amenities |
| [retail_site_selection.py](retail_site_selection.py) | buffer + sjoin + nearest | Score retail locations |
| [urban_heat_island.py](urban_heat_island.py) | sjoin + dissolve + area ratios | Heat vulnerability analysis |

### Emergency & Risk

| File | Features | Use Case |
|------|----------|----------|
| [emergency_coverage.py](emergency_coverage.py) | multi-buffer + sjoin + collect | Fire/hospital coverage gaps |
| [flood_risk_overture.py](flood_risk_overture.py) | Overture + sjoin + clip | Building flood exposure |

## Running Workflows

```bash
# Run any workflow directly
python examples/workflows/buffer_and_measure.py

# Or import and call
from examples.workflows.spatial_enrichment import main
main()
```

## Pattern

Each workflow follows a consistent pattern:

```python
import geofabric as gf

def main() -> None:
    # 1. Load data source(s)
    data = gf.open("file:///data/input.parquet")

    # 2. Define region of interest
    roi = gf.roi.bbox(-74.0, 40.7, -73.9, 40.8)

    # 3. Apply 2-4 operations
    result = (
        data.query()
        .within(roi)
        .operation1()
        .operation2()
    )

    # 4. Export results
    result.to_parquet("output.parquet")

if __name__ == "__main__":
    main()
```

## Data Requirements

Replace placeholder paths with your actual data:

### Local Files (No Authentication Required)

```python
# Using file:// URI scheme
gf.open("file:///data/parcels.parquet")

# Using plain file paths
gf.open("/data/parcels.parquet")
gf.open("./data/parcels.parquet")
gf.open("~/data/parcels.parquet")
```

Supported formats: `.parquet`, `.geojson`, `.shp`, `.gpkg`, `.fgb`, `.csv`

### Cloud Storage

| Source | URI Format | Example |
|--------|------------|---------|
| AWS S3 | `s3://bucket/path` | `gf.open("s3://my-bucket/data.parquet")` |
| GCS | `gs://bucket/path` | `gf.open("gs://my-bucket/data.parquet")` |
| Azure | `az://container/path` | `gf.open("az://mycontainer/data.parquet")` |
| PostGIS | `postgresql://...?table=...` | `gf.open("postgresql://host/db?table=public.parcels")` |
| Overture | Download first | See [overture_extract.py](overture_extract.py) |

### Configuring Credentials

Cloud storage requires credentials. Use programmatic configuration or environment variables:

```python
import geofabric as gf

# Programmatic configuration (takes precedence over env vars)
gf.configure_s3(access_key_id="...", secret_access_key="...", region="us-east-1")
gf.configure_postgis(host="db.example.com", user="user", password="pass")

# Now use gf.open() with configured credentials
ds = gf.open("s3://my-bucket/data.parquet?anonymous=false")
```

See [Authentication Guide](../AUTHENTICATION.md) for detailed setup instructions.

## See Also

- [Authentication Guide](../AUTHENTICATION.md) - Configure cloud credentials and learn about DuckDB's httpfs
- [API Reference](../../docs/api.md) - Complete method documentation
