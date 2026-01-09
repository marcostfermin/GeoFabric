#!/usr/bin/env python3
"""
Validation and Statistics Examples for GeoFabric

This script demonstrates data quality tools:
- Geometry validation
- Dataset statistics
- Data profiling
- Quality checks
"""

import geofabric as gf


def validate_dataset() -> None:
    """Validate geometries in a dataset."""
    ds = gf.open("file:///data/buildings.parquet")

    # Run validation
    validation_result = ds.validate()

    print("Validation Results:")
    print(f"  Total rows: {validation_result.total_rows}")
    print(f"  Valid geometries: {validation_result.valid_count}")
    print(f"  Invalid geometries: {validation_result.invalid_count}")
    print(f"  NULL geometries: {validation_result.null_count}")

    # Check for issues
    if validation_result.issues:
        print(f"\nIssues found ({len(validation_result.issues)}):")
        for issue in validation_result.issues[:10]:  # Show first 10
            print(f"  Row {issue.row_id}: {issue.reason}")


def get_dataset_statistics() -> None:
    """Get comprehensive dataset statistics."""
    ds = gf.open("file:///data/buildings.parquet")

    # Compute statistics
    stats = ds.stats()

    print("Dataset Statistics:")
    print(f"  Row count: {stats.row_count}")
    print(f"  Column count: {stats.column_count}")
    print(f"  Columns: {stats.columns}")
    print(f"  Data types: {stats.dtypes}")
    print(f"  Geometry type: {stats.geometry_type}")
    print(f"  CRS: {stats.crs}")

    if stats.bounds:
        print(f"  Bounds: {stats.bounds}")

    if stats.null_counts:
        print(f"  NULL counts: {stats.null_counts}")


def quick_data_preview() -> None:
    """Get quick previews of data."""
    ds = gf.open("file:///data/buildings.parquet")

    # Get first N rows
    head = ds.head(10)
    print(f"First 10 rows:\n{head}")

    # Get random sample
    sample = ds.sample(20)
    print(f"\nRandom sample of 20 rows:\n{sample}")

    # Count total rows
    count = ds.count()
    print(f"\nTotal rows: {count}")


def describe_query_results() -> None:
    """Get statistics on query results."""
    ds = gf.open("file:///data/buildings.parquet")
    roi = gf.roi.bbox(-74.10, 40.60, -73.70, 40.90)

    query = ds.within(roi).limit(1000)

    # Describe provides summary statistics
    description = query.describe()
    print(f"Query description:\n{description}")


def explain_query_plan() -> None:
    """View the query execution plan."""
    ds = gf.open("file:///data/buildings.parquet")
    roi = gf.roi.bbox(-74.10, 40.60, -73.70, 40.90)

    query = (
        ds.within(roi)
        .where("type = 'commercial'")
        .select(["id", "name", "geometry"])
        .limit(100)
    )

    # Explain shows the execution plan
    plan = query.explain()
    print(f"Query plan:\n{plan}")


def check_data_quality() -> None:
    """Perform data quality checks."""
    ds = gf.open("file:///data/buildings.parquet")

    # Check for invalid geometries
    validation = ds.validate()

    quality_report = {
        "total_rows": validation.total_rows,
        "valid_percentage": (
            validation.valid_count / validation.total_rows * 100
            if validation.total_rows > 0
            else 0
        ),
        "null_percentage": (
            validation.null_count / validation.total_rows * 100
            if validation.total_rows > 0
            else 0
        ),
        "issues_count": len(validation.issues) if validation.issues else 0,
    }

    print("Data Quality Report:")
    print(f"  Total rows: {quality_report['total_rows']}")
    print(f"  Valid geometries: {quality_report['valid_percentage']:.1f}%")
    print(f"  NULL geometries: {quality_report['null_percentage']:.1f}%")
    print(f"  Issues found: {quality_report['issues_count']}")


