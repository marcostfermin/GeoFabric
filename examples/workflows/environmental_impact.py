#!/usr/bin/env python3
"""
Environmental Impact Assessment Workflow

Features: transform + buffer + make_valid + sjoin + clip + with_area + with_is_valid
Use case: Identify developments that may impact protected waterways and wetlands.
"""

import geofabric as gf


def main() -> None:
    """
    Assess potential environmental impacts of development proposals.

    Steps:
    1. Load development proposals and environmental features
    2. Create regulatory buffer zones around waterways
    3. Identify developments that intersect buffer zones
    4. Compute affected areas and distances
    5. Validate geometry quality
    6. Generate compliance report data
    """
    # Load datasets
    developments = gf.open("file:///data/proposed_developments.parquet")
    waterways = gf.open("file:///data/waterways.parquet")
    wetlands = gf.open("file:///data/wetlands.parquet")

    county_boundary = gf.roi.wkt(
        "POLYGON((-74.3 40.5, -73.7 40.5, -73.7 41.0, -74.3 41.0, -74.3 40.5))",
        srid=4326,
    )

    # Step 1: Create 100-foot riparian buffer zones (regulatory requirement)
    # Convert to projected CRS for accurate distance buffering
    waterway_buffers = (
        waterways.query()
        .within(county_boundary)
        .transform(to_srid=32618)  # UTM Zone 18N for accurate meters
        .buffer(distance=30.48, unit="meters")  # 100 feet
        .transform(to_srid=4326)  # Back to WGS84
        .make_valid()  # Ensure valid after transformations
    )

    # Step 2: Combine with wetland buffers (50-foot buffer)
    wetland_buffers = (
        wetlands.query()
        .within(county_boundary)
        .transform(to_srid=32618)
        .buffer(distance=15.24, unit="meters")  # 50 feet
        .transform(to_srid=4326)
        .make_valid()
    )

    # Step 3: Find developments intersecting waterway buffers
    waterway_impacts = (
        developments.query()
        .within(county_boundary)
        .sjoin(
            waterway_buffers,
            predicate="intersects",
            how="inner",
        )
        .with_area(col_name="development_area")
    )

    # Step 4: Find developments intersecting wetland buffers
    wetland_impacts = (
        developments.query()
        .within(county_boundary)
        .sjoin(
            wetland_buffers,
            predicate="intersects",
            how="inner",
        )
        .with_area(col_name="development_area")
    )

    # Step 5: Clip developments to buffer zones to find actual impact area
    waterway_overlaps = (
        developments.query()
        .within(county_boundary)
        .clip(waterway_buffers.sql())
        .with_area(col_name="impacted_area")
        .with_is_valid(col_name="geometry_valid")
    )

    # Step 6: Export for environmental review
    waterway_impacts.to_parquet("waterway_impact_developments.parquet")
    wetland_impacts.to_parquet("wetland_impact_developments.parquet")
    waterway_impacts.to_geojson("environmental_impacts.geojson")

    # Export buffer zones for reference
    waterway_buffers.to_geojson("waterway_buffer_zones.geojson")
    wetland_buffers.to_geojson("wetland_buffer_zones.geojson")

    print("Environmental impact assessment complete")


if __name__ == "__main__":
    main()
