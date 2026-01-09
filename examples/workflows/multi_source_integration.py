#!/usr/bin/env python3
"""
Multi-Source Data Integration Workflow

Features: S3 + Azure + PostGIS + local file + transform + make_valid + select + sjoin + with_area + with_bounds + with_geometry_type
Use case: Combine data from multiple sources (S3, Azure, PostGIS, local files) into a unified dataset.

Authentication (see docs/API_REFERENCE.md for full details):
- S3: gf.configure_s3() or AWS environment variables
- Azure: gf.configure_azure() or Azure environment variables
- PostGIS: gf.configure_postgis() or connection string
- Local files: No authentication required
"""

import geofabric as gf


def main() -> None:
    """
    Integrate geospatial data from multiple sources.

    Steps:
    1. Configure credentials for all sources
    2. Load buildings from S3 (Overture data)
    3. Load infrastructure from Azure Blob Storage
    4. Load parcels from PostGIS database
    5. Load zoning from local GeoJSON
    6. Standardize schemas and CRS
    7. Perform spatial joins to enrich data
    8. Export unified dataset
    """
    # Step 1: Configure credentials for all sources
    # S3 credentials (programmatic configuration)
    gf.configure_s3(
        access_key_id="AKIAIOSFODNN7EXAMPLE",
        secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        region="us-east-1",
    )

    # Azure credentials
    gf.configure_azure(
        account_name="geodatastorageaccount",
        account_key="your-azure-account-key",
    )

    # PostGIS defaults (allows shorter connection strings)
    gf.configure_postgis(
        host="geodatabase.company.com",
        port=5432,
        user="user",
        password="pass",
        sslmode="require",
    )

    # Optional: Configure HTTP settings for any web requests
    gf.configure_http(timeout=60)

    # Step 2: Load from different sources
    # Cloud storage (S3) - uses configured credentials
    buildings = gf.open("s3://company-geodata/buildings.parquet?anonymous=false")

    # Azure Blob Storage - uses configured credentials
    infrastructure = gf.open("az://geodata/infrastructure.parquet")

    # Database (PostGIS) - uses configured defaults
    parcels = gf.open("postgresql:///gis?table=public.parcels")

    # Local file - no authentication needed
    zoning = gf.open("file:///data/zoning_districts.geojson")

    # Define integration area
    integration_area = gf.roi.bbox(-74.05, 40.70, -73.95, 40.80)

    # Step 2: Standardize CRS (all to WGS84)
    buildings_std = (
        buildings.query()
        .within(integration_area)
        .transform(to_srid=4326)
        .make_valid()
        .select(["id", "height", "class", "geometry"])
    )

    parcels_std = (
        parcels.query()
        .within(integration_area)
        .transform(to_srid=4326)
        .make_valid()
        .select(["parcel_id", "owner", "land_use", "geometry"])
    )

    zoning_std = (
        zoning.query()
        .within(integration_area)
        .transform(to_srid=4326)
        .select(["zone_id", "zone_code", "zone_name", "geometry"])
    )

    infrastructure_std = (
        infrastructure.query()
        .within(integration_area)
        .transform(to_srid=4326)
        .make_valid()
        .select(["infra_id", "type", "status", "geometry"])
    )

    # Step 3: Spatial join buildings to parcels
    buildings_with_parcels = buildings_std.sjoin(
        parcels_std,
        predicate="within",
        how="left",
    )

    # Step 4: Spatial join to add zoning information
    buildings_enriched = buildings_with_parcels.sjoin(
        zoning_std,
        predicate="intersects",
        how="left",
    )

    # Step 5: Add computed columns
    final_integrated = (
        buildings_enriched
        .with_area(col_name="building_area")
        .with_bounds()
        .with_geometry_type()
    )

    # Step 6: Export unified dataset
    final_integrated.to_parquet("integrated_buildings.parquet")
    final_integrated.to_geopackage("integrated_buildings.gpkg")

    # Export individual layers for reference
    buildings_std.to_parquet("buildings_standardized.parquet")
    parcels_std.to_parquet("parcels_standardized.parquet")
    zoning_std.to_parquet("zoning_standardized.parquet")
    infrastructure_std.to_parquet("infrastructure_standardized.parquet")

    print("Multi-source data integration complete")


if __name__ == "__main__":
    main()
