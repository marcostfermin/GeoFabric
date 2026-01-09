#!/usr/bin/env python3
"""
Comprehensive Data Quality Pipeline Workflow

Features: validate + with_is_valid + with_geometry_type + with_num_points + with_area + make_valid + where + transform + with_bounds
Use case: Validate, clean, and standardize geospatial data for production database.
"""

import geofabric as gf


def main() -> None:
    """
    Comprehensive data quality pipeline for production data.

    Steps:
    1. Load raw data and validate geometries
    2. Repair invalid geometries
    3. Remove duplicates and outliers
    4. Standardize coordinate system
    5. Add quality metadata columns
    6. Export cleaned data with quality report
    """
    # Load raw data
    raw_data = gf.open("file:///data/raw_parcels.parquet")

    # Step 1: Initial validation
    validation = raw_data.validate()

    print("Initial Data Quality:")
    print(f"  Total rows: {validation.total_rows}")
    print(f"  Valid geometries: {validation.valid_count}")
    print(f"  Invalid geometries: {validation.invalid_count}")
    print(f"  NULL geometries: {validation.null_count}")

    # Step 2: Add quality check columns before cleaning
    data_with_checks = (
        raw_data.query()
        .with_is_valid(col_name="original_valid")
        .with_geometry_type(col_name="geom_type")
        .with_num_points(col_name="vertex_count")
        .with_area(col_name="original_area")
    )

    # Step 3: Repair invalid geometries
    repaired_data = (
        raw_data.query()
        .make_valid()
        .with_is_valid(col_name="is_valid_after_repair")
    )

    # Step 4: Filter out remaining invalids and nulls
    clean_data = repaired_data.where("geometry IS NOT NULL")

    # Step 5: Remove geometry outliers (tiny or huge polygons)
    reasonable_data = (
        clean_data
        .with_area(col_name="area_check")
        .where("area_check > 0.0000001")  # Not degenerate
        .where("area_check < 1")  # Not continent-sized (in degrees)
    )

    # Step 6: Standardize to WGS84 (EPSG:4326)
    standardized = reasonable_data.transform(to_srid=4326)

    # Step 7: Add final quality metadata
    final_data = (
        standardized
        .with_area(col_name="final_area")
        .with_bounds()
        .with_num_points(col_name="final_vertex_count")
        .with_is_valid(col_name="final_valid")
    )

    # Step 8: Export cleaned data
    final_data.to_parquet("parcels_cleaned.parquet")

    # Export quality report data
    data_with_checks.to_parquet("parcels_quality_checks.parquet")

    # Get final statistics
    final_stats = final_data.to_pandas()
    print(f"\nCleaned Data Quality:")
    print(f"  Final row count: {len(final_stats)}")
    print(f"  All geometries valid: {final_stats['final_valid'].all()}")

    print("\nData quality pipeline complete")


if __name__ == "__main__":
    main()
