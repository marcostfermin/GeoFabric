#!/usr/bin/env python3
"""
Web Mapping Pipeline Workflow

Features: transform + simplify + select + to_pmtiles
Use case: Prepare building footprints for a web map application.
"""

import geofabric as gf


def main() -> None:
    # Load buildings
    buildings = gf.open("file:///data/buildings.parquet")

    # City bounds
    roi = gf.roi.bbox(-74.05, 40.68, -73.90, 40.82)

    # Prepare for web mapping:
    # - Transform to Web Mercator (what web maps use)
    # - Simplify geometry for faster rendering
    # - Select only needed attributes
    web_ready = (
        buildings.query()
        .within(roi)
        .transform(to_srid=3857)  # Web Mercator
        .simplify(tolerance=1)  # ~1 meter tolerance
        .select(["id", "name", "type", "height", "geometry"])
        .limit(100000)
    )

    # Export to PMTiles for Mapbox/MapLibre
    web_ready.to_pmtiles(
        "buildings.pmtiles",
        layer="buildings",
        maxzoom=16,
    )

    # Also export GeoJSON for debugging
    web_ready.limit(1000).to_geojson("buildings_sample.geojson")

    print("Web mapping tiles generated: buildings.pmtiles")


if __name__ == "__main__":
    main()
