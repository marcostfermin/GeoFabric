#!/usr/bin/env python3
"""
Point Extraction Workflow

Features: centroid + with_coordinates + with_bounds + to_csv
Use case: Create a point dataset from building polygons for geocoding reference.
"""

import geofabric as gf


def main() -> None:
    # Load building footprints
    buildings = gf.open("file:///data/buildings.parquet")

    # Study area
    roi = gf.roi.bbox(-74.02, 40.70, -73.98, 40.75)

    # Extract centroids with coordinates and original bounds
    building_points = (
        buildings.query()
        .within(roi)
        .select(["building_id", "address", "type", "geometry"])
        .centroid()  # Convert polygons to points
        .with_coordinates(x_col="longitude", y_col="latitude")
        .with_bounds(prefix="orig_")  # Original polygon bounds
    )

    # Export as CSV for geocoding database
    building_points.to_csv("building_centroids.csv")

    # Export as GeoJSON for mapping
    building_points.to_geojson("building_centroids.geojson")

    result = building_points.to_pandas()
    print(f"Extracted {len(result)} building centroids")
    print(f"Columns: {list(result.columns)}")


if __name__ == "__main__":
    main()
