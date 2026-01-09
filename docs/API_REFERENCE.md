# GeoFabric API Reference

Complete reference for all GeoFabric functions, classes, and methods.

## Table of Contents

- [Core Functions](#core-functions)
- [Configuration Functions](#configuration-functions)
- [ROI (Region of Interest) Functions](#roi-region-of-interest-functions)
- [Cache Functions](#cache-functions)
- [Validation Functions](#validation-functions)
- [Dataset Class](#dataset-class)
- [Query Class](#query-class)
- [Data Classes](#data-classes)

---

## Core Functions

### `gf.open(uri, *, engine=None)`

Open a geospatial data source and return a Dataset.

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `uri` | `str` | URI to the data source |
| `engine` | `DuckDBEngine \| None` | Optional custom engine instance |

**Returns:** `Dataset`

**Supported URI Schemes:**
| Scheme | Description | Example |
|--------|-------------|---------|
| `file://` or path | Local files (Parquet, GeoJSON, etc.) | `gf.open("data.parquet")` |
| `s3://` | Amazon S3 | `gf.open("s3://bucket/data.parquet")` |
| `gs://` or `gcs://` | Google Cloud Storage | `gf.open("gs://bucket/data.parquet")` |
| `az://` | Azure Blob Storage | `gf.open("az://container/data.parquet")` |
| `postgresql://` | PostGIS database | `gf.open("postgresql://host/db?table=t")` |
| `overture://` | Overture Maps data | `gf.open("overture://buildings")` |
| `stac://` | STAC catalogs | `gf.open("stac://catalog.com/collection")` |

**Example:**
```python
import geofabric as gf

# Local file
ds = gf.open("buildings.parquet")

# S3 with credentials configured
gf.configure_s3(access_key_id="...", secret_access_key="...")
ds = gf.open("s3://my-bucket/data.parquet?anonymous=false")

# PostGIS
ds = gf.open("postgresql://user:pass@host:5432/db?table=parcels")
```

---

## Configuration Functions

All configuration functions set credentials programmatically. Programmatic configuration takes precedence over environment variables.

### `gf.configure_s3(...)`

Configure Amazon S3 credentials.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `access_key_id` | `str \| None` | `None` | AWS access key ID |
| `secret_access_key` | `str \| None` | `None` | AWS secret access key |
| `region` | `str \| None` | `None` | AWS region (e.g., 'us-east-1') |
| `session_token` | `str \| None` | `None` | AWS session token (for temporary credentials) |
| `endpoint` | `str \| None` | `None` | Custom S3 endpoint (for MinIO, DigitalOcean Spaces) |
| `use_ssl` | `bool` | `True` | Use SSL for connections |

**Example:**
```python
# Standard AWS credentials
gf.configure_s3(
    access_key_id="AKIAIOSFODNN7EXAMPLE",
    secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    region="us-east-1"
)

# MinIO or S3-compatible service
gf.configure_s3(
    access_key_id="minioadmin",
    secret_access_key="minioadmin",
    endpoint="http://localhost:9000",
    use_ssl=False
)
```

---

### `gf.configure_gcs(...)`

Configure Google Cloud Storage credentials.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `access_key_id` | `str \| None` | `None` | GCS HMAC access key ID |
| `secret_access_key` | `str \| None` | `None` | GCS HMAC secret access key |
| `project` | `str \| None` | `None` | GCP project ID |

**Example:**
```python
gf.configure_gcs(
    access_key_id="GOOGTS7C7FUP3AIRVJTE2BCD",
    secret_access_key="bGoa+V7g/yqDXvKRqq+JTFn4uQZbPiQJo4pf9RzJ",
    project="my-gcp-project"
)
```

---

### `gf.configure_azure(...)`

Configure Azure Blob Storage credentials.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `account_name` | `str \| None` | `None` | Azure storage account name |
| `account_key` | `str \| None` | `None` | Azure storage account key |
| `connection_string` | `str \| None` | `None` | Full Azure connection string |
| `sas_token` | `str \| None` | `None` | Shared Access Signature token |

**Example:**
```python
# Account name and key
gf.configure_azure(
    account_name="mystorageaccount",
    account_key="accountkey123..."
)

# Connection string
gf.configure_azure(
    connection_string="DefaultEndpointsProtocol=https;AccountName=...;AccountKey=..."
)

# SAS token
gf.configure_azure(
    account_name="mystorageaccount",
    sas_token="sv=2021-06-08&ss=b&srt=sco&sp=r..."
)
```

---

### `gf.configure_postgis(...)`

Configure default PostGIS connection parameters.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `host` | `str \| None` | `None` | Database host |
| `port` | `int \| None` | `None` | Database port (typically 5432) |
| `database` | `str \| None` | `None` | Database name |
| `user` | `str \| None` | `None` | Database user |
| `password` | `str \| None` | `None` | Database password |
| `sslmode` | `str \| None` | `None` | SSL mode (disable, allow, prefer, require, verify-ca, verify-full) |

**Example:**
```python
gf.configure_postgis(
    host="db.example.com",
    port=5432,
    user="geouser",
    password="geopassword",
    sslmode="require"
)

# Now use shorter connection strings
ds = gf.open("postgresql:///mydb?table=public.buildings")
```

---

### `gf.configure_stac(...)`

Configure STAC catalog authentication.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_key` | `str \| None` | `None` | API key for authenticated catalogs |
| `headers` | `dict[str, str] \| None` | `None` | Custom HTTP headers |
| `default_catalog` | `str \| None` | `None` | Default STAC catalog URL |

**Example:**
```python
# API key authentication
gf.configure_stac(api_key="my-stac-api-key")

# Bearer token authentication
gf.configure_stac(
    headers={"Authorization": "Bearer eyJ..."}
)

# Combined configuration
gf.configure_stac(
    api_key="my-api-key",
    headers={"X-Custom-Header": "value"},
    default_catalog="https://planetarycomputer.microsoft.com/api/stac/v1"
)
```

---

### `gf.configure_http(...)`

Configure global HTTP settings for web requests.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `proxy` | `str \| None` | `None` | HTTP proxy URL |
| `timeout` | `int` | `30` | Request timeout in seconds |
| `headers` | `dict[str, str] \| None` | `None` | Custom HTTP headers for all requests |
| `verify_ssl` | `bool` | `True` | Verify SSL certificates |

**Example:**
```python
gf.configure_http(
    proxy="http://corporate-proxy:8080",
    timeout=60,
    headers={"User-Agent": "MyApp/1.0"},
    verify_ssl=True
)
```

---

### `gf.get_config()`

Get the current GeoFabric configuration.

**Returns:** `GeoFabricConfig` - The global configuration object

**Example:**
```python
config = gf.get_config()
print(config.s3.access_key_id)
print(config.postgis.host)
```

---

### `gf.reset_config()`

Reset all configuration to defaults, clearing any programmatically set credentials.

**Example:**
```python
gf.configure_s3(access_key_id="...", secret_access_key="...")
gf.reset_config()  # Clears S3 credentials, reverts to env vars
```

---

## ROI (Region of Interest) Functions

### `gf.roi.bbox(minx, miny, maxx, maxy, srid=4326)`

Create a bounding box ROI.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `minx` | `float` | - | Minimum X coordinate (longitude) |
| `miny` | `float` | - | Minimum Y coordinate (latitude) |
| `maxx` | `float` | - | Maximum X coordinate (longitude) |
| `maxy` | `float` | - | Maximum Y coordinate (latitude) |
| `srid` | `int` | `4326` | Spatial Reference ID |

**Returns:** `ROI`

**Example:**
```python
# New York City area
roi = gf.roi.bbox(-74.10, 40.60, -73.70, 40.90)
result = ds.within(roi).to_pandas()
```

---

### `gf.roi.wkt(wkt_text, srid=4326)`

Create an ROI from WKT (Well-Known Text) geometry.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `wkt_text` | `str` | - | WKT geometry string |
| `srid` | `int` | `4326` | Spatial Reference ID |

**Returns:** `ROI`

**Example:**
```python
# Polygon ROI
roi = gf.roi.wkt("POLYGON((-74.0 40.7, -74.0 40.8, -73.9 40.8, -73.9 40.7, -74.0 40.7))")
result = ds.within(roi).to_pandas()
```

---

## Cache Functions

### `gf.configure_cache(...)`

Configure the global query cache.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `cache_dir` | `str \| None` | `~/.geofabric/cache` | Cache directory path |
| `enabled` | `bool` | `True` | Enable/disable caching |
| `max_size_mb` | `int` | `1000` | Maximum cache size in MB |

**Example:**
```python
gf.configure_cache(
    cache_dir="/tmp/geofabric_cache",
    enabled=True,
    max_size_mb=2000
)
```

---

### `gf.get_cache()`

Get the global cache instance.

**Returns:** `QueryCache`

**Example:**
```python
cache = gf.get_cache()
print(f"Cache size: {cache.size_mb():.2f} MB")
cache.clear()  # Clear all cached data
```

---

## Validation Functions

### `gf.validate_geometries(engine, sql, geometry_col="geometry", id_col=None)`

Validate geometries in a query result.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `engine` | `DuckDBEngine` | - | Database engine |
| `sql` | `str` | - | SQL query |
| `geometry_col` | `str` | `"geometry"` | Geometry column name |
| `id_col` | `str \| None` | `None` | ID column for issue reporting |

**Returns:** `ValidationResult`

---

### `gf.compute_stats(engine, sql, geometry_col="geometry")`

Compute statistics for a query result.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `engine` | `DuckDBEngine` | - | Database engine |
| `sql` | `str` | - | SQL query |
| `geometry_col` | `str` | `"geometry"` | Geometry column name |

**Returns:** `DatasetStats`

---

## Dataset Class

The `Dataset` class represents a geospatial data source.

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `columns` | `list[str]` | List of column names |
| `dtypes` | `dict[str, str]` | Mapping of column names to data types |

### Methods

#### `dataset.query()`
Create a new Query object for this dataset.

**Returns:** `Query`

---

#### `dataset.within(roi)`
Filter to geometries within the ROI.

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `roi` | `ROI` | Region of interest |

**Returns:** `Query`

---

#### `dataset.where(sql_predicate)`
Filter with a SQL predicate.

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `sql_predicate` | `str` | SQL WHERE clause condition |

**Returns:** `Query`

---

#### `dataset.select(columns)`
Select specific columns.

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `columns` | `str \| Sequence[str]` | Column(s) to select |

**Returns:** `Query`

---

#### `dataset.limit(n)`
Limit the number of results.

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `n` | `int` | Maximum number of rows |

**Returns:** `Query`

---

#### `dataset.count()`
Return the total number of rows.

**Returns:** `int`

---

#### `dataset.head(n=10)`
Return the first n rows.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `n` | `int` | `10` | Number of rows |

**Returns:** `pd.DataFrame`

---

#### `dataset.sample(n=10, seed=None)`
Return a random sample of n rows.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `n` | `int` | `10` | Number of rows |
| `seed` | `int \| None` | `None` | Random seed |

**Returns:** `pd.DataFrame`

---

#### `dataset.validate(geometry_col="geometry", id_col=None)`
Validate geometries in the dataset.

**Returns:** `ValidationResult`

---

#### `dataset.stats(geometry_col="geometry")`
Compute statistics for the dataset.

**Returns:** `DatasetStats`

---

## Query Class

The `Query` class provides a fluent API for building and executing queries.

### Filtering Methods

#### `query.select(columns)`
Select specific columns.

**Returns:** `Query`

---

#### `query.where(sql_predicate)`
Add a SQL WHERE condition.

**Example:**
```python
query.where("population > 1000000")
query.where("type IN ('residential', 'commercial')")
```

**Returns:** `Query`

---

#### `query.within(roi, geometry_col="geometry")`
Filter to geometries within the ROI.

**Returns:** `Query`

---

#### `query.limit(n)`
Limit the number of results.

**Returns:** `Query`

---

### Spatial Transformation Methods

#### `query.buffer(distance, unit="meters", geometry_col="geometry")`
Buffer geometries by a distance.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `distance` | `float` | - | Buffer distance |
| `unit` | `str` | `"meters"` | Distance unit |
| `geometry_col` | `str` | `"geometry"` | Geometry column |

**Returns:** `Query`

---

#### `query.simplify(tolerance, preserve_topology=True, geometry_col="geometry")`
Simplify geometries with a tolerance.

**Returns:** `Query`

---

#### `query.centroid(geometry_col="geometry")`
Replace geometries with their centroids.

**Returns:** `Query`

---

#### `query.convex_hull(geometry_col="geometry")`
Replace geometries with their convex hulls.

**Returns:** `Query`

---

#### `query.envelope(geometry_col="geometry")`
Replace geometries with their bounding boxes.

**Returns:** `Query`

---

#### `query.make_valid(geometry_col="geometry")`
Repair invalid geometries using ST_MakeValid.

**Returns:** `Query`

---

#### `query.transform(to_srid, from_srid=4326, geometry_col="geometry")`
Transform geometries to a different CRS.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `to_srid` | `int` | - | Target SRID (e.g., 3857) |
| `from_srid` | `int` | `4326` | Source SRID |

**Returns:** `Query`

---

#### `query.clip(clip_wkt, geometry_col="geometry")`
Clip geometries to a boundary (intersection).

**Returns:** `Query`

---

#### `query.erase(erase_wkt, geometry_col="geometry")`
Erase a region from geometries (difference).

**Returns:** `Query`

---

#### `query.boundary(geometry_col="geometry")`
Extract geometry boundaries.

**Returns:** `Query`

---

#### `query.explode(geometry_col="geometry")`
Explode multi-part geometries into single-part geometries.

**Returns:** `Query`

---

#### `query.densify(max_distance, geometry_col="geometry")`
Add intermediate vertices along geometry edges.

**Returns:** `Query`

---

#### `query.point_on_surface(geometry_col="geometry")`
Replace geometries with a point guaranteed to be on the surface.

**Returns:** `Query`

---

#### `query.reverse(geometry_col="geometry")`
Reverse the order of vertices in geometries.

**Returns:** `Query`

---

#### `query.flip_coordinates(geometry_col="geometry")`
Flip X and Y coordinates (useful for lat/lon vs lon/lat issues).

**Returns:** `Query`

---

#### `query.collect(geometry_col="geometry")`
Collect all geometries into a single MultiGeometry.

**Returns:** `Query`

---

#### `query.symmetric_difference(other_wkt, geometry_col="geometry")`
Compute symmetric difference (XOR) with another geometry.

**Returns:** `Query`

---

#### `query.dissolve(by=None, geometry_col="geometry")`
Dissolve geometries, optionally grouped by columns.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `by` | `str \| list[str] \| None` | `None` | Group by column(s) |

**Returns:** `Query`

---

### Computed Column Methods

#### `query.with_area(column_name="area", geometry_col="geometry")`
Add an area column computed from geometries.

**Returns:** `Query`

---

#### `query.with_length(column_name="length", geometry_col="geometry")`
Add a length/perimeter column computed from geometries.

**Returns:** `Query`

---

#### `query.with_perimeter(column_name="perimeter", geometry_col="geometry")`
Alias for `with_length()` for semantic clarity with polygons.

**Returns:** `Query`

---

#### `query.with_bounds(geometry_col="geometry")`
Add columns for geometry bounding box (minx, miny, maxx, maxy).

**Returns:** `Query`

---

#### `query.with_geometry_type(column_name="geom_type", geometry_col="geometry")`
Add a column with the geometry type.

**Returns:** `Query`

---

#### `query.with_num_points(column_name="num_points", geometry_col="geometry")`
Add a column with the number of points in each geometry.

**Returns:** `Query`

---

#### `query.with_is_valid(column_name="is_valid", geometry_col="geometry")`
Add a column indicating if each geometry is valid.

**Returns:** `Query`

---

#### `query.with_distance_to(reference_wkt, column_name="distance", geometry_col="geometry")`
Add a column with distance to a reference geometry.

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `reference_wkt` | `str` | WKT string of reference geometry |

**Returns:** `Query`

---

#### `query.with_x(column_name="x", geometry_col="geometry")`
Add a column with X coordinate (longitude).

**Returns:** `Query`

---

#### `query.with_y(column_name="y", geometry_col="geometry")`
Add a column with Y coordinate (latitude).

**Returns:** `Query`

---

#### `query.with_coordinates(x_column="x", y_column="y", geometry_col="geometry")`
Add X and Y coordinate columns.

**Returns:** `Query`

---

### Spatial Join Methods

#### `query.sjoin(other, predicate="intersects", how="inner", lsuffix="_left", rsuffix="_right", geometry_col="geometry")`
Spatial join with another query.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `other` | `Query` | - | Other query to join with |
| `predicate` | `str` | `"intersects"` | Spatial predicate |
| `how` | `str` | `"inner"` | Join type ('inner', 'left') |

**Supported predicates:** `intersects`, `within`, `contains`, `touches`, `crosses`, `overlaps`

**Returns:** `Query`

---

#### `query.nearest(other, k=1, max_distance=None, geometry_col="geometry")`
Find k nearest neighbors from another query.

Columns from the right query that conflict with left query columns are automatically renamed with a `_right` suffix. The distance to each neighbor is returned in the `_distance` column.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `other` | `Query` | - | Query with reference features |
| `k` | `int` | `1` | Number of nearest neighbors |
| `max_distance` | `float \| None` | `None` | Maximum search distance |

**Returns:** `Query` - Contains left columns, renamed right columns (with `_right` suffix for conflicts), and `_distance` column

**Example:**
```python
# Find nearest hospital for each building
buildings = gf.open("buildings.parquet")
hospitals = gf.open("hospitals.parquet")

result = buildings.query().nearest(hospitals.query(), k=1)
# If both have 'name' column: result has 'name' (building) and 'name_right' (hospital)
# Result also includes '_distance' column with the distance to nearest neighbor
```

---

### Inspection Methods

#### `query.count()`
Return the number of rows matching the query.

**Returns:** `int`

---

#### `query.head(n=10)`
Return the first n rows as a DataFrame.

**Returns:** `pd.DataFrame`

---

#### `query.sample(n=10, seed=None)`
Return a random sample of n rows.

**Returns:** `pd.DataFrame`

---

#### `query.columns`
Return list of column names.

**Returns:** `list[str]`

---

#### `query.dtypes`
Return mapping of column names to data types.

**Returns:** `dict[str, str]`

---

#### `query.describe(geometry_col="geometry")`
Return summary statistics.

**Returns:** `pd.DataFrame`

---

#### `query.explain()`
Return the query execution plan.

**Returns:** `str`

---

#### `query.sql()`
Return the generated SQL.

**Returns:** `str`

---

### Output Methods

#### `query.to_pandas()`
Execute query and return as pandas DataFrame.

**Returns:** `pd.DataFrame`

---

#### `query.to_geopandas(geometry_col="geometry")`
Execute query and return as GeoDataFrame.

**Requires:** `pip install geofabric[viz]`

**Returns:** `gpd.GeoDataFrame`

---

#### `query.to_arrow()`
Execute query and return as PyArrow Table.

**Returns:** `pa.Table`

---

#### `query.to_parquet(path, geometry_col="geometry")`
Export to Parquet file (with GeoParquet metadata if geopandas available).

**Returns:** `str` (path)

---

#### `query.to_geojson(path)`
Export to GeoJSON file.

**Returns:** `str` (path)

---

#### `query.to_pmtiles(pmtiles_path, *, layer="features", maxzoom=14, minzoom=0, geometry_col="geometry")`
Export to PMTiles format for web mapping.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `pmtiles_path` | `str` | - | Output file path |
| `layer` | `str` | `"features"` | Layer name |
| `maxzoom` | `int` | `14` | Maximum zoom level |
| `minzoom` | `int` | `0` | Minimum zoom level |

**Returns:** `str` (path)

---

#### `query.to_flatgeobuf(path, geometry_col="geometry")`
Export to FlatGeobuf format.

**Returns:** `str` (path)

---

#### `query.to_geopackage(path, layer="data", geometry_col="geometry")`
Export to GeoPackage format.

**Returns:** `str` (path)

---

#### `query.to_csv(path, include_wkt=True, geometry_col="geometry")`
Export to CSV format (optionally with WKT geometry).

**Returns:** `str` (path)

---

#### `query.show(geometry_col="geometry")`
Display results interactively using lonboard.

**Requires:** `pip install geofabric[viz]`

**Returns:** Interactive map widget

---

### Streaming Methods

#### `query.iter_chunks(chunk_size=10000)`
Iterate over query results in PyArrow RecordBatch chunks.

**Yields:** `pa.RecordBatch`

---

#### `query.iter_dataframes(chunk_size=10000)`
Iterate over query results as DataFrames.

**Yields:** `pd.DataFrame`

---

### Aggregation Methods

#### `query.aggregate(agg)`
Aggregate results.

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `agg` | `dict[str, str]` | Aggregation specification (e.g., `{"by": "type"}`) |

**Returns:** `pd.DataFrame`

---

## Data Classes

### `ValidationResult`

Result of geometry validation.

| Field | Type | Description |
|-------|------|-------------|
| `total_rows` | `int` | Total number of rows |
| `valid_count` | `int` | Number of valid geometries |
| `invalid_count` | `int` | Number of invalid geometries |
| `null_count` | `int` | Number of null geometries |
| `issues` | `list[ValidationIssue]` | List of validation issues |
| `is_valid` | `bool` | Whether all geometries are valid |

**Methods:**
- `summary()` - Returns a formatted summary string

---

### `ValidationIssue`

A geometry validation issue.

| Field | Type | Description |
|-------|------|-------------|
| `row_id` | `Any` | Row identifier |
| `issue_type` | `str` | Type of issue |
| `message` | `str` | Issue description |

---

### `DatasetStats`

Statistics about a dataset.

| Field | Type | Description |
|-------|------|-------------|
| `row_count` | `int` | Total number of rows |
| `column_count` | `int` | Number of columns |
| `columns` | `list[str]` | Column names |
| `dtypes` | `dict[str, str]` | Column data types |
| `bounds` | `tuple[float, float, float, float] \| None` | Bounding box (minx, miny, maxx, maxy) |
| `geometry_type` | `str \| None` | Predominant geometry type |
| `crs` | `str \| None` | Coordinate reference system |
| `null_counts` | `dict[str, int]` | Null counts per column |

**Methods:**
- `summary()` - Returns a formatted summary string

---

### `ROI`

Region of interest for spatial queries.

| Field | Type | Description |
|-------|------|-------------|
| `kind` | `str` | ROI type ('bbox' or 'wkt') |
| `wkt` | `str \| None` | WKT geometry (for wkt kind) |
| `minx`, `miny`, `maxx`, `maxy` | `float \| None` | Bounding box coordinates |
| `srid` | `int` | Spatial reference ID (default: 4326) |

---

### Configuration Classes

#### `GeoFabricConfig`
| Field | Type | Description |
|-------|------|-------------|
| `s3` | `S3Config` | S3 configuration |
| `gcs` | `GCSConfig` | GCS configuration |
| `azure` | `AzureConfig` | Azure configuration |
| `postgis` | `PostGISConfig` | PostGIS configuration |
| `stac` | `STACConfig` | STAC configuration |
| `http` | `HTTPConfig` | HTTP configuration |

#### `S3Config`
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `access_key_id` | `str \| None` | `None` | AWS access key ID |
| `secret_access_key` | `str \| None` | `None` | AWS secret access key |
| `region` | `str \| None` | `None` | AWS region |
| `session_token` | `str \| None` | `None` | Session token |
| `endpoint` | `str \| None` | `None` | Custom endpoint |
| `use_ssl` | `bool` | `True` | Use SSL |

#### `GCSConfig`
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `access_key_id` | `str \| None` | `None` | HMAC access key |
| `secret_access_key` | `str \| None` | `None` | HMAC secret |
| `project` | `str \| None` | `None` | GCP project ID |

#### `AzureConfig`
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `account_name` | `str \| None` | `None` | Storage account name |
| `account_key` | `str \| None` | `None` | Storage account key |
| `connection_string` | `str \| None` | `None` | Connection string |
| `sas_token` | `str \| None` | `None` | SAS token |

#### `PostGISConfig`
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `host` | `str \| None` | `None` | Database host |
| `port` | `int \| None` | `None` | Database port |
| `database` | `str \| None` | `None` | Database name |
| `user` | `str \| None` | `None` | Database user |
| `password` | `str \| None` | `None` | Database password |
| `sslmode` | `str \| None` | `None` | SSL mode |

#### `STACConfig`
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `api_key` | `str \| None` | `None` | API key |
| `headers` | `dict[str, str]` | `{}` | Custom headers |
| `default_catalog` | `str \| None` | `None` | Default catalog URL |

#### `HTTPConfig`
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `proxy` | `str \| None` | `None` | Proxy URL |
| `timeout` | `int` | `30` | Timeout in seconds |
| `headers` | `dict[str, str]` | `{}` | Custom headers |
| `verify_ssl` | `bool` | `True` | Verify SSL certs |

---

## Credential Precedence

GeoFabric follows industry-standard credential resolution:

1. **Programmatic configuration** (highest priority)
   ```python
   gf.configure_s3(access_key_id="...", secret_access_key="...")
   ```

2. **Environment variables**
   ```bash
   export AWS_ACCESS_KEY_ID="..."
   export AWS_SECRET_ACCESS_KEY="..."
   ```

3. **Credential files** (e.g., `~/.aws/credentials`)

4. **Instance metadata** (IAM roles, service accounts)

---

## Version

Access the library version:

```python
import geofabric as gf
print(gf.__version__)
```
