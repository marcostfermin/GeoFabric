#!/usr/bin/env python3
"""
Overture Extract Workflow

Features: Overture download + within + simplify + select + PMTiles
Use case: Extract Overture buildings for a specific city and create web tiles.
"""

import geofabric as gf
from geofabric.sources.overture import Overture


def main() -> None:
    # Step 1: Download Overture buildings (run once)
    # ov = Overture(release="2025-12-17.0", theme="buildings", type_="building")
    # ov.download("./data/overture/buildings")

    # Step 2: Load downloaded Overture data
    buildings = gf.open("file:///data/overture/buildings")

    # Austin, TX bounding box
    austin = gf.roi.bbox(-97.85, 30.15, -97.65, 30.40)

    # Extract and process for web mapping
    austin_buildings = (
        buildings.query()
        .within(austin)
        .select(["id", "names", "height", "class", "geometry"])
        .simplify(tolerance=0.00001)  # Simplify for web
        .with_area(col_name="footprint_sqm")
        .limit(200000)
    )

    # Export to multiple formats
    austin_buildings.to_parquet("austin_buildings.parquet")

    # Create vector tiles for web map
    austin_buildings.to_pmtiles(
        "austin_buildings.pmtiles",
        layer="buildings",
        maxzoom=16,
    )

    result = austin_buildings.to_pandas()
    print(f"Extracted {len(result)} Overture buildings for Austin")
    print(f"Total footprint: {result['footprint_sqm'].sum():,.0f} sqm")


if __name__ == "__main__":
    main()
