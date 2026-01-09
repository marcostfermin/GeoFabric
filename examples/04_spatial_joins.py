#!/usr/bin/env python3
"""
Spatial Joins Examples for GeoFabric

This script demonstrates spatial join operations:
- Spatial joins with various predicates
- K-nearest neighbor queries
- Join types (inner, left)
"""

import geofabric as gf


def basic_spatial_join() -> None:
    """Perform a basic spatial join between two datasets."""
    # Open two datasets
    buildings = gf.open("file:///data/buildings.parquet")
    parcels = gf.open("file:///data/parcels.parquet")

    # Join buildings to parcels where they intersect
    joined = buildings.query().sjoin(
        parcels.query(),
        predicate="intersects",
        how="inner",
    )

    result = joined.to_pandas()
    print(f"Joined {len(result)} building-parcel pairs")


def spatial_join_predicates() -> None:
    """Demonstrate different spatial join predicates."""
    buildings = gf.open("file:///data/buildings.parquet")
    zones = gf.open("file:///data/zones.parquet")

    # INTERSECTS - geometries share any space
    intersects = buildings.query().sjoin(
        zones.query(),
        predicate="intersects",
        how="inner",
    )

    # WITHIN - building completely inside zone
    within = buildings.query().sjoin(
        zones.query(),
        predicate="within",
        how="inner",
    )

    # CONTAINS - zone completely contains building
    # Note: This joins zones to buildings where zone contains building
    contains = zones.query().sjoin(
        buildings.query(),
        predicate="contains",
        how="inner",
    )

    # TOUCHES - geometries share boundary but not interior
    touches = buildings.query().sjoin(
        zones.query(),
        predicate="touches",
        how="inner",
    )

    # CROSSES - geometries cross each other (typically lines)
    roads = gf.open("file:///data/roads.parquet")
    rivers = gf.open("file:///data/rivers.parquet")
    crosses = roads.query().sjoin(
        rivers.query(),
        predicate="crosses",
        how="inner",
    )

    # OVERLAPS - geometries overlap but neither contains the other
    overlaps = buildings.query().sjoin(
        zones.query(),
        predicate="overlaps",
        how="inner",
    )

    print("Available predicates: intersects, within, contains, touches, crosses, overlaps")


def spatial_join_types() -> None:
    """Demonstrate inner vs left joins."""
    buildings = gf.open("file:///data/buildings.parquet")
    parcels = gf.open("file:///data/parcels.parquet")

    # INNER JOIN - only matching pairs
    inner_join = buildings.query().sjoin(
        parcels.query(),
        predicate="intersects",
        how="inner",
    )
    inner_result = inner_join.to_pandas()
    print(f"Inner join: {len(inner_result)} rows")

    # LEFT JOIN - all buildings, with parcel info where available
    left_join = buildings.query().sjoin(
        parcels.query(),
        predicate="intersects",
        how="left",
    )
    left_result = left_join.to_pandas()
    print(f"Left join: {len(left_result)} rows")


def k_nearest_neighbors() -> None:
    """Find K nearest neighbors."""
    buildings = gf.open("file:///data/buildings.parquet")
    hospitals = gf.open("file:///data/hospitals.parquet")

    # Find 3 nearest hospitals for each building
    nearest = buildings.query().nearest(
        hospitals.query(),
        k=3,
    )

    result = nearest.to_pandas()
    print(f"Found nearest hospitals: {len(result)} pairs")


def nearest_with_max_distance() -> None:
    """Find nearest neighbors within a maximum distance."""
    buildings = gf.open("file:///data/buildings.parquet")
    transit_stops = gf.open("file:///data/transit_stops.parquet")

    # Find up to 5 nearest transit stops within 500 units
    nearest = buildings.query().nearest(
        transit_stops.query(),
        k=5,
        max_distance=500,  # In CRS units
    )

    result = nearest.to_pandas()
    print(f"Found nearby transit stops: {len(result)} pairs")


def join_with_region_filter() -> None:
    """Combine spatial join with region filtering."""
    buildings = gf.open("file:///data/buildings.parquet")
    parcels = gf.open("file:///data/parcels.parquet")

    # Define region of interest
    roi = gf.roi.bbox(-74.10, 40.60, -73.70, 40.90)

    # Filter both datasets to region, then join
    joined = (
        buildings.query()
        .within(roi)
        .sjoin(
            parcels.query().within(roi),
            predicate="intersects",
            how="inner",
        )
    )

    result = joined.to_pandas()
    print(f"Joined {len(result)} pairs in region")


def join_with_attribute_filter() -> None:
    """Combine spatial join with attribute filtering."""
    buildings = gf.open("file:///data/buildings.parquet")
    zones = gf.open("file:///data/zones.parquet")

    # Filter buildings before joining
    joined = (
        buildings.query()
        .where("type = 'commercial'")
        .sjoin(
            zones.query().where("zone_type = 'business'"),
            predicate="within",
            how="inner",
        )
    )

    result = joined.to_pandas()
    print(f"Found {len(result)} commercial buildings in business zones")


def join_and_export() -> None:
    """Perform spatial join and export results."""
    buildings = gf.open("file:///data/buildings.parquet")
    parcels = gf.open("file:///data/parcels.parquet")

    # Join and export
    joined = buildings.query().sjoin(
        parcels.query(),
        predicate="intersects",
        how="inner",
    )

    # Export to various formats
    joined.to_parquet("joined_buildings_parcels.parquet")
    joined.to_geojson("joined_buildings_parcels.geojson")
    joined.to_geopackage("joined_buildings_parcels.gpkg")

    print("Exported joined results to multiple formats")


def complex_spatial_analysis() -> None:
    """Complex analysis combining joins and operations."""
    buildings = gf.open("file:///data/buildings.parquet")
    parcels = gf.open("file:///data/parcels.parquet")
    flood_zones = gf.open("file:///data/flood_zones.parquet")

    roi = gf.roi.bbox(-74.10, 40.60, -73.70, 40.90)

    # Find buildings in flood zones with parcel information
    result = (
        buildings.query()
        .within(roi)
        .where("year_built < 2000")
        .sjoin(
            flood_zones.query().where("risk_level = 'high'"),
            predicate="intersects",
            how="inner",
        )
        .with_area(col_name="building_area")
        .to_pandas()
    )

    print(f"Found {len(result)} at-risk buildings")


def main() -> None:
    """Run all examples."""
    print("=" * 60)
    print("GeoFabric Spatial Joins Examples")
    print("=" * 60)

    print("\nSpatial Join Methods:")
    print("- sjoin(other, predicate, how)")
    print("  Predicates: intersects, within, contains, touches, crosses, overlaps")
    print("  Join types: inner, left")
    print("")
    print("- nearest(other, k, max_distance)")
    print("  K-nearest neighbor join")
    print("  Optional max_distance filtering")

    print("\nUncomment function calls to run with real data.")


if __name__ == "__main__":
    main()
