#!/usr/bin/env python3
"""
Coordinate Flip Workflow

Features: flip_coordinates + with_bounds + with_is_valid
Use case: Fix data where lat/lon are swapped (common import error).
"""

import geofabric as gf


def main() -> None:
    # Load data with potentially swapped coordinates
    data = gf.open("file:///data/imported_points.parquet")

    # Check bounds before flip
    before = data.query().with_bounds().limit(100).to_pandas()
    print("Before flip:")
    print(f"  X range: {before['minx'].min():.4f} to {before['maxx'].max():.4f}")
    print(f"  Y range: {before['miny'].min():.4f} to {before['maxy'].max():.4f}")

    # If Y looks like longitude (e.g., -74) and X like latitude (e.g., 40),
    # coordinates are swapped
    needs_flip = before["miny"].min() < -70  # Longitude-like values in Y

    if needs_flip:
        print("\nCoordinates appear swapped, applying flip...")
        fixed = (
            data.query()
            .flip_coordinates()  # Swap X and Y
            .with_bounds()
            .with_is_valid(col_name="is_valid")
        )

        # Verify after flip
        after = fixed.limit(100).to_pandas()
        print("\nAfter flip:")
        print(f"  X range: {after['minx'].min():.4f} to {after['maxx'].max():.4f}")
        print(f"  Y range: {after['miny'].min():.4f} to {after['maxy'].max():.4f}")

        # Export fixed data
        fixed.to_parquet("points_fixed.parquet")
        print("\nFixed data exported")
    else:
        print("\nCoordinates appear correct, no flip needed")


if __name__ == "__main__":
    main()
