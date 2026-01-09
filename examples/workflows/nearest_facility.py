#!/usr/bin/env python3
"""
Nearest Facility Workflow

Features: nearest + with_distance_to + with_coordinates + to_csv
Use case: Find the closest hospital to each residential address.
"""

import geofabric as gf


def main() -> None:
    # Load addresses and hospitals
    addresses = gf.open("file:///data/residential_addresses.parquet")
    hospitals = gf.open("file:///data/hospitals.parquet")

    # City bounds
    roi = gf.roi.bbox(-74.05, 40.68, -73.90, 40.82)

    # Find nearest hospital for each address
    nearest = (
        addresses.query()
        .within(roi)
        .nearest(
            hospitals.query().within(roi).where("has_emergency = true"),
            k=1,  # Just the closest one
            max_distance=10000,  # Within 10km
        )
        .with_coordinates(x_col="address_lon", y_col="address_lat")
    )

    # Export to CSV for analysis (non-spatial)
    nearest.to_csv("addresses_nearest_hospital.csv")

    # Also export spatial for mapping
    nearest.to_geojson("addresses_nearest_hospital.geojson")

    result = nearest.to_pandas()
    print(f"Matched {len(result)} addresses to nearest hospital")


if __name__ == "__main__":
    main()
