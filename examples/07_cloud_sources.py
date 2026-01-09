#!/usr/bin/env python3
"""
Cloud Data Sources Examples for GeoFabric

This script demonstrates reading from cloud sources:
- Amazon S3
- Google Cloud Storage (GCS)
- Azure Blob Storage
- PostGIS databases
- STAC catalogs

Includes both programmatic configuration and environment variable approaches.
"""

import geofabric as gf


# =============================================================================
# Configuration Methods
# =============================================================================


def configure_s3_programmatically() -> None:
    """Configure S3 credentials programmatically.

    This method is recommended for scripts, notebooks, and testing.
    Programmatic configuration takes precedence over environment variables.
    """
    # Option 1: Standard AWS credentials
    gf.configure_s3(
        access_key_id="AKIAIOSFODNN7EXAMPLE",
        secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        region="us-east-1",
    )

    # Option 2: Temporary credentials with session token
    gf.configure_s3(
        access_key_id="AKIAIOSFODNN7EXAMPLE",
        secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        session_token="FwoGZXIvYXdzEBYaDK...",
        region="us-east-1",
    )

    # Option 3: S3-compatible services (MinIO, DigitalOcean Spaces)
    gf.configure_s3(
        access_key_id="minioadmin",
        secret_access_key="minioadmin",
        endpoint="http://localhost:9000",
        use_ssl=False,
    )


def configure_gcs_programmatically() -> None:
    """Configure GCS credentials programmatically."""
    gf.configure_gcs(
        access_key_id="GOOGTS7C7FUP3AIRVJTE2BCD",
        secret_access_key="bGoa+V7g/yqDXvKRqq+JTFn4uQZbPiQJo4pf9RzJ",
        project="my-gcp-project",
    )


def configure_azure_programmatically() -> None:
    """Configure Azure Blob Storage credentials programmatically."""
    # Option 1: Account name and key
    gf.configure_azure(
        account_name="mystorageaccount",
        account_key="accountkey123...",
    )

    # Option 2: Connection string
    gf.configure_azure(
        connection_string="DefaultEndpointsProtocol=https;AccountName=...;AccountKey=..."
    )

    # Option 3: SAS token
    gf.configure_azure(
        account_name="mystorageaccount",
        sas_token="sv=2021-06-08&ss=b&srt=sco&sp=r...",
    )


def configure_postgis_programmatically() -> None:
    """Configure PostGIS defaults programmatically.

    Set defaults that apply when connection URI doesn't specify them.
    """
    gf.configure_postgis(
        host="db.example.com",
        port=5432,
        user="myuser",
        password="mypassword",
        sslmode="require",
    )

    # Now shorter URIs work:
    # gf.open("postgresql:///mydb?table=public.buildings")


def configure_stac_programmatically() -> None:
    """Configure STAC catalog authentication."""
    # Option 1: API key
    gf.configure_stac(api_key="my-stac-api-key")

    # Option 2: Bearer token
    gf.configure_stac(
        headers={"Authorization": "Bearer eyJ..."}
    )

    # Option 3: Multiple custom headers
    gf.configure_stac(
        api_key="my-api-key",
        headers={"X-Custom-Header": "value"},
        default_catalog="https://planetarycomputer.microsoft.com/api/stac/v1",
    )


def configure_http_globally() -> None:
    """Configure global HTTP settings."""
    gf.configure_http(
        proxy="http://corporate-proxy:8080",
        timeout=60,
        headers={"User-Agent": "MyApp/1.0"},
        verify_ssl=True,
    )


def reset_all_configuration() -> None:
    """Reset all configuration to defaults (use env vars)."""
    gf.reset_config()


# =============================================================================
# Amazon S3
# =============================================================================


def read_from_s3_public() -> None:
    """Read from a public S3 bucket."""
    # Public buckets don't require credentials
    ds = gf.open("s3://my-public-bucket/data/buildings.parquet")

    # Query as usual
    sample = ds.sample(100)
    print(f"Read {len(sample)} rows from S3")


