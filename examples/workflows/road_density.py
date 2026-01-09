#!/usr/bin/env python3
"""
Road Density Workflow

Features: with_length + sjoin + dissolve + with_area
Use case: Calculate road density per census tract.
"""

import geofabric as gf


def main() -> None:
    # Load roads and census tracts
    roads = gf.open("file:///data/roads.parquet")
    tracts = gf.open("file:///data/census_tracts.parquet")

    # Study area
    roi = gf.roi.bbox(-74.05, 40.68, -73.90, 40.82)

    # Add length to roads
    roads_with_length = (
        roads.query()
        .within(roi)
        .where("road_class IN ('primary', 'secondary', 'tertiary', 'residential')")
        .with_length(col_name="road_length_m")
    )

    # Join roads to tracts
    roads_by_tract = roads_with_length.sjoin(
        tracts.query().within(roi).select(["tract_id", "geometry"]),
        predicate="intersects",
        how="inner",
    )

    # Get tract areas
    tract_areas = (
        tracts.query()
        .within(roi)
        .select(["tract_id", "geometry"])
        .with_area(col_name="tract_area_sqm")
    )

    # Export for density calculation
    roads_by_tract.to_parquet("roads_by_tract.parquet")
    tract_areas.to_parquet("tract_areas.parquet")

    print("Road density data exported")
    print("Calculate density = sum(road_length_m) / tract_area_sqm")


if __name__ == "__main__":
    main()