def repair_and_validate() -> None:
    """Repair invalid geometries and re-validate."""
    ds = gf.open("file:///data/buildings.parquet")
    roi = gf.roi.bbox(-74.10, 40.60, -73.70, 40.90)

    # Add validity check column
    query = ds.within(roi).with_is_valid(col_name="is_valid")

    # Check validity before repair
    before = query.to_pandas()
    invalid_before = len(before[~before["is_valid"]])
    print(f"Invalid geometries before repair: {invalid_before}")

    # Repair invalid geometries
    repaired = ds.within(roi).make_valid().with_is_valid(col_name="is_valid")

    # Check validity after repair
    after = repaired.to_pandas()
    invalid_after = len(after[~after["is_valid"]])
    print(f"Invalid geometries after repair: {invalid_after}")


def analyze_geometry_types() -> None:
    """Analyze geometry types in dataset."""
    ds = gf.open("file:///data/mixed_geometries.parquet")

    # Add geometry type column
    query = ds.query().with_geometry_type(col_name="geom_type")

    result = query.to_pandas()

    # Count by geometry type
    type_counts = result["geom_type"].value_counts()

    print("Geometry Types:")
    for geom_type, count in type_counts.items():
        print(f"  {geom_type}: {count}")


def analyze_spatial_distribution() -> None:
    """Analyze spatial distribution of data."""
    ds = gf.open("file:///data/buildings.parquet")

    # Add bounds columns
    query = ds.query().with_bounds().limit(10000)

    result = query.to_pandas()

    print("Spatial Distribution:")
    print(f"  Min X: {result['minx'].min():.6f}")
    print(f"  Max X: {result['maxx'].max():.6f}")
    print(f"  Min Y: {result['miny'].min():.6f}")
    print(f"  Max Y: {result['maxy'].max():.6f}")


def profile_attribute_values() -> None:
    """Profile attribute values in dataset."""
    ds = gf.open("file:///data/buildings.parquet")

    # Get sample for profiling
    sample = ds.sample(1000)

    # Analyze specific columns
    if "type" in sample.columns:
        type_counts = sample["type"].value_counts()
        print("Building Types:")
        for btype, count in type_counts.head(10).items():
            print(f"  {btype}: {count}")

    if "height" in sample.columns:
        print(f"\nHeight Statistics:")
        print(f"  Min: {sample['height'].min()}")
        print(f"  Max: {sample['height'].max()}")
        print(f"  Mean: {sample['height'].mean():.2f}")
        print(f"  Median: {sample['height'].median():.2f}")


def compare_datasets() -> None:
    """Compare two datasets."""
    ds1 = gf.open("file:///data/buildings_old.parquet")
    ds2 = gf.open("file:///data/buildings_new.parquet")

    # Get counts
    count1 = ds1.count()
    count2 = ds2.count()

    # Get statistics
    stats1 = ds1.stats()
    stats2 = ds2.stats()

    print("Dataset Comparison:")
    print(f"  Old dataset: {count1} rows")
    print(f"  New dataset: {count2} rows")
    print(f"  Difference: {count2 - count1} rows")

    # Compare bounds
    if stats1.bounds and stats2.bounds:
        print(f"\n  Old bounds: {stats1.bounds}")
        print(f"  New bounds: {stats2.bounds}")


def main() -> None:
    """Run all examples."""
    print("=" * 60)
    print("GeoFabric Validation and Statistics Examples")
    print("=" * 60)

    print("\nValidation Methods:")
    print("- ds.validate()    - Validate all geometries")
    print("- ds.stats()       - Get dataset statistics")
    print("- ds.head(n)       - Preview first n rows")
    print("- ds.sample(n)     - Random sample of n rows")
    print("- ds.count()       - Count total rows")
    print("")
    print("Query Methods:")
    print("- query.describe() - Get result statistics")
    print("- query.explain()  - View query plan")
    print("")
    print("Computed Columns for Validation:")
    print("- with_is_valid()      - Add validity check column")
    print("- with_geometry_type() - Add geometry type column")
    print("- with_num_points()    - Add vertex count column")

    print("\nUncomment function calls to run with real data.")


if __name__ == "__main__":
    main()
