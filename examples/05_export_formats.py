#!/usr/bin/env python3
"""
Export Formats Examples for GeoFabric

This script demonstrates exporting data to various formats:
- Parquet (GeoParquet)
- GeoJSON
- GeoPackage
- FlatGeoBuf
- CSV (with WKT geometry)
- PMTiles (vector tiles)
- Arrow Table
- Pandas/GeoPandas DataFrames
"""

import geofabric as gf


def export_to_parquet() -> None:
    """Export to Parquet format (recommended for large datasets)."""
    ds = gf.open("file:///data/buildings.parquet")
    roi = gf.roi.bbox(-74.10, 40.60, -73.70, 40.90)

    query = ds.within(roi).limit(10000)

    # Export to Parquet
    query.to_parquet("output/buildings_subset.parquet")

    print("Exported to Parquet format")


def export_to_geojson() -> None:
    """Export to GeoJSON format."""
    ds = gf.open("file:///data/buildings.parquet")
    roi = gf.roi.bbox(-74.10, 40.60, -73.70, 40.90)

    query = ds.within(roi).limit(1000)

    # Export to GeoJSON
    query.to_geojson("output/buildings_subset.geojson")

    # GeoJSON is human-readable but larger than binary formats
    print("Exported to GeoJSON format")


def export_to_geopackage() -> None:
    """Export to GeoPackage format."""
    ds = gf.open("file:///data/buildings.parquet")
    roi = gf.roi.bbox(-74.10, 40.60, -73.70, 40.90)

    query = ds.within(roi).limit(5000)

    # Export to GeoPackage (SQLite-based, compatible with QGIS, ArcGIS)
    query.to_geopackage("output/buildings_subset.gpkg")

    print("Exported to GeoPackage format")


def export_to_flatgeobuf() -> None:
    """Export to FlatGeoBuf format."""
    ds = gf.open("file:///data/buildings.parquet")
    roi = gf.roi.bbox(-74.10, 40.60, -73.70, 40.90)

    query = ds.within(roi).limit(5000)

    # FlatGeoBuf is optimized for streaming and cloud access
    query.to_flatgeobuf("output/buildings_subset.fgb")

    print("Exported to FlatGeoBuf format")


def export_to_csv() -> None:
    """Export to CSV with WKT geometry."""
    ds = gf.open("file:///data/buildings.parquet")
    roi = gf.roi.bbox(-74.10, 40.60, -73.70, 40.90)

    query = ds.within(roi).limit(1000)

    # CSV exports geometry as WKT string
    query.to_csv("output/buildings_subset.csv")

    print("Exported to CSV format (geometry as WKT)")


def export_to_pmtiles() -> None:
    """Export to PMTiles vector tiles (requires tippecanoe)."""
    ds = gf.open("file:///data/buildings.parquet")
    roi = gf.roi.bbox(-74.10, 40.60, -73.70, 40.90)

    query = ds.within(roi).limit(50000)

    # PMTiles requires tippecanoe to be installed
    # Install: brew install tippecanoe (macOS) or build from source
    query.to_pmtiles(
        "output/buildings.pmtiles",
        layer="buildings",  # Layer name in the tileset
        maxzoom=14,  # Maximum zoom level
    )

    print("Exported to PMTiles format")


def export_to_arrow() -> None:
    """Export to Arrow Table (in-memory)."""
    ds = gf.open("file:///data/buildings.parquet")
    roi = gf.roi.bbox(-74.10, 40.60, -73.70, 40.90)

    query = ds.within(roi).limit(1000)

    # Get as Arrow Table (efficient for inter-process communication)
    arrow_table = query.to_arrow()

    print(f"Arrow Table: {arrow_table.num_rows} rows, {arrow_table.num_columns} columns")
    print(f"Schema: {arrow_table.schema}")


def export_to_pandas() -> None:
    """Export to Pandas DataFrame."""
    ds = gf.open("file:///data/buildings.parquet")
    roi = gf.roi.bbox(-74.10, 40.60, -73.70, 40.90)

    query = ds.within(roi).limit(1000)

    # Get as Pandas DataFrame
    df = query.to_pandas()

    print(f"DataFrame: {len(df)} rows, {len(df.columns)} columns")
    print(f"Columns: {list(df.columns)}")


