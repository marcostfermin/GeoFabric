#!/usr/bin/env python3
"""
Buffer and Measure Workflow

Features: buffer + with_area + with_perimeter + export
Use case: Create safety zones around industrial facilities and measure their extent.
"""

import geofabric as gf


def main() -> None:
    # Load industrial facilities
    facilities = gf.open("file:///data/industrial_facilities.parquet")

    # Define study area
    county = gf.roi.bbox(-74.2, 40.5, -73.8, 40.9)

    # Create 500m buffer zones and measure them
    safety_zones = (
        facilities.query()
        .within(county)
        .where("hazard_class IN ('high', 'medium')")
        .buffer(distance=500, unit="meters")
        .with_area(column_name="zone_area_sqm")
        .with_perimeter(column_name="zone_perimeter_m")
    )

    # Export for regulatory review
    safety_zones.to_parquet("safety_zones.parquet")
    safety_zones.to_geojson("safety_zones.geojson")

    # Print summary
    result = safety_zones.to_pandas()
    print(f"Created {len(result)} safety zones")
    print(f"Total protected area: {result['zone_area_sqm'].sum():,.0f} sqm")


if __name__ == "__main__":
    main()
