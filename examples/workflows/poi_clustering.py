#!/usr/bin/env python3
"""
POI Clustering Workflow

Features: where + buffer + collect + convex_hull + with_area
Use case: Create clusters around groups of restaurants.
"""

import geofabric as gf


def main() -> None:
    # Load POIs
    pois = gf.open("file:///data/points_of_interest.parquet")

    # Study area (Manhattan)
    manhattan = gf.roi.bbox(-74.02, 40.70, -73.97, 40.80)

    # Filter to restaurants
    restaurants = (
        pois.query()
        .within(manhattan)
        .where("category = 'restaurant'")
        .select(["poi_id", "name", "cuisine", "geometry"])
    )

    # Create small buffers around each restaurant
    restaurant_zones = (
        restaurants
        .buffer(distance=50, unit="meters")
        .with_area(col_name="buffer_area")
    )

    # Collect all restaurant points into one MultiPoint
    all_restaurants = restaurants.collect()

    # Create convex hull around all restaurants
    restaurant_hull = (
        restaurants
        .convex_hull()
        .with_area(col_name="hull_area")
    )

    # Export layers
    restaurants.to_geojson("restaurants_points.geojson")
    restaurant_zones.to_geojson("restaurant_buffers.geojson")
    restaurant_hull.to_geojson("restaurant_convex_hull.geojson")

    result = restaurants.to_pandas()
    print(f"Found {len(result)} restaurants in Manhattan")


if __name__ == "__main__":
    main()
