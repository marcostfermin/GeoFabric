#!/usr/bin/env python3
"""
Computed Columns Examples for GeoFabric

This script demonstrates adding computed columns:
- Area and length measurements
- Bounding box coordinates
- Distance calculations
- Coordinate extraction
- Geometry metadata
"""

import geofabric as gf


def add_area_column() -> None:
    """Add area measurement column."""
    ds = gf.open("file:///data/parcels.parquet")

    # Add area column (in CRS units, typically square degrees for WGS84)
    with_area = ds.query().with_area().limit(100)

    # Custom column name
    with_area_named = ds.query().with_area(col_name="area_sq_units").limit(100)

    result = with_area.to_pandas()
    print(f"Added area column to {len(result)} rows")
    print(f"Columns: {list(result.columns)}")


def add_length_column() -> None:
    """Add length/perimeter measurement column."""
    ds = gf.open("file:///data/roads.parquet")

    # Add length column for linestrings
    with_length = ds.query().with_length().limit(100)

    # Custom column name
    with_length_named = ds.query().with_length(col_name="road_length").limit(100)

    result = with_length.to_pandas()
    print(f"Added length column to {len(result)} rows")


def add_perimeter_column() -> None:
    """Add perimeter measurement column for polygons."""
    ds = gf.open("file:///data/parcels.parquet")

    # Add perimeter column
    with_perimeter = ds.query().with_perimeter().limit(100)

    # Custom column name
    with_perimeter_named = ds.query().with_perimeter(col_name="boundary_length").limit(100)

    result = with_perimeter.to_pandas()
    print(f"Added perimeter column to {len(result)} rows")


def add_bounds_columns() -> None:
    """Add bounding box coordinate columns."""
    ds = gf.open("file:///data/buildings.parquet")

    # Add minx, miny, maxx, maxy columns
    with_bounds = ds.query().with_bounds().limit(100)

    # Custom prefix
    with_bounds_prefixed = ds.query().with_bounds(prefix="bbox_").limit(100)

    result = with_bounds.to_pandas()
    print(f"Added bounds columns to {len(result)} rows")
    print(f"Columns: {list(result.columns)}")


def add_distance_column() -> None:
    """Add distance to reference geometry column."""
    ds = gf.open("file:///data/buildings.parquet")

    # Distance to a reference point (e.g., city center)
    city_center = "POINT(-74.006 40.7128)"  # NYC
    with_distance = ds.query().with_distance_to(city_center).limit(100)

    # Custom column name
    with_distance_named = ds.query().with_distance_to(
        city_center, col_name="distance_to_center"
    ).limit(100)

    result = with_distance.to_pandas()
    print(f"Added distance column to {len(result)} rows")


def add_coordinate_columns() -> None:
    """Add X and Y coordinate columns for point geometries."""
    ds = gf.open("file:///data/points.parquet")

    # Add X coordinate
    with_x = ds.query().with_x().limit(100)

    # Add Y coordinate
    with_y = ds.query().with_y().limit(100)

    # Add both X and Y
    with_coords = ds.query().with_coordinates().limit(100)

    # Custom column names
    with_coords_named = ds.query().with_coordinates(
        x_col="longitude", y_col="latitude"
    ).limit(100)

    result = with_coords.to_pandas()
    print(f"Added coordinate columns to {len(result)} rows")
    print(f"Columns: {list(result.columns)}")


def add_geometry_type_column() -> None:
    """Add geometry type column."""
    ds = gf.open("file:///data/mixed_geometries.parquet")

    # Add column with geometry type (Point, LineString, Polygon, etc.)
    with_type = ds.query().with_geometry_type().limit(100)

    # Custom column name
    with_type_named = ds.query().with_geometry_type(col_name="geom_type").limit(100)

    result = with_type.to_pandas()
    print(f"Added geometry type column to {len(result)} rows")
    if "geometry_type" in result.columns:
        print(f"Geometry types: {result['geometry_type'].unique()}")


def add_vertex_count_column() -> None:
    """Add vertex count column."""
    ds = gf.open("file:///data/buildings.parquet")

    # Add column with number of vertices/points in geometry
    with_num_points = ds.query().with_num_points().limit(100)

    # Custom column name
    with_num_points_named = ds.query().with_num_points(col_name="vertex_count").limit(100)

    result = with_num_points.to_pandas()
    print(f"Added vertex count column to {len(result)} rows")


def add_validity_column() -> None:
    """Add geometry validity check column."""
    ds = gf.open("file:///data/buildings.parquet")

    # Add boolean column indicating if geometry is valid
    with_valid = ds.query().with_is_valid().limit(100)

    # Custom column name
    with_valid_named = ds.query().with_is_valid(col_name="geom_is_valid").limit(100)

    result = with_valid.to_pandas()
    print(f"Added validity column to {len(result)} rows")


def combine_computed_columns() -> None:
    """Add multiple computed columns at once."""
    ds = gf.open("file:///data/parcels.parquet")
    roi = gf.roi.bbox(-74.10, 40.60, -73.70, 40.90)

    # Chain multiple computed columns
    result = (
        ds.query()
        .within(roi)
        .with_area(col_name="area_sqm")
        .with_perimeter(col_name="perimeter_m")
        .with_bounds()
        .with_geometry_type()
        .with_is_valid()
        .limit(100)
        .to_pandas()
    )

    print(f"Added multiple computed columns to {len(result)} rows")
    print(f"Columns: {list(result.columns)}")


def computed_columns_with_spatial_ops() -> None:
    """Combine computed columns with spatial operations."""
    ds = gf.open("file:///data/buildings.parquet")
    roi = gf.roi.bbox(-74.10, 40.60, -73.70, 40.90)

    # Spatial operations followed by computed columns
    result = (
        ds.query()
        .within(roi)
        .buffer(distance=10, unit="meters")  # Buffer first
        .with_area(col_name="buffered_area")  # Then compute area
        .with_num_points(col_name="vertex_count")
        .limit(100)
        .to_pandas()
    )

    print(f"Processed {len(result)} geometries")
    print(f"Columns: {list(result.columns)}")


def analyze_with_computed_columns() -> None:
    """Use computed columns for analysis."""
    ds = gf.open("file:///data/parcels.parquet")

    # Add area and filter by it
    result = (
        ds.query()
        .with_area(col_name="area")
        .where("area > 1000")  # Filter by computed area
        .limit(100)
        .to_pandas()
    )

    print(f"Found {len(result)} large parcels")

    # Get statistics on computed columns
    if len(result) > 0:
        print(f"Area statistics:")
        print(f"  Min: {result['area'].min():.2f}")
        print(f"  Max: {result['area'].max():.2f}")
        print(f"  Mean: {result['area'].mean():.2f}")


def main() -> None:
    """Run all examples."""
    print("=" * 60)
    print("GeoFabric Computed Columns Examples")
    print("=" * 60)

    print("\nAvailable computed column methods:")
    print("- with_area(col_name='area')")
    print("- with_length(col_name='length')")
    print("- with_perimeter(col_name='perimeter')")
    print("- with_bounds(prefix='')")
    print("- with_distance_to(wkt, col_name='distance')")
    print("- with_x(col_name='x')")
    print("- with_y(col_name='y')")
    print("- with_coordinates(x_col='x', y_col='y')")
    print("- with_geometry_type(col_name='geometry_type')")
    print("- with_num_points(col_name='num_points')")
    print("- with_is_valid(col_name='is_valid')")

    print("\nUncomment function calls to run with real data.")


if __name__ == "__main__":
    main()
