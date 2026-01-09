# API Reference

> **Note:** For a comprehensive API reference with full parameter details, examples, and data class documentation, see [API_REFERENCE.md](API_REFERENCE.md).

## Core Functions

### `geofabric.open(uri)`

Open a dataset from various sources.

**Parameters:**
- `uri` (str): Data source URI

**Supported URI formats:**
| Source | Format | Example |
|--------|--------|---------|
| Local files | `file:///path` | `file:///data/buildings.parquet` |
| S3 | `s3://bucket/key` | `s3://my-bucket/data.parquet` |
| GCS | `gs://bucket/key` | `gs://my-bucket/data.parquet` |
| Azure | `az://container/path` | `az://mycontainer/data.parquet` |
| PostGIS | `postgresql://...` | `postgresql://user:pass@host/db?table=mytable` |
| STAC | `stac://...` | `stac://catalog-url/collection` |

**Returns:** `Dataset`

---

## Dataset

The `Dataset` class represents a connection to a data source.

### Methods

| Method | Description |
|--------|-------------|
| `query()` | Create a new Query builder |
| `within(roi)` | Filter by region of interest |
| `where(predicate)` | Add SQL WHERE clause |
| `select(columns)` | Select specific columns |
| `limit(n)` | Limit number of rows |
| `head(n=10)` | Get first n rows as DataFrame |
| `sample(n=10)` | Get random sample as DataFrame |
| `count()` | Count total rows |
| `validate()` | Validate geometries |
| `stats()` | Compute dataset statistics |

### Properties

| Property | Description |
|----------|-------------|
| `columns` | List of column names |
| `dtypes` | Dictionary of column types |

---

## Query

The `Query` class provides a lazy, chainable query builder.

### Selection & Filtering

| Method | Description |
|--------|-------------|
| `select(columns)` | Select columns (str or list) |
| `where(predicate)` | Add WHERE clause |
| `within(roi)` | Filter by ROI (bbox or WKT) |
| `limit(n)` | Limit rows |

### Output Methods

| Method | Description |
|--------|-------------|
| `sql()` | Get generated SQL string |
| `to_pandas()` | Execute and return DataFrame |
| `to_arrow()` | Execute and return Arrow Table |
| `to_geopandas()` | Execute and return GeoDataFrame |
| `to_parquet(path)` | Write to Parquet file |
| `to_geojson(path)` | Write to GeoJSON file |
| `to_geopackage(path)` | Write to GeoPackage |
| `to_flatgeobuf(path)` | Write to FlatGeoBuf |
| `to_csv(path)` | Write to CSV (with WKT geometry) |
| `to_pmtiles(path)` | Write to PMTiles (requires tippecanoe) |
| `show()` | Visualize in notebook (requires viz extras) |

### Spatial Transformations

| Method | Description |
|--------|-------------|
| `buffer(distance, unit)` | Buffer geometries |
| `simplify(tolerance)` | Simplify geometries |
| `transform(to_srid)` | Transform CRS |
| `centroid()` | Get geometry centroids |
| `convex_hull()` | Get convex hulls |
| `envelope()` | Get bounding boxes |
| `boundary()` | Extract boundaries |
| `make_valid()` | Repair invalid geometries |
| `densify(max_distance)` | Add vertices |
| `explode()` | Split multi-geometries |
| `collect()` | Gather into MultiGeometry |
| `dissolve(by)` | Merge geometries by attribute |
| `clip(wkt)` | Clip to geometry (intersection) |
| `erase(wkt)` | Erase geometry (difference) |
| `symmetric_difference(wkt)` | XOR with geometry |
| `point_on_surface()` | Get point on surface |
| `reverse()` | Reverse vertex order |
| `flip_coordinates()` | Swap X/Y coordinates |

### Computed Columns

| Method | Description |
|--------|-------------|
| `with_area(col_name)` | Add area column |
| `with_length(col_name)` | Add length/perimeter column |
| `with_perimeter(col_name)` | Add perimeter column |
| `with_bounds(prefix)` | Add minx, miny, maxx, maxy columns |
| `with_distance_to(wkt, col_name)` | Add distance column |
| `with_x(col_name)` | Add X coordinate column |
| `with_y(col_name)` | Add Y coordinate column |
| `with_coordinates(x_col, y_col)` | Add X and Y columns |
| `with_geometry_type(col_name)` | Add geometry type column |
| `with_num_points(col_name)` | Add vertex count column |
| `with_is_valid(col_name)` | Add validity check column |