def read_from_s3_private() -> None:
    """Read from a private S3 bucket with programmatic credentials."""
    # Configure credentials first
    gf.configure_s3(
        access_key_id="AKIAIOSFODNN7EXAMPLE",
        secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        region="us-east-1",
    )

    # Use anonymous=false for private buckets
    ds = gf.open("s3://my-private-bucket/data/buildings.parquet?anonymous=false")

    roi = gf.roi.bbox(-74.10, 40.60, -73.70, 40.90)
    result = ds.within(roi).limit(1000).to_pandas()

    print(f"Read {len(result)} rows from private S3 bucket")


def query_s3_with_filters() -> None:
    """Query S3 data with spatial and attribute filters."""
    ds = gf.open("s3://my-bucket/geodata/parcels.parquet")

    roi = gf.roi.bbox(-122.5, 37.7, -122.3, 37.9)  # San Francisco area

    result = (
        ds.within(roi)
        .where("land_use = 'residential'")
        .select(["parcel_id", "land_use", "area_sqft", "geometry"])
        .with_area(col_name="computed_area")
        .limit(5000)
        .to_pandas()
    )

    print(f"Found {len(result)} residential parcels in SF")


# =============================================================================
# Google Cloud Storage
# =============================================================================


def read_from_gcs_public() -> None:
    """Read from a public GCS bucket."""
    ds = gf.open("gs://my-public-bucket/data/roads.parquet")

    sample = ds.sample(100)
    print(f"Read {len(sample)} rows from GCS")


def read_from_gcs_private() -> None:
    """Read from a private GCS bucket with programmatic credentials."""
    # Configure GCS credentials
    gf.configure_gcs(
        access_key_id="GOOGTS7C7FUP3AIRVJTE2BCD",
        secret_access_key="your-secret-key",
    )

    ds = gf.open("gs://my-private-bucket/data/buildings.parquet")

    result = ds.head(20)
    print(f"Read {len(result)} rows from private GCS bucket")


def query_gcs_with_transformations() -> None:
    """Query GCS data with spatial transformations."""
    ds = gf.open("gs://geodata-bucket/california/buildings.parquet")

    roi = gf.roi.bbox(-118.5, 33.9, -118.1, 34.1)  # Los Angeles area

    result = (
        ds.within(roi)
        .transform(to_srid=3857)  # Convert to Web Mercator
        .buffer(distance=50, unit="meters")
        .with_area(col_name="buffered_area")
        .limit(1000)
        .to_pandas()
    )

    print(f"Processed {len(result)} buildings from GCS")


# =============================================================================
# PostGIS
# =============================================================================


def read_from_postgis() -> None:
    """Read from a PostGIS database using full connection string."""
    # Connection string format:
    # postgresql://user:password@host:port/database?table=schema.tablename

    ds = gf.open(
        "postgresql://myuser:mypassword@localhost:5432/geodatabase?table=public.buildings"
    )

    sample = ds.sample(100)
    print(f"Read {len(sample)} rows from PostGIS")


def read_from_postgis_with_config() -> None:
    """Read from PostGIS using programmatic defaults."""
    # Configure defaults once
    gf.configure_postgis(
        host="db.example.com",
        port=5432,
        user="myuser",
        password="mypassword",
        sslmode="require",
    )

    # Now use shorter connection strings
    ds = gf.open("postgresql:///geodatabase?table=public.buildings")

    sample = ds.sample(100)
    print(f"Read {len(sample)} rows from PostGIS")


def query_postgis_with_filters() -> None:
    """Query PostGIS with spatial and attribute filters."""
    gf.configure_postgis(
        host="db.example.com",
        user="myuser",
        password="mypassword",
    )

    ds = gf.open("postgresql:///geodata?table=parcels")

    roi = gf.roi.bbox(-74.10, 40.60, -73.70, 40.90)

    result = (
        ds.within(roi)
        .where("zone_code IN ('R1', 'R2', 'R3')")
        .select(["id", "zone_code", "area_sqft", "geometry"])
        .limit(5000)
        .to_pandas()
    )

    print(f"Found {len(result)} residential parcels")


