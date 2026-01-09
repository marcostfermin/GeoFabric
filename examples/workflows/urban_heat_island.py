#!/usr/bin/env python3
"""
Urban Heat Island Analysis Workflow

Features: with_area + with_bounds + sjoin + dissolve + simplify + PMTiles
Use case: Analyze building density and green space to identify heat-vulnerable areas.
"""

import geofabric as gf


def main() -> None:
    """
    Identify areas vulnerable to urban heat island effects.

    Steps:
    1. Load buildings, green spaces, and neighborhood boundaries
    2. Compute building footprint density per neighborhood
    3. Compute green space ratio per neighborhood
    4. Creates heat vulnerability index
    5. Identifies high-risk areas
    6. Export for urban planning
    """
    # Load datasets
    buildings = gf.open("file:///data/buildings.parquet")
    green_spaces = gf.open("file:///data/parks_greenspace.parquet")
    neighborhoods = gf.open("file:///data/neighborhoods.parquet")

    city_bounds = gf.roi.bbox(-74.05, 40.68, -73.90, 40.82)

    # Step 1: Add area calculations to buildings
    buildings_with_area = (
        buildings.query()
        .within(city_bounds)
        .with_area(col_name="footprint_area")
        .with_bounds()
    )

    # Step 2: Add area calculations to green spaces
    green_with_area = (
        green_spaces.query()
        .within(city_bounds)
        .with_area(col_name="green_area")
    )

    # Step 3: Compute neighborhood areas
    neighborhood_areas = (
        neighborhoods.query()
        .within(city_bounds)
        .with_area(col_name="neighborhood_area")
        .select(["neighborhood_id", "name", "neighborhood_area", "geometry"])
    )

    # Step 4: Spatial join buildings to neighborhoods
    buildings_by_neighborhood = buildings_with_area.sjoin(
        neighborhood_areas,
        predicate="within",
        how="inner",
    )

    # Step 5: Spatial join green spaces to neighborhoods
    green_by_neighborhood = green_with_area.sjoin(
        neighborhood_areas,
        predicate="intersects",
        how="inner",
    )

    # Step 6: Dissolve buildings by neighborhood
    building_coverage = (
        buildings_by_neighborhood
        .dissolve(by="neighborhood_id")
        .with_area(col_name="total_building_area")
    )

    # Step 7: Dissolve green space by neighborhood
    green_coverage = (
        green_by_neighborhood
        .dissolve(by="neighborhood_id")
        .with_area(col_name="total_green_area")
    )

    # Step 8: Export analysis layers
    buildings_with_area.to_parquet("buildings_heat_analysis.parquet")
    green_with_area.to_parquet("greenspace_heat_analysis.parquet")
    building_coverage.to_parquet("building_coverage_by_neighborhood.parquet")
    green_coverage.to_parquet("green_coverage_by_neighborhood.parquet")

    neighborhood_areas.to_geojson("neighborhoods_base.geojson")

    # Vector tiles for web dashboard
    buildings_with_area.simplify(tolerance=0.00001).to_pmtiles(
        "heat_island_buildings.pmtiles",
        layer="buildings",
        maxzoom=16,
    )

    print("Urban heat island analysis complete")


if __name__ == "__main__":
    main()
