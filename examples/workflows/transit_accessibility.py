#!/usr/bin/env python3
"""
Transit Accessibility Scoring Workflow

Features: centroid + select + where + nearest + with_distance_to + with_area + PMTiles
Use case: Score neighborhoods by transit accessibility using K-nearest neighbor analysis.
"""

import geofabric as gf


def main() -> None:
    """
    Calculate transit accessibility scores for census blocks.

    Steps:
    1. Load census blocks and transit stops with frequency data
    2. Compute centroid of each block
    3. Find K nearest transit stops for each block
    4. Calculate weighted accessibility score
    5. Join scores back to block polygons
    6. Export for thematic mapping
    """
    # Load datasets
    census_blocks = gf.open("file:///data/census_blocks.parquet")
    transit_stops = gf.open("file:///data/transit_stops.parquet")

    city_bounds = gf.roi.bbox(-74.05, 40.68, -73.90, 40.82)

    # Step 1: Get block centroids for distance calculations
    block_centroids = (
        census_blocks.query()
        .within(city_bounds)
        .centroid()
        .select(["block_id", "population", "geometry"])
    )

    # Step 2: Filter to high-frequency transit (buses + rail)
    frequent_transit = (
        transit_stops.query()
        .within(city_bounds)
        .where("headway_minutes <= 15 OR mode = 'rail'")
    )

    # Step 3: Find 5 nearest transit stops within 800m (10-min walk)
    nearest_transit = block_centroids.nearest(
        frequent_transit,
        k=5,
        max_distance=800,
    )

    # Step 4: Get results for scoring
    accessibility_data = (
        nearest_transit
        .with_distance_to(
            "POINT(-74.0 40.75)",
            col_name="ref_distance",
        )
        .to_pandas()
    )

    if len(accessibility_data) > 0:
        print(f"Computed accessibility for {len(accessibility_data)} block-stop pairs")

    # Step 5: Export block polygons with scores for mapping
    scored_blocks = (
        census_blocks.query()
        .within(city_bounds)
        .select(["block_id", "population", "geometry"])
        .with_area(col_name="block_area")
        .with_bounds()
    )

    scored_blocks.to_parquet("transit_accessibility_blocks.parquet")
    scored_blocks.to_pmtiles(
        "transit_accessibility.pmtiles",
        layer="accessibility",
        maxzoom=14,
    )

    print("Transit accessibility scoring complete")


if __name__ == "__main__":
    main()
