#!/usr/bin/env python3
"""
Real Estate Proximity Analysis Workflow

Features: buffer + sjoin (multiple) + with_area + centroid + coordinates + PMTiles
Use case: Find residential properties within walking distance of transit and parks.
"""

import geofabric as gf


def main() -> None:
    """
    Analyze residential properties based on proximity to amenities.

    Steps:
    1. Load property parcels, transit stops, and parks
    2. Filter to residential properties in target area
    3. Find properties within 400m of transit (5-min walk)
    4. Identify properties near parks
    5. Compute property metrics (area, centroid)
    6. Export results for web mapping
    """
    # Load datasets
    parcels = gf.open("file:///data/parcels.parquet")
    transit = gf.open("file:///data/transit_stops.parquet")
    parks = gf.open("file:///data/parks.parquet")

    # Define study area (downtown)
    study_area = gf.roi.bbox(-74.02, 40.70, -73.98, 40.75)

    # Step 1: Filter residential parcels in study area
    residential = (
        parcels.query()
        .within(study_area)
        .where("land_use IN ('R1', 'R2', 'R3', 'residential')")
    )

    # Step 2: Find parcels within 400m of transit (walkable)
    transit_walksheds = (
        transit.query()
        .within(study_area)
        .buffer(distance=400, unit="meters")
    )

    transit_accessible = residential.sjoin(
        transit_walksheds,
        predicate="intersects",
        how="inner",
    )

    # Step 3: Also check proximity to parks (300m)
    park_buffers = (
        parks.query()
        .within(study_area)
        .buffer(distance=300, unit="meters")
    )

    # Find parcels near both transit AND parks
    premium_locations = transit_accessible.sjoin(
        park_buffers,
        predicate="intersects",
        how="inner",
    )

    # Step 4: Add computed metrics
    analysis_result = (
        premium_locations
        .with_area(col_name="parcel_area_sqm")
        .with_bounds()
        .with_geometry_type()
        .limit(5000)
    )

    # Step 5: Export for different uses
    # Full data for GIS analysis
    analysis_result.to_parquet("premium_parcels_analysis.parquet")

    # Centroids for web mapping (lighter weight)
    centroids = (
        premium_locations
        .centroid()
        .with_coordinates(x_col="longitude", y_col="latitude")
        .with_area(col_name="parcel_area")
        .limit(5000)
    )
    centroids.to_geojson("premium_parcels_points.geojson")

    # Vector tiles for interactive web map
    analysis_result.to_pmtiles(
        "premium_parcels.pmtiles",
        layer="parcels",
        maxzoom=16,
    )

    print("Real estate proximity analysis complete")
    print("Outputs: premium_parcels_analysis.parquet, .geojson, .pmtiles")


if __name__ == "__main__":
    main()