def postgis_spatial_join() -> None:
    """Perform spatial join between PostGIS tables."""
    gf.configure_postgis(host="localhost", user="user", password="pass")

    buildings = gf.open("postgresql:///db?table=buildings")
    parcels = gf.open("postgresql:///db?table=parcels")

    # Spatial join
    joined = buildings.query().sjoin(
        parcels.query(),
        predicate="within",
        how="inner",
    )

    result = joined.limit(1000).to_pandas()
    print(f"Joined {len(result)} building-parcel pairs")


def postgis_to_local_file() -> None:
    """Extract data from PostGIS to local file."""
    gf.configure_postgis(host="localhost", user="user", password="pass")

    ds = gf.open("postgresql:///geodata?table=buildings")

    roi = gf.roi.bbox(-74.10, 40.60, -73.70, 40.90)

    # Extract and save locally
    query = ds.within(roi).where("year_built >= 2020")

    query.to_parquet("extracted_buildings.parquet")
    query.to_geojson("extracted_buildings.geojson")

    print("Extracted PostGIS data to local files")


# =============================================================================
# Azure Blob Storage
# =============================================================================


def read_from_azure_public() -> None:
    """Read from a public Azure Blob Storage container."""
    ds = gf.open("az://public-container/data/buildings.parquet")

    sample = ds.sample(100)
    print(f"Read {len(sample)} rows from Azure")


def read_from_azure_private() -> None:
    """Read from a private Azure Blob Storage container."""
    # Configure Azure credentials
    gf.configure_azure(
        account_name="mystorageaccount",
        account_key="your-account-key",
    )

    ds = gf.open("az://private-container/data/buildings.parquet")

    sample = ds.head(20)
    print(f"Read {len(sample)} rows from private Azure container")


def read_from_azure_with_sas() -> None:
    """Read from Azure using a SAS token."""
    gf.configure_azure(
        account_name="mystorageaccount",
        sas_token="sv=2021-06-08&ss=b&srt=sco&sp=r...",
    )

    ds = gf.open("az://container/data.parquet")
    sample = ds.head(10)
    print(f"Read {len(sample)} rows using SAS token")


def query_azure_with_filters() -> None:
    """Query Azure data with spatial and attribute filters."""
    gf.configure_azure(
        account_name="mystorageaccount",
        account_key="your-account-key",
    )

    ds = gf.open("az://geodata/parcels.parquet")

    roi = gf.roi.bbox(-122.5, 37.7, -122.3, 37.9)

    result = (
        ds.within(roi)
        .where("land_use = 'residential'")
        .select(["parcel_id", "land_use", "area_sqft", "geometry"])
        .limit(5000)
        .to_pandas()
    )

    print(f"Found {len(result)} residential parcels from Azure")


# =============================================================================
# STAC Catalogs
# =============================================================================


def read_from_stac() -> None:
    """Read from a STAC catalog.

    Requires stac extras: pip install geofabric[stac]
    """
    # STAC URI format: stac://catalog-url/collection
    ds = gf.open("stac://https://planetarycomputer.microsoft.com/api/stac/v1/collections/io-lulc")

    sample = ds.sample(100)
    print(f"Read {len(sample)} items from STAC catalog")


def read_from_authenticated_stac() -> None:
    """Read from an authenticated STAC catalog."""
    # Configure STAC authentication
    gf.configure_stac(
        api_key="my-api-key",
        headers={"X-Custom-Header": "value"},
    )

    ds = gf.open("stac://https://private-catalog.example.com/api/stac/v1/collections/my-collection")

    sample = ds.sample(100)
    print(f"Read {len(sample)} items from authenticated STAC catalog")


def query_stac_with_bbox() -> None:
    """Query STAC catalog with bounding box."""
    ds = gf.open("stac://https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a")

    roi = gf.roi.bbox(-122.5, 37.7, -122.3, 37.9)

    result = ds.within(roi).limit(100).to_pandas()
    print(f"Found {len(result)} STAC items")


# =============================================================================
# Cross-Cloud Workflows
# =============================================================================


