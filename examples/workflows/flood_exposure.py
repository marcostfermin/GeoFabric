#!/usr/bin/env python3
"""
Flood Exposure Workflow

Features: sjoin + clip + with_area + where
Use case: Calculate building footprint area exposed to flood zones.
"""

import geofabric as gf


def main() -> None:
    # Load buildings and flood zones
    buildings = gf.open("file:///data/buildings.parquet")
    flood_zones = gf.open("file:///data/fema_flood_zones.parquet")

    # Coastal study area
    coastal = gf.roi.bbox(-74.05, 40.55, -73.85, 40.65)

    # Find buildings intersecting high-risk flood zones
    at_risk = (
        buildings.query()
        .within(coastal)
        .sjoin(
            flood_zones.query()
            .within(coastal)
            .where("zone IN ('AE', 'VE', 'A')"),  # High risk FEMA zones
            predicate="intersects",
            how="inner",
        )
        .with_area(col_name="total_footprint")
    )

    # Export at-risk buildings
    at_risk.to_parquet("buildings_flood_risk.parquet")
    at_risk.to_geojson("buildings_flood_risk.geojson")

    result = at_risk.to_pandas()
    print(f"Buildings in flood zones: {len(result)}")
    print(f"Total exposed footprint: {result['total_footprint'].sum():,.0f} sqm")


if __name__ == "__main__":
    main()
