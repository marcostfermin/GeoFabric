#!/usr/bin/env python3
"""
Cloud to Local Workflow

Features: S3 source + within + where + multiple export formats
Use case: Extract a regional subset from cloud storage for local analysis.

Authentication Options:
1. Programmatic: gf.configure_s3(access_key_id="...", secret_access_key="...")
2. Environment: AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY
3. AWS CLI configuration (~/.aws/credentials)
4. IAM role (when running on AWS infrastructure)
"""

import geofabric as gf


def main() -> None:
    # Option 1: Configure S3 credentials programmatically (recommended for scripts)
    # gf.configure_s3(
    #     access_key_id="AKIAIOSFODNN7EXAMPLE",
    #     secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    #     region="us-east-1",
    # )

    # Option 2: For S3-compatible services (MinIO, DigitalOcean Spaces)
    # gf.configure_s3(
    #     access_key_id="minioadmin",
    #     secret_access_key="minioadmin",
    #     endpoint="http://localhost:9000",
    #     use_ssl=False,
    # )

    # Load from S3 (public or authenticated)
    # Use ?anonymous=false for private buckets with configured credentials
    buildings = gf.open("s3://geodata-bucket/buildings/national.parquet")

    # Define region to extract (Denver metro area)
    denver_metro = gf.roi.bbox(-105.1, 39.6, -104.7, 39.9)

    # Extract subset with filters
    denver_buildings = (
        buildings.query()
        .within(denver_metro)
        .where("year_built >= 2010")
        .select(["id", "address", "type", "year_built", "sqft", "geometry"])
        .with_area(col_name="footprint_area")
        .with_bounds()
    )

    # Export to multiple local formats
    denver_buildings.to_parquet("denver_buildings.parquet")
    denver_buildings.to_geopackage("denver_buildings.gpkg")
    denver_buildings.to_geojson("denver_buildings.geojson")

    result = denver_buildings.to_pandas()
    print(f"Extracted {len(result)} buildings from cloud to local")
    print(f"Date range: {result['year_built'].min()} - {result['year_built'].max()}")


if __name__ == "__main__":
    main()
