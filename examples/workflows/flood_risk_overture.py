#!/usr/bin/env python3
"""
Flood Risk Assessment with Overture Data Workflow

Features: make_valid + with_area + with_bounds + with_is_valid + where + sjoin + clip + simplify + PMTiles
Use case: Assess building flood exposure using Overture Maps data and FEMA flood zones.
"""

import geofabric as gf
# from geofabric.sources.overture import Overture


def main() -> None:
    """
    Assess flood risk using Overture Maps building data.

    Steps:
    1. Download/load Overture buildings
    2. Load FEMA flood zones
    3. Identify buildings in flood zones
    4. Compute exposure metrics (area, value estimates)
    5. Aggregate by flood zone type
    6. Export risk assessment data
    """
    # Step 1: Load Overture buildings (download first if needed)
    # ov = Overture(release="2025-12-17.0", theme="buildings", type_="building")
    # ov.download("./data/overture/buildings")

    buildings = gf.open("file:///data/overture/buildings")
    flood_zones = gf.open("file:///data/fema_flood_zones.parquet")

    # Coastal area study region
    coastal_region = gf.roi.bbox(-74.05, 40.55, -73.85, 40.65)

    # Step 2: Validate and prepare building data
    buildings_clean = (
        buildings.query()
        .within(coastal_region)
        .make_valid()
        .with_area(col_name="footprint_sqm")
        .with_bounds()
        .with_is_valid(col_name="geom_valid")
    )

    # Step 3: Filter flood zones by risk level
    high_risk_zones = (
        flood_zones.query()
        .within(coastal_region)
        .where("zone_type IN ('AE', 'VE', 'A')")
    )

    moderate_risk_zones = (
        flood_zones.query()
        .within(coastal_region)
        .where("zone_type IN ('X500', 'B')")
    )

    # Step 4: Identify buildings in high-risk zones
    high_risk_buildings = buildings_clean.sjoin(
        high_risk_zones,
        predicate="intersects",
        how="inner",
    )

    # Step 5: Identify buildings in moderate-risk zones
    moderate_risk_buildings = buildings_clean.sjoin(
        moderate_risk_zones,
        predicate="intersects",
        how="inner",
    )

    # Step 6: Clip buildings to flood zones for actual exposure area
    exposed_footprints = (
        buildings_clean
        .clip(high_risk_zones.sql())
        .with_area(col_name="exposed_area_sqm")
    )

    # Step 7: Compute statistics
    high_risk_result = high_risk_buildings.to_pandas()
    moderate_risk_result = moderate_risk_buildings.to_pandas()

    print(f"Buildings in high-risk flood zones: {len(high_risk_result)}")
    print(f"Buildings in moderate-risk flood zones: {len(moderate_risk_result)}")

    if len(high_risk_result) > 0:
        total_exposure = high_risk_result["footprint_sqm"].sum()
        print(f"Total high-risk building footprint: {total_exposure:,.0f} sqm")

    # Step 8: Export risk assessment
    high_risk_buildings.to_parquet("flood_high_risk_buildings.parquet")
    high_risk_buildings.to_geojson("flood_high_risk_buildings.geojson")
    moderate_risk_buildings.to_parquet("flood_moderate_risk_buildings.parquet")
    exposed_footprints.to_parquet("flood_exposed_footprints.parquet")

    high_risk_zones.to_geojson("flood_zones_high_risk.geojson")
    moderate_risk_zones.to_geojson("flood_zones_moderate_risk.geojson")

    high_risk_buildings.simplify(tolerance=0.00001).to_pmtiles(
        "flood_risk_buildings.pmtiles",
        layer="flood_risk",
        maxzoom=16,
    )

    print("Flood risk assessment complete")


if __name__ == "__main__":
    main()