def s3_to_gcs_migration() -> None:
    """Read from S3, process, and write to GCS."""
    # Configure S3
    gf.configure_s3(
        access_key_id="AWS_KEY",
        secret_access_key="AWS_SECRET",
        region="us-east-1",
    )

    # Read from S3
    ds = gf.open("s3://source-bucket/data/buildings.parquet?anonymous=false")

    roi = gf.roi.bbox(-74.10, 40.60, -73.70, 40.90)

    # Process
    query = (
        ds.within(roi)
        .where("type = 'commercial'")
        .with_area(col_name="area_sqm")
        .limit(10000)
    )

    # Write to GCS (requires write permissions)
    # Note: Direct cloud-to-cloud writes may require intermediate local file
    result = query.to_pandas()
    print(f"Processed {len(result)} rows for migration")

    # Save locally first, then upload
    query.to_parquet("temp_migration.parquet")
    print("Saved to local file for GCS upload")


def combine_multiple_sources() -> None:
    """Combine data from multiple cloud sources."""
    # Configure all credentials
    gf.configure_s3(
        access_key_id="AWS_KEY",
        secret_access_key="AWS_SECRET",
    )
    gf.configure_postgis(
        host="db.example.com",
        user="user",
        password="pass",
    )

    # Buildings from S3
    buildings = gf.open("s3://data-bucket/buildings.parquet?anonymous=false")

    # Parcels from PostGIS
    parcels = gf.open("postgresql:///db?table=parcels")

    roi = gf.roi.bbox(-74.10, 40.60, -73.70, 40.90)

    # Spatial join across sources
    joined = (
        buildings.query()
        .within(roi)
        .sjoin(
            parcels.query().within(roi),
            predicate="intersects",
            how="inner",
        )
        .limit(5000)
    )

    result = joined.to_pandas()
    print(f"Combined {len(result)} records from S3 and PostGIS")


def cloud_data_validation() -> None:
    """Validate cloud data before processing."""
    gf.configure_s3(
        access_key_id="AWS_KEY",
        secret_access_key="AWS_SECRET",
    )

    ds = gf.open("s3://my-bucket/data/buildings.parquet?anonymous=false")

    # Quick validation
    validation = ds.validate()

    print("Cloud Data Validation:")
    print(f"  Total rows: {validation.total_rows}")
    print(f"  Valid: {validation.valid_count}")
    print(f"  Invalid: {validation.invalid_count}")
    print(f"  NULL: {validation.null_count}")

    # Get statistics
    stats = ds.stats()
    print(f"\n  Geometry type: {stats.geometry_type}")
    print(f"  Bounds: {stats.bounds}")


def main() -> None:
    """Run all examples."""
    print("=" * 60)
    print("GeoFabric Cloud Data Sources Examples")
    print("=" * 60)

    print("\n=== CREDENTIAL CONFIGURATION ===")
    print("")
    print("Method 1: Programmatic (recommended for scripts)")
    print("  gf.configure_s3(access_key_id='...', secret_access_key='...')")
    print("  gf.configure_gcs(access_key_id='...', secret_access_key='...')")
    print("  gf.configure_azure(account_name='...', account_key='...')")
    print("  gf.configure_postgis(host='...', user='...', password='...')")
    print("  gf.configure_stac(api_key='...', headers={...})")
    print("  gf.configure_http(proxy='...', timeout=60)")
    print("")
    print("Method 2: Environment Variables (recommended for production)")
    print("  export AWS_ACCESS_KEY_ID='...'")
    print("  export AWS_SECRET_ACCESS_KEY='...'")
    print("  export GOOGLE_APPLICATION_CREDENTIALS='...'")
    print("")
    print("Credential Precedence: Programmatic > Env Vars > Files > IAM Roles")

    print("\n=== SUPPORTED URI FORMATS ===")
    print("")
    print("S3:")
    print("  s3://bucket-name/path/to/file.parquet")
    print("  s3://bucket-name/path/to/file.parquet?anonymous=false")
    print("")
    print("GCS:")
    print("  gs://bucket-name/path/to/file.parquet")
    print("")
    print("Azure:")
    print("  az://container/path/to/file.parquet")
    print("")
    print("PostGIS:")
    print("  postgresql://user:pass@host:port/database?table=schema.tablename")
    print("  postgresql:///database?table=tablename  (with config defaults)")
    print("")
    print("STAC:")
    print("  stac://catalog-url/collection")
    print("  Requires: pip install geofabric[stac]")

    print("\nUncomment function calls to run with real data.")


if __name__ == "__main__":
    main()
