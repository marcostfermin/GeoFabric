#!/usr/bin/env python3
"""
Basic Usage Examples for GeoFabric

This script demonstrates fundamental operations:
- Opening datasets from various sources
- Building queries with the fluent API
- Filtering by region of interest
- Using WHERE clauses
- Limiting and sampling data
"""

import geofabric as gf


def open_local_file() -> None:
    """Open a local Parquet file."""
    # GeoFabric uses URI-style paths for consistency
    ds = gf.open("file:///path/to/buildings.parquet")

    # Check available columns
    print(f"Columns: {ds.columns}")
    print(f"Data types: {ds.dtypes}")


def open_different_formats() -> None:
    """Open various file formats."""
    # Parquet (recommended for large datasets)
    ds_parquet = gf.open("file:///data/buildings.parquet")

    # GeoJSON
    ds_geojson = gf.open("file:///data/boundaries.geojson")

    # GeoPackage
    ds_gpkg = gf.open("file:///data/parcels.gpkg")

    # FlatGeoBuf
    ds_fgb = gf.open("file:///data/roads.fgb")

    # Shapefile
    ds_shp = gf.open("file:///data/points.shp")

    # CSV with WKT geometry
    ds_csv = gf.open("file:///data/locations.csv")


def basic_query() -> None:
    """Build a basic query."""
    ds = gf.open("file:///data/buildings.parquet")

    # Create a query builder
    query = ds.query()

    # Select specific columns
    query = query.select(["id", "name", "type", "geometry"])

    # Limit results
    query = query.limit(100)

    # Execute and get results as pandas DataFrame
    df = query.to_pandas()
    print(f"Retrieved {len(df)} rows")


def filter_by_region() -> None:
    """Filter data by geographic region."""
    ds = gf.open("file:///data/buildings.parquet")

    # Define region of interest using bounding box
    # bbox(minx, miny, maxx, maxy, srid=4326)
    nyc_bbox = gf.roi.bbox(-74.10, 40.60, -73.70, 40.90)

    # Filter by region
    query = ds.within(nyc_bbox).limit(1000)

    # Execute query
    result = query.to_pandas()
    print(f"Found {len(result)} buildings in NYC area")


def filter_by_polygon() -> None:
    """Filter data using a WKT polygon."""
    ds = gf.open("file:///data/buildings.parquet")

    # Define region using WKT
    manhattan = gf.roi.wkt(
        "POLYGON((-74.02 40.70, -73.97 40.70, -73.97 40.75, -74.02 40.75, -74.02 40.70))",
        srid=4326,
    )

    query = ds.within(manhattan).limit(500)
    result = query.to_pandas()
    print(f"Found {len(result)} buildings in Manhattan")


def use_where_clause() -> None:
    """Filter data using SQL WHERE clauses."""
    ds = gf.open("file:///data/buildings.parquet")

    # Single condition
    query = ds.query().where("type = 'commercial'").limit(100)

    # Multiple conditions (AND)
    query = ds.query().where("type = 'residential' AND height > 10").limit(100)

    # Using LIKE for pattern matching
    query = ds.query().where("name LIKE '%Tower%'").limit(100)

    # Combining with region filter
    roi = gf.roi.bbox(-74.10, 40.60, -73.70, 40.90)
    query = ds.within(roi).where("year_built >= 2000").limit(100)

    result = query.to_pandas()
    print(f"Found {len(result)} matching buildings")


def get_quick_preview() -> None:
    """Get quick previews of data."""
    ds = gf.open("file:///data/buildings.parquet")

    # Get first N rows (default 10)
    first_rows = ds.head(20)
    print(f"First 20 rows:\n{first_rows}")

    # Get random sample
    sample = ds.sample(50)
    print(f"Random sample of 50 rows:\n{sample}")

    # Count total rows
    total = ds.count()
    print(f"Total rows: {total}")


def chain_operations() -> None:
    """Chain multiple operations fluently."""
    ds = gf.open("file:///data/buildings.parquet")
    roi = gf.roi.bbox(-74.10, 40.60, -73.70, 40.90)

    # Fluent API allows chaining all operations
    result = (
        ds.query()
        .within(roi)
        .select(["id", "name", "type", "height", "geometry"])
        .where("height > 50")
        .limit(500)
        .to_pandas()
    )

    print(f"Retrieved {len(result)} tall buildings")


def view_generated_sql() -> None:
    """View the SQL that will be executed."""
    ds = gf.open("file:///data/buildings.parquet")
    roi = gf.roi.bbox(-74.10, 40.60, -73.70, 40.90)

    query = ds.within(roi).where("type = 'commercial'").limit(100)

    # Get the generated SQL (useful for debugging)
    sql = query.sql()
    print(f"Generated SQL:\n{sql}")


def main() -> None:
    """Run all examples."""
    print("=" * 60)
    print("GeoFabric Basic Usage Examples")
    print("=" * 60)

    # Note: These examples use placeholder paths.
    # Replace with actual file paths to run.

    print("\n1. Opening datasets...")
    # open_local_file()

    print("\n2. Basic queries...")
    # basic_query()

    print("\n3. Region filtering...")
    # filter_by_region()

    print("\n4. WHERE clauses...")
    # use_where_clause()

    print("\n5. Quick previews...")
    # get_quick_preview()

    print("\n6. Chained operations...")
    # chain_operations()

    print("\nExamples completed. Uncomment function calls to run with real data.")


if __name__ == "__main__":
    main()
