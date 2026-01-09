#!/usr/bin/env python3
"""
Viewshed Preparation Workflow

Features: point_on_surface + with_coordinates + select + to_csv
Use case: Prepare building points for viewshed analysis in external tool.
"""

import geofabric as gf


def main() -> None:
    # Load buildings
    buildings = gf.open("file:///data/buildings.parquet")

    # Study area
    roi = gf.roi.bbox(-74.02, 40.70, -73.98, 40.75)

    # Get points on surface (guaranteed inside polygon, unlike centroid)
    viewpoints = (
        buildings.query()
        .within(roi)
        .where("height IS NOT NULL AND height > 0")
        .select(["building_id", "name", "height", "geometry"])
        .point_on_surface()  # Point guaranteed to be inside building
        .with_coordinates(x_col="x", y_col="y")
    )

    # Export as CSV for viewshed tool (needs x, y, height)
    viewpoints.to_csv("viewshed_input.csv")

    # Also export as points for verification
    viewpoints.to_geojson("viewshed_points.geojson")

    result = viewpoints.to_pandas()
    print(f"Prepared {len(result)} viewpoints")
    print(f"Height range: {result['height'].min():.1f}m - {result['height'].max():.1f}m")


if __name__ == "__main__":
    main()
