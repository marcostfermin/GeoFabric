#!/usr/bin/env python3
"""
Download sample data from Overture Maps for integration testing.

This script downloads 10 sample buildings from NYC from the Overture Maps
public dataset and saves them in formats suitable for testing GeoFabric.

Output files:
    tests/data/overture_buildings_sample.geojson  (~12KB)
    tests/data/overture_buildings_sample.parquet  (~7KB)

Requirements:
    - duckdb with azure and spatial extensions
    - Internet connection

Usage:
    python tests/integration/download_overture_sample.py
"""

import json
import os
import sys


def main():
    try:
        import duckdb
    except ImportError:
        print("ERROR: duckdb is required. Install with: pip install duckdb")
        sys.exit(1)

    print("=" * 70)
    print("DOWNLOADING SAMPLE OVERTURE DATA")
    print("=" * 70)

    # Setup DuckDB with extensions
    conn = duckdb.connect()
    conn.execute("INSTALL azure;")
    conn.execute("LOAD azure;")
    conn.execute("INSTALL spatial;")
    conn.execute("LOAD spatial;")
    conn.execute("SET azure_account_name = 'overturemapswestus2';")

    # Find the latest release
    print("\nFinding available Overture releases...")
    try:
        files = conn.execute("""
            SELECT file_name
            FROM parquet_file_metadata('az://release/**/type=building/*.parquet')
            ORDER BY file_name DESC
            LIMIT 1
        """).fetchone()
        release = files[0].split("/")[2]  # Extract release from path
        print(f"Using release: {release}")
    except Exception as e:
        print(f"Could not detect release, using default: {e}")
        release = "2025-11-19.0"

    # Download sample buildings from NYC
    print(f"\nFetching 10 sample buildings from NYC (release {release})...")

    result = conn.execute(f"""
        SELECT
            id,
            ST_AsText(geometry) as wkt_geometry,
            ST_AsWKB(geometry) as geometry_wkb,
            subtype,
            class,
            height
        FROM 'az://release/{release}/theme=buildings/type=building/*.parquet'
        WHERE bbox.xmin > -74.01 AND bbox.xmax < -74.00
          AND bbox.ymin > 40.70 AND bbox.ymax < 40.71
        LIMIT 10
    """).fetchdf()

    print(f"Downloaded {len(result)} buildings")

    # Prepare output directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(os.path.dirname(script_dir), "data")
    os.makedirs(data_dir, exist_ok=True)

    # Save as GeoJSON
    features = []
    for _, row in result.iterrows():
        height = row["height"]
        if height and height == height:  # Check for NaN
            height = float(height)
        else:
            height = None

        geojson_geom = conn.execute(
            f"SELECT ST_AsGeoJSON(ST_GeomFromText('{row['wkt_geometry']}'))"
        ).fetchone()[0]

        features.append({
            "type": "Feature",
            "properties": {
                "id": row["id"],
                "subtype": row["subtype"],
                "class": row["class"],
                "height": height,
            },
            "geometry": json.loads(geojson_geom),
        })

    geojson = {"type": "FeatureCollection", "features": features}

    geojson_path = os.path.join(data_dir, "overture_buildings_sample.geojson")
    with open(geojson_path, "w") as f:
        json.dump(geojson, f, indent=2)
    print(f"\nSaved: {geojson_path} ({os.path.getsize(geojson_path)} bytes)")

    # Save as Parquet with WKB geometry
    parquet_df = result[["id", "subtype", "class", "height"]].copy()
    parquet_df["geometry"] = result["geometry_wkb"]

    parquet_path = os.path.join(data_dir, "overture_buildings_sample.parquet")
    parquet_df.to_parquet(parquet_path)
    print(f"Saved: {parquet_path} ({os.path.getsize(parquet_path)} bytes)")

    # Print sample info
    print("\n" + "=" * 70)
    print("SAMPLE DATA INFO")
    print("=" * 70)
    print(f"Release: {release}")
    print(f"Location: NYC (bbox: -74.01, 40.70, -74.00, 40.71)")
    print(f"Features: {len(result)} buildings")
    print(f"\nSample records:")
    print(result[["id", "subtype", "class", "height"]].head().to_string())

    print("\n" + "=" * 70)
    print("DONE! Sample data ready for integration testing.")
    print("=" * 70)


if __name__ == "__main__":
    main()
