#!/usr/bin/env python3
"""
Data Cleaning Workflow

Features: validate + make_valid + with_is_valid + where + export
Use case: Clean and repair geometries before loading into production database.
"""

import geofabric as gf


def main() -> None:
    # Load raw data with potential geometry issues
    raw_parcels = gf.open("file:///data/raw_parcels.parquet")

    # Step 1: Check initial data quality
    validation = raw_parcels.validate()
    print("Before cleaning:")
    print(f"  Total: {validation.total_rows}")
    print(f"  Valid: {validation.valid_count}")
    print(f"  Invalid: {validation.invalid_count}")
    print(f"  NULL: {validation.null_count}")

    # Step 2: Repair and filter
    cleaned = (
        raw_parcels.query()
        .make_valid()  # Repair invalid geometries
        .with_is_valid(col_name="is_valid")
        .with_area(col_name="area")
        .where("geometry IS NOT NULL")  # Remove NULLs
        .where("area > 0.0000001")  # Remove degenerate polygons
    )

    # Step 3: Export cleaned data
    cleaned.to_parquet("parcels_cleaned.parquet")

    # Verify results
    result = cleaned.to_pandas()
    valid_count = result["is_valid"].sum()
    print(f"\nAfter cleaning:")
    print(f"  Total: {len(result)}")
    print(f"  Valid: {valid_count}")


if __name__ == "__main__":
    main()
