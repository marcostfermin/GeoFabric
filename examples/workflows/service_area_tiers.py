#!/usr/bin/env python3
"""
Service Area Tiers Workflow

Features: multiple buffers + sjoin + with_area + aggregate
Use case: Analyze customer distribution across delivery service tiers.
"""

import geofabric as gf


def main() -> None:
    # Load warehouse and customers
    warehouse = gf.open("file:///data/warehouse.parquet")
    customers = gf.open("file:///data/customers.parquet")

    # Create service area tiers (same-day, next-day, standard)
    same_day = (
        warehouse.query()
        .buffer(distance=10000, unit="meters")  # 10km
        .with_area(col_name="tier_area")
    )

    next_day = (
        warehouse.query()
        .buffer(distance=50000, unit="meters")  # 50km
        .with_area(col_name="tier_area")
    )

    standard = (
        warehouse.query()
        .buffer(distance=150000, unit="meters")  # 150km
        .with_area(col_name="tier_area")
    )

    # Count customers in each tier
    same_day_customers = customers.query().sjoin(
        same_day, predicate="within", how="inner"
    )

    next_day_customers = customers.query().sjoin(
        next_day, predicate="within", how="inner"
    )

    # Export service zones
    same_day.to_geojson("service_tier_same_day.geojson")
    next_day.to_geojson("service_tier_next_day.geojson")
    standard.to_geojson("service_tier_standard.geojson")

    # Count results
    tier1_count = same_day_customers.to_pandas().shape[0]
    tier2_count = next_day_customers.to_pandas().shape[0]

    print("Service Area Analysis:")
    print(f"  Same-day (10km): {tier1_count} customers")
    print(f"  Next-day (50km): {tier2_count} customers")


if __name__ == "__main__":
    main()
