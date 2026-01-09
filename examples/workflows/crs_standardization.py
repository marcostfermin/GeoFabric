#!/usr/bin/env python3
"""
CRS Standardization Workflow

Features: transform + make_valid + with_bounds + with_is_valid
Use case: Standardize data from different sources to a common CRS.
"""

import geofabric as gf


def main() -> None:
    # Load data that might be in different CRS
    # (state plane, UTM, or other local projections)
    parcels = gf.open("file:///data/county_parcels.parquet")

    # Standardize to WGS84 (EPSG:4326)
    standardized = (
        parcels.query()
        .transform(to_srid=4326)  # Reproject to WGS84
        .make_valid()  # Fix any issues from reprojection
        .with_is_valid(col_name="is_valid")
        .with_bounds()  # Add bounds in new CRS
        .with_area(col_name="area_degrees")  # Area in new units
    )

    # Verify all geometries are valid after transform
    result = standardized.to_pandas()
    invalid_count = (~result["is_valid"]).sum()

    if invalid_count > 0:
        print(f"Warning: {invalid_count} geometries invalid after transform")
    else:
        print("All geometries valid after CRS transformation")

    # Export standardized data
    standardized.to_parquet("parcels_wgs84.parquet")
    standardized.to_geojson("parcels_wgs84.geojson")

    print(f"Standardized {len(result)} parcels to WGS84")
    print(f"Bounds: ({result['minx'].min():.4f}, {result['miny'].min():.4f}) to "
          f"({result['maxx'].max():.4f}, {result['maxy'].max():.4f})")


if __name__ == "__main__":
    main()
