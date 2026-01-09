#!/usr/bin/env python3
"""
Spatial Enrichment Workflow

Features: sjoin + with_area + select + export
Use case: Enrich building footprints with parcel ownership information.
"""

import geofabric as gf


def main() -> None:
    # Load buildings and parcels
    buildings = gf.open("file:///data/buildings.parquet")
    parcels = gf.open("file:///data/parcels.parquet")

    # Study area
    roi = gf.roi.bbox(-74.02, 40.70, -73.98, 40.75)

    # Join buildings to parcels to get ownership info
    enriched = (
        buildings.query()
        .within(roi)
        .select(["building_id", "height", "year_built", "geometry"])
        .sjoin(
            parcels.query()
            .within(roi)
            .select(["parcel_id", "owner_name", "assessed_value", "geometry"]),
            predicate="within",
            how="left",
        )
        .with_area(col_name="footprint_sqm")
    )

    # Export enriched buildings
    enriched.to_parquet("buildings_with_ownership.parquet")

    result = enriched.to_pandas()
    print(f"Enriched {len(result)} buildings with parcel data")
    matched = result["parcel_id"].notna().sum()
    print(f"Buildings matched to parcels: {matched}")


if __name__ == "__main__":
    main()
