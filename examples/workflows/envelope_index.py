#!/usr/bin/env python3
"""
Envelope Index Workflow

Features: envelope + with_bounds + with_area + to_csv
Use case: Create bounding box index for large dataset cataloging.
"""

import geofabric as gf


def main() -> None:
    # Load complex geometries
    parcels = gf.open("file:///data/parcels.parquet")

    # Create envelope (bounding box) index
    envelope_index = (
        parcels.query()
        .select(["parcel_id", "owner", "geometry"])
        .envelope()  # Convert to bounding rectangles
        .with_bounds()  # Extract min/max coordinates
        .with_area(col_name="bbox_area")
    )

    # Export as CSV catalog (no geometry needed)
    envelope_index.to_csv("parcel_bbox_index.csv")

    # Also export envelopes for visualization
    envelope_index.to_geojson("parcel_envelopes.geojson")

    result = envelope_index.to_pandas()
    print(f"Created bounding box index for {len(result)} parcels")
    print(f"Columns: {list(result.columns)}")


if __name__ == "__main__":
    main()
