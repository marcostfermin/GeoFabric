#!/usr/bin/env python3
"""
Parcel Subdivision Workflow

Features: explode + with_area + with_num_points + where
Use case: Split multi-polygons into individual parcels and filter by size.
"""

import geofabric as gf


def main() -> None:
    # Load parcels (may contain MultiPolygons)
    parcels = gf.open("file:///data/parcels.parquet")

    # Study area
    roi = gf.roi.bbox(-74.02, 40.70, -73.98, 40.75)

    # Check geometry types before
    before = (
        parcels.query()
        .within(roi)
        .with_geometry_type(col_name="geom_type")
        .to_pandas()
    )
    print("Before explode:")
    print(before["geom_type"].value_counts())

    # Explode multi-geometries into single geometries
    exploded = (
        parcels.query()
        .within(roi)
        .explode()  # Split MultiPolygon into Polygons
        .with_area(col_name="area_sqm")
        .with_num_points(col_name="vertices")
        .with_geometry_type(col_name="geom_type")
    )

    # Filter out tiny slivers (likely errors)
    valid_parcels = exploded.where("area_sqm > 10")  # At least 10 sqm

    # Export cleaned parcels
    valid_parcels.to_parquet("parcels_exploded.parquet")

    result = valid_parcels.to_pandas()
    print(f"\nAfter explode and filter:")
    print(f"  Total parcels: {len(result)}")
    print(result["geom_type"].value_counts())


if __name__ == "__main__":
    main()