def export_to_geopandas() -> None:
    """Export to GeoPandas GeoDataFrame."""
    ds = gf.open("file:///data/buildings.parquet")
    roi = gf.roi.bbox(-74.10, 40.60, -73.70, 40.90)

    query = ds.within(roi).limit(1000)

    # Get as GeoDataFrame (requires viz extras)
    gdf = query.to_geopandas()

    print(f"GeoDataFrame: {len(gdf)} rows")
    print(f"CRS: {gdf.crs}")
    print(f"Geometry types: {gdf.geometry.type.unique()}")


def batch_export() -> None:
    """Export the same query to multiple formats."""
    ds = gf.open("file:///data/buildings.parquet")
    roi = gf.roi.bbox(-74.10, 40.60, -73.70, 40.90)

    query = (
        ds.within(roi)
        .select(["id", "name", "type", "geometry"])
        .where("type IS NOT NULL")
        .limit(5000)
    )

    # Export to multiple formats
    query.to_parquet("output/buildings.parquet")
    query.to_geojson("output/buildings.geojson")
    query.to_geopackage("output/buildings.gpkg")
    query.to_flatgeobuf("output/buildings.fgb")
    query.to_csv("output/buildings.csv")

    print("Exported to all formats")


def export_with_transformations() -> None:
    """Export data with spatial transformations applied."""
    ds = gf.open("file:///data/buildings.parquet")
    roi = gf.roi.bbox(-74.10, 40.60, -73.70, 40.90)

    # Apply transformations before export
    query = (
        ds.within(roi)
        .transform(to_srid=3857)  # Convert to Web Mercator
        .buffer(distance=10, unit="meters")
        .simplify(tolerance=1)
        .with_area(col_name="area_sqm")
        .limit(1000)
    )

    query.to_parquet("output/buildings_transformed.parquet")
    print("Exported transformed geometries")


def export_centroids_for_mapping() -> None:
    """Export centroids for point-based visualization."""
    ds = gf.open("file:///data/buildings.parquet")
    roi = gf.roi.bbox(-74.10, 40.60, -73.70, 40.90)

    # Convert polygons to centroids
    query = (
        ds.within(roi)
        .centroid()
        .with_coordinates(x_col="lon", y_col="lat")
        .limit(10000)
    )

    # Export for web mapping
    query.to_geojson("output/building_centroids.geojson")

    # Export to CSV for tools that need lat/lon columns
    query.to_csv("output/building_centroids.csv")

    print("Exported centroids for mapping")


def visualize_in_notebook() -> None:
    """Visualize data in Jupyter notebook."""
    ds = gf.open("file:///data/buildings.parquet")
    roi = gf.roi.bbox(-74.10, 40.60, -73.70, 40.90)

    query = ds.within(roi).limit(5000)

    # Show interactive map (requires viz extras and Jupyter)
    # This uses lonboard for fast WebGL-based rendering
    query.show()

    print("Displayed interactive map")


def main() -> None:
    """Run all examples."""
    print("=" * 60)
    print("GeoFabric Export Formats Examples")
    print("=" * 60)

    print("\nAvailable export methods:")
    print("")
    print("File formats:")
    print("- to_parquet(path)      - GeoParquet (recommended for large data)")
    print("- to_geojson(path)      - GeoJSON (human-readable, web-friendly)")
    print("- to_geopackage(path)   - GeoPackage (SQLite-based, GIS-compatible)")
    print("- to_flatgeobuf(path)   - FlatGeoBuf (streaming, cloud-optimized)")
    print("- to_csv(path)          - CSV with WKT geometry")
    print("- to_pmtiles(path, ...) - Vector tiles (requires tippecanoe)")
    print("")
    print("In-memory formats:")
    print("- to_arrow()            - Arrow Table")
    print("- to_pandas()           - Pandas DataFrame")
    print("- to_geopandas()        - GeoPandas GeoDataFrame")
    print("")
    print("Visualization:")
    print("- show()                - Interactive map (requires viz extras)")

    print("\nUncomment function calls to run with real data.")


if __name__ == "__main__":
    main()
