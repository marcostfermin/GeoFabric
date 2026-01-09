#!/usr/bin/env python3
"""
Ring Buffer Analysis Workflow

Features: sequential buffers + erase + with_area + sjoin
Use case: Analyze population distribution in distance rings from city center.
"""

import geofabric as gf


def main() -> None:
    # Load city center point and population grid
    city_center = gf.open("file:///data/city_center.parquet")
    population = gf.open("file:///data/population_grid.parquet")

    # Create concentric distance rings
    ring_1km = (
        city_center.query()
        .buffer(distance=1000, unit="meters")
    )

    ring_2km = (
        city_center.query()
        .buffer(distance=2000, unit="meters")
    )

    ring_5km = (
        city_center.query()
        .buffer(distance=5000, unit="meters")
    )

    ring_10km = (
        city_center.query()
        .buffer(distance=10000, unit="meters")
    )

    # Find population in each ring
    pop_0_1km = population.query().sjoin(ring_1km, predicate="within", how="inner")

    pop_1_2km = (
        population.query()
        .sjoin(ring_2km, predicate="within", how="inner")
        .sjoin(ring_1km, predicate="within", how="left")  # Exclude inner ring
    )

    pop_2_5km = (
        population.query()
        .sjoin(ring_5km, predicate="within", how="inner")
        .sjoin(ring_2km, predicate="within", how="left")
    )

    # Export rings for visualization
    ring_1km.to_geojson("ring_0_1km.geojson")
    ring_2km.to_geojson("ring_0_2km.geojson")
    ring_5km.to_geojson("ring_0_5km.geojson")
    ring_10km.to_geojson("ring_0_10km.geojson")

    # Get population counts
    count_0_1 = pop_0_1km.to_pandas().shape[0]
    count_1_2 = pop_1_2km.to_pandas().shape[0]

    print("Population Distribution by Distance Ring:")
    print(f"  0-1 km: {count_0_1} grid cells")
    print(f"  1-2 km: {count_1_2} grid cells")


if __name__ == "__main__":
    main()
