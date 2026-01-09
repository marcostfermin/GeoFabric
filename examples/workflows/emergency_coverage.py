#!/usr/bin/env python3
"""
Emergency Response Coverage Analysis Workflow

Features: buffer (multiple) + where + sjoin + with_area + make_valid + collect + PMTiles
Use case: Analyze fire station and hospital coverage to identify gaps in response times.
"""

import geofabric as gf


def main() -> None:
    """
    Analyze emergency service coverage and identify gaps.

    Steps:
    1. Load fire stations, hospitals, and population data
    2. Create response time zones (2, 5, 10 minute drive times)
    3. Identify population in each response zone
    4. Find underserved areas
    5. Suggest optimal locations for new stations
    6. Export coverage maps
    """
    # Load datasets
    fire_stations = gf.open("file:///data/fire_stations.parquet")
    hospitals = gf.open("file:///data/hospitals.parquet")
    population = gf.open("file:///data/population_grid.parquet")

    county_bounds = gf.roi.bbox(-74.15, 40.60, -73.85, 40.90)

    # Step 1: Create fire station response zones
    # Approximate: 2-min = 1.5km, 5-min = 4km, 10-min = 8km at 45km/h avg
    fire_2min = (
        fire_stations.query()
        .within(county_bounds)
        .buffer(distance=1500, unit="meters")
    )

    fire_5min = (
        fire_stations.query()
        .within(county_bounds)
        .buffer(distance=4000, unit="meters")
    )

    fire_10min = (
        fire_stations.query()
        .within(county_bounds)
        .buffer(distance=8000, unit="meters")
    )

    # Step 2: Create hospital response zones (ambulance)
    hospital_5min = (
        hospitals.query()
        .within(county_bounds)
        .where("has_emergency = true")
        .buffer(distance=3000, unit="meters")
    )

    hospital_10min = (
        hospitals.query()
        .within(county_bounds)
        .where("has_emergency = true")
        .buffer(distance=6000, unit="meters")
    )

    hospital_15min = (
        hospitals.query()
        .within(county_bounds)
        .where("has_emergency = true")
        .buffer(distance=10000, unit="meters")
    )

    # Step 3: Identify population in fire response zones
    pop_fire_2min = (
        population.query()
        .within(county_bounds)
        .sjoin(fire_2min, predicate="intersects", how="inner")
        .with_area(col_name="grid_area")
    )

    pop_fire_5min = (
        population.query()
        .within(county_bounds)
        .sjoin(fire_5min, predicate="intersects", how="inner")
    )

    # Step 4: All population for gap analysis
    all_population = (
        population.query()
        .within(county_bounds)
        .select(["grid_id", "population", "geometry"])
        .with_area(col_name="grid_area")
    )

    # Step 5: Validate and clean response zones
    fire_zones_valid = (
        fire_10min
        .make_valid()
        .with_is_valid(col_name="is_valid")
        .with_area(col_name="zone_area")
    )

    # Step 6: Dissolve overlapping zones for clean coverage
    fire_coverage_dissolved = fire_10min.collect()
    hospital_coverage_dissolved = hospital_15min.collect()

    # Step 7: Export all layers
    fire_2min.to_geojson("fire_response_2min.geojson")
    fire_5min.to_geojson("fire_response_5min.geojson")
    fire_10min.to_geojson("fire_response_10min.geojson")

    hospital_5min.to_geojson("hospital_response_5min.geojson")
    hospital_10min.to_geojson("hospital_response_10min.geojson")
    hospital_15min.to_geojson("hospital_response_15min.geojson")

    pop_fire_2min.to_parquet("population_fire_2min.parquet")
    all_population.to_parquet("population_grid_analysis.parquet")

    fire_stations.query().within(county_bounds).to_geojson("fire_stations.geojson")
    hospitals.query().within(county_bounds).to_geojson("hospitals.geojson")

    fire_zones_valid.to_pmtiles(
        "emergency_coverage.pmtiles",
        layer="fire_zones",
        maxzoom=14,
    )

    print("Emergency response coverage analysis complete")


if __name__ == "__main__":
    main()
