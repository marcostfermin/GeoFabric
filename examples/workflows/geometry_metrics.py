#!/usr/bin/env python3
"""
Geometry Metrics Workflow

Features: with_area + with_length + with_perimeter + with_num_points + with_geometry_type
Use case: Add comprehensive geometry measurements to parcels for analysis.
"""

import geofabric as gf


def main() -> None:
    # Load parcels
    parcels = gf.open("file:///data/parcels.parquet")

    # Study area
    roi = gf.roi.bbox(-74.02, 40.70, -73.98, 40.75)

    # Add all geometry metrics
    parcels_with_metrics = (
        parcels.query()
        .within(roi)
        .select(["parcel_id", "owner", "land_use", "geometry"])
        .with_area(col_name="area_sqm")
        .with_perimeter(col_name="perimeter_m")
        .with_num_points(col_name="vertex_count")
        .with_geometry_type(col_name="geom_type")
        .with_is_valid(col_name="is_valid")
        .with_bounds()
    )

    # Export enriched parcels
    parcels_with_metrics.to_parquet("parcels_with_metrics.parquet")

    # Analyze metrics
    result = parcels_with_metrics.to_pandas()
    print(f"Processed {len(result)} parcels")
    print(f"\nArea statistics:")
    print(f"  Min: {result['area_sqm'].min():.2f} sqm")
    print(f"  Max: {result['area_sqm'].max():.2f} sqm")
    print(f"  Mean: {result['area_sqm'].mean():.2f} sqm")
    print(f"\nGeometry complexity (vertices):")
    print(f"  Min: {result['vertex_count'].min()}")
    print(f"  Max: {result['vertex_count'].max()}")
    print(f"  Mean: {result['vertex_count'].mean():.1f}")


if __name__ == "__main__":
    main()
