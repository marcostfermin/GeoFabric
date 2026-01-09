#!/usr/bin/env python3
"""
PostGIS Sync Workflow

Features: PostGIS source + transform + make_valid + to_parquet
Use case: Extract and cache PostGIS data locally for faster analysis.

Authentication Options:
1. Programmatic: gf.configure_postgis(host="...", user="...", password="...")
2. Full connection string: postgresql://user:pass@host:port/database
3. Environment: PGUSER, PGPASSWORD, PGHOST, PGPORT, PGDATABASE
"""

import geofabric as gf


def main() -> None:
    # Option 1: Configure PostGIS defaults programmatically
    # This allows using shorter connection strings
    gf.configure_postgis(
        host="localhost",
        port=5432,
        user="user",
        password="password",
        sslmode="prefer",
    )

    # With defaults configured, you can use shorter connection strings
    # The configured values are used when not specified in the URI
    buildings = gf.open("postgresql:///geodatabase?table=public.buildings")

    # Or use full connection string (overrides configured defaults)
    # buildings = gf.open(
    #     "postgresql://user:password@localhost:5432/geodatabase?table=public.buildings"
    # )

    # Define extraction area
    roi = gf.roi.bbox(-74.02, 40.70, -73.98, 40.75)

    # Extract, clean, and standardize
    local_copy = (
        buildings.query()
        .within(roi)
        .select(["id", "address", "type", "height", "year_built", "geometry"])
        .transform(to_srid=4326)  # Ensure WGS84
        .make_valid()
        .with_area(col_name="footprint_sqm")
        .with_is_valid(col_name="is_valid")
    )

    # Cache locally as Parquet (much faster for repeated queries)
    local_copy.to_parquet("buildings_cache.parquet")

    # Also create GeoPackage for GIS software
    local_copy.to_geopackage("buildings_cache.gpkg")

    result = local_copy.to_pandas()
    print(f"Synced {len(result)} buildings from PostGIS")
    print(f"All valid: {result['is_valid'].all()}")


if __name__ == "__main__":
    main()
