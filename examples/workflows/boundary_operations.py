#!/usr/bin/env python3
"""
Boundary Operations Workflow

Features: clip + dissolve + boundary + export
Use case: Extract and dissolve neighborhoods within city boundary.
"""

import geofabric as gf


def main() -> None:
    # Load neighborhoods and city boundary
    neighborhoods = gf.open("file:///data/neighborhoods.parquet")
    city_boundary = gf.open("file:///data/city_boundary.parquet")

    # Get city boundary as WKT for clipping
    city_wkt = "POLYGON((-74.05 40.68, -73.90 40.68, -73.90 40.82, -74.05 40.82, -74.05 40.68))"

    # Clip neighborhoods to city boundary
    clipped = (
        neighborhoods.query()
        .clip(city_wkt)
        .with_area(col_name="clipped_area")
    )

    # Dissolve by borough to get borough boundaries
    boroughs = (
        neighborhoods.query()
        .clip(city_wkt)
        .dissolve(by="borough_name")
        .with_area(col_name="borough_area")
    )

    # Extract just the boundary lines
    borough_outlines = boroughs.boundary()

    # Export all layers
    clipped.to_geojson("neighborhoods_clipped.geojson")
    boroughs.to_geojson("boroughs_dissolved.geojson")
    borough_outlines.to_geojson("borough_outlines.geojson")

    print("Boundary operations complete")
    print(f"Neighborhoods: {clipped.to_pandas().shape[0]}")
    print(f"Boroughs: {boroughs.to_pandas().shape[0]}")


if __name__ == "__main__":
    main()