### Spatial Joins

| Method | Description |
|--------|-------------|
| `sjoin(other, predicate, how)` | Spatial join with predicates: intersects, within, contains, touches, crosses, overlaps |
| `nearest(other, k, max_distance)` | K-nearest neighbor join (conflicting columns get `_right` suffix) |

### Analytics

| Method | Description |
|--------|-------------|
| `aggregate(agg)` | GROUP BY with aggregations |
| `count()` | Count rows |
| `head(n)` | Get first n rows |
| `sample(n, seed)` | Get random sample |
| `describe()` | Get statistics |
| `explain()` | Get query plan |

---

## ROI (Region of Interest)

### `geofabric.roi.bbox(minx, miny, maxx, maxy, srid=4326)`

Create a bounding box ROI.

### `geofabric.roi.wkt(wkt_text, srid=4326)`

Create a WKT geometry ROI.

---

## Configuration

Programmatic configuration for credentials and settings. Takes precedence over environment variables.

### Cloud Storage

| Function | Parameters | Description |
|----------|------------|-------------|
| `configure_s3()` | access_key_id, secret_access_key, region, session_token, endpoint, use_ssl | AWS S3 credentials |
| `configure_gcs()` | access_key_id, secret_access_key, project | Google Cloud Storage |
| `configure_azure()` | account_name, account_key, connection_string, sas_token | Azure Blob Storage |

### Databases

| Function | Parameters | Description |
|----------|------------|-------------|
| `configure_postgis()` | host, port, database, user, password, sslmode | PostgreSQL/PostGIS defaults |

### APIs & HTTP

| Function | Parameters | Description |
|----------|------------|-------------|
| `configure_stac()` | api_key, headers, default_catalog | STAC catalog authentication |
| `configure_http()` | proxy, timeout, headers, verify_ssl | Global HTTP settings |

### Utility

| Function | Description |
|----------|-------------|
| `reset_config()` | Clear all programmatic configuration |
| `get_config()` | Get current configuration object |

**Example:**
```python
import geofabric as gf

gf.configure_s3(
    access_key_id="AKIA...",
    secret_access_key="...",
    region="us-east-1"
)
ds = gf.open("s3://my-bucket/data.parquet?anonymous=false")
```

See [Authentication Guide](../examples/AUTHENTICATION.md) for detailed usage.

---

## Validation

### `geofabric.validate_geometries(engine, sql, geometry_col, id_col)`

Validate geometries and return `ValidationResult`.

### `geofabric.compute_stats(engine, sql, geometry_col)`

Compute dataset statistics and return `DatasetStats`.

---

## Data Classes

### `ValidationResult`
- `total_rows`: Total row count
- `valid_count`: Valid geometry count
- `invalid_count`: Invalid geometry count
- `null_count`: NULL geometry count
- `issues`: List of `ValidationIssue`

### `DatasetStats`
- `row_count`: Total rows
- `column_count`: Number of columns
- `columns`: List of column names
- `dtypes`: Dictionary of column types
- `bounds`: Geometry bounds (minx, miny, maxx, maxy)
- `geometry_type`: Geometry type
- `crs`: Coordinate reference system
- `null_counts`: NULL counts per column

---

## CLI Commands

| Command | Description |
|---------|-------------|
| `gf sql URI QUERY` | Run SQL query |
| `gf pull URI OUT` | Extract data subset |
| `gf info URI` | Show dataset info |
| `gf stats URI` | Show statistics |
| `gf validate URI` | Validate geometries |
| `gf head URI` | Show first rows |
| `gf sample URI OUT` | Random sample |
| `gf buffer URI OUT` | Buffer geometries |
| `gf simplify URI OUT` | Simplify geometries |
| `gf transform URI OUT` | Transform CRS |
| `gf centroid URI OUT` | Compute centroids |
| `gf convex-hull URI OUT` | Compute convex hulls |
| `gf dissolve URI OUT` | Dissolve geometries |
| `gf add-area URI OUT` | Add area column |
| `gf add-length URI OUT` | Add length column |
| `gf overture download` | Download Overture data |
