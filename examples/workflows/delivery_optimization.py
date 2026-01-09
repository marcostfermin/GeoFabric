#!/usr/bin/env python3
"""
Delivery Zone Optimization Workflow

Features: buffer (multiple) + with_area + nearest + with_coordinates + sjoin + with_length
Use case: Create optimized delivery zones based on warehouse locations and customer density.
"""

import geofabric as gf


def main() -> None:
    """
    Create and analyze delivery zones for logistics optimization.

    Steps:
    1. Load customer locations, road network, warehouse locations
    2. Create service area buffers around warehouses
    3. Assign customers to nearest warehouse
    4. Compute zone statistics (customer count, total distance)
    5. Identify underserved areas
    6. Export zones for route planning
    """
    # Load datasets
    customers = gf.open("file:///data/customer_locations.parquet")
    warehouses = gf.open("file:///data/warehouse_locations.parquet")
    roads = gf.open("file:///data/road_network.parquet")

    service_region = gf.roi.bbox(-74.20, 40.55, -73.70, 40.95)

    # Step 1: Create service area buffers (5km, 10km, 15km)
    warehouse_5km = (
        warehouses.query()
        .within(service_region)
        .buffer(distance=5000, unit="meters")
        .with_area(col_name="zone_area")
    )

    warehouse_10km = (
        warehouses.query()
        .within(service_region)
        .buffer(distance=10000, unit="meters")
    )

    warehouse_15km = (
        warehouses.query()
        .within(service_region)
        .buffer(distance=15000, unit="meters")
    )

    # Step 2: Assign customers to nearest warehouse
    customer_assignments = (
        customers.query()
        .within(service_region)
        .nearest(
            warehouses.query().within(service_region),
            k=1,
        )
        .with_coordinates(x_col="cust_lon", y_col="cust_lat")
    )

    # Step 3: Identify customers in each service tier
    tier1_customers = (
        customers.query()
        .within(service_region)
        .sjoin(warehouse_5km, predicate="within", how="inner")
    )

    tier2_customers = (
        customers.query()
        .within(service_region)
        .sjoin(warehouse_10km, predicate="within", how="inner")
    )

    # Step 4: Find underserved customers (outside 15km)
    underserved = (
        customers.query()
        .within(service_region)
        .sjoin(warehouse_15km, predicate="intersects", how="left")
    )

    # Step 5: Compute road density in service zones
    road_segments = (
        roads.query()
        .within(service_region)
        .where("road_class IN ('primary', 'secondary', 'tertiary')")
        .with_length(col_name="segment_length")
    )

    # Step 6: Export delivery zones
    warehouse_5km.to_geojson("delivery_zones_5km.geojson")
    warehouse_10km.to_geojson("delivery_zones_10km.geojson")
    warehouse_15km.to_geojson("delivery_zones_15km.geojson")

    customer_assignments.to_parquet("customer_warehouse_assignments.parquet")
    customer_assignments.to_csv("customer_assignments.csv")

    print("Delivery zone optimization complete")


if __name__ == "__main__":
    main()
