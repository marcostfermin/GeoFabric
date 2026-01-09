#!/usr/bin/env python3
"""
Attribute Summary Workflow

Features: where + with_area + describe + aggregate
Use case: Summarize commercial buildings by type and size.
"""

import geofabric as gf


def main() -> None:
    # Load buildings
    buildings = gf.open("file:///data/buildings.parquet")

    # Study area
    roi = gf.roi.bbox(-74.02, 40.70, -73.98, 40.75)

    # Filter to commercial and add area
    commercial = (
        buildings.query()
        .within(roi)
        .where("type IN ('office', 'retail', 'industrial', 'warehouse')")
        .with_area(col_name="footprint_sqm")
        .with_num_points(col_name="complexity")
    )

    # Get summary statistics
    stats = commercial.describe()
    print("Commercial Building Statistics:")
    print(stats)

    # Export filtered data
    commercial.to_parquet("commercial_buildings.parquet")

    # Get counts by type
    result = commercial.to_pandas()
    print(f"\nTotal commercial buildings: {len(result)}")
    if "type" in result.columns:
        print("\nBy type:")
        print(result["type"].value_counts())


if __name__ == "__main__":
    main()
