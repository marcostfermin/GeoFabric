#!/usr/bin/env python3
"""
Join and Filter Workflow

Features: sjoin + where + select + limit
Use case: Find schools within residential zones.
"""

import geofabric as gf


def main() -> None:
    # Load schools and zoning
    schools = gf.open("file:///data/schools.parquet")
    zoning = gf.open("file:///data/zoning.parquet")

    # Study area
    roi = gf.roi.bbox(-74.05, 40.68, -73.90, 40.82)

    # Find schools that are within residential zones
    schools_in_residential = (
        schools.query()
        .within(roi)
        .where("school_type IN ('elementary', 'middle', 'high')")
        .select(["school_id", "name", "school_type", "enrollment", "geometry"])
        .sjoin(
            zoning.query()
            .within(roi)
            .where("zone_type LIKE 'R%'"),  # Residential zones
            predicate="within",
            how="inner",
        )
    )

    # Export results
    schools_in_residential.to_geojson("schools_in_residential_zones.geojson")
    schools_in_residential.to_parquet("schools_in_residential_zones.parquet")

    result = schools_in_residential.to_pandas()
    print(f"Found {len(result)} schools in residential zones")


if __name__ == "__main__":
    main()
