#!/usr/bin/env python3
"""
Spatial Operations Examples for GeoFabric

This script demonstrates spatial transformations:
- Buffer geometries
- Simplify geometries
- Transform CRS
- Centroid, convex hull, envelope
- Clip, erase, symmetric difference
- Dissolve by attribute
- Geometry repair and validation
"""

import geofabric as gf


def buffer_geometries() -> None:
    """Buffer geometries with unit conversion."""
    ds = gf.open("file:///data/buildings.parquet")

    # Buffer by 100 meters (auto-converts units based on CRS)
    buffered = ds.query().buffer(distance=100, unit="meters").limit(100)

    # Buffer in degrees (for WGS84 data)
    buffered_deg = ds.query().buffer(distance=0.001).limit(100)

    result = buffered.to_geopandas()
    print(f"Buffered {len(result)} geometries by 100 meters")


def simplify_geometries() -> None:
    """Simplify geometries to reduce complexity."""
    ds = gf.open("file:///data/coastlines.parquet")

    # Simplify with Douglas-Peucker algorithm
    # Tolerance in same units as geometry (degrees for WGS84)
    simplified = ds.query().simplify(tolerance=0.001).limit(100)

    result = simplified.to_geopandas()
    print(f"Simplified {len(result)} geometries")


def transform_crs() -> None:
    """Transform coordinate reference system."""
    ds = gf.open("file:///data/buildings.parquet")  # Assume WGS84

    # Transform to Web Mercator (EPSG:3857)
    web_mercator = ds.query().transform(to_srid=3857).limit(100)

    # Transform to UTM Zone 18N (EPSG:32618) for NYC area
    utm = ds.query().transform(to_srid=32618).limit(100)

    result = web_mercator.to_geopandas()
    print(f"Transformed {len(result)} geometries to EPSG:3857")


def extract_centroids() -> None:
    """Extract geometry centroids."""
    ds = gf.open("file:///data/parcels.parquet")

    # Get centroid points from polygons
    centroids = ds.query().centroid().limit(100)

    result = centroids.to_geopandas()
    print(f"Extracted {len(result)} centroids")


def compute_convex_hulls() -> None:
    """Compute convex hulls of geometries."""
    ds = gf.open("file:///data/buildings.parquet")

    # Convex hull wraps around the geometry
    hulls = ds.query().convex_hull().limit(100)

    result = hulls.to_geopandas()
    print(f"Computed {len(result)} convex hulls")


def compute_envelopes() -> None:
    """Compute bounding box envelopes."""
    ds = gf.open("file:///data/buildings.parquet")

    # Envelope returns the bounding rectangle
    envelopes = ds.query().envelope().limit(100)

    result = envelopes.to_geopandas()
    print(f"Computed {len(result)} envelopes")


def extract_boundaries() -> None:
    """Extract geometry boundaries."""
    ds = gf.open("file:///data/parcels.parquet")

    # Boundary extracts the outline (polygon -> linestring)
    boundaries = ds.query().boundary().limit(100)

    result = boundaries.to_geopandas()
    print(f"Extracted {len(result)} boundaries")


def clip_geometries() -> None:
    """Clip geometries to a region (intersection)."""
    ds = gf.open("file:///data/buildings.parquet")

    # Define clip region as WKT
    clip_region = "POLYGON((-74.01 40.71, -73.99 40.71, -73.99 40.73, -74.01 40.73, -74.01 40.71))"

    # Clip returns the intersection
    clipped = ds.query().clip(clip_region).limit(100)

    result = clipped.to_geopandas()
    print(f"Clipped {len(result)} geometries")


def erase_geometries() -> None:
    """Erase a region from geometries (difference)."""
    ds = gf.open("file:///data/parcels.parquet")

    # Define erase region as WKT
    erase_region = "POLYGON((-74.005 40.715, -73.995 40.715, -73.995 40.725, -74.005 40.725, -74.005 40.715))"

    # Erase returns the difference
    erased = ds.query().erase(erase_region).limit(100)

    result = erased.to_geopandas()
    print(f"Erased region from {len(result)} geometries")


def symmetric_difference_operation() -> None:
    """Compute symmetric difference (XOR) with a geometry."""
    ds = gf.open("file:///data/parcels.parquet")

    other_geom = "POLYGON((-74.01 40.71, -73.99 40.71, -73.99 40.73, -74.01 40.73, -74.01 40.71))"

    # XOR operation
    xor_result = ds.query().symmetric_difference(other_geom).limit(100)

    result = xor_result.to_geopandas()
    print(f"Computed symmetric difference for {len(result)} geometries")


def dissolve_by_attribute() -> None:
    """Merge geometries by attribute value."""
    ds = gf.open("file:///data/parcels.parquet")

    # Dissolve merges geometries that share the same attribute value
    dissolved = ds.query().dissolve(by="zoning_code")

    result = dissolved.to_geopandas()
    print(f"Dissolved into {len(result)} groups by zoning code")


def densify_geometries() -> None:
    """Add vertices to geometries."""
    ds = gf.open("file:///data/roads.parquet")

    # Densify adds points along edges
    densified = ds.query().densify(max_distance=100).limit(100)

    result = densified.to_geopandas()
    print(f"Densified {len(result)} geometries")


def explode_multi_geometries() -> None:
    """Split multi-geometries into single geometries."""
    ds = gf.open("file:///data/multipolygons.parquet")

    # Explode splits MultiPolygon into individual Polygons
    exploded = ds.query().explode().limit(100)

    result = exploded.to_geopandas()
    print(f"Exploded into {len(result)} single geometries")


def collect_geometries() -> None:
    """Gather geometries into a MultiGeometry."""
    ds = gf.open("file:///data/points.parquet")

    # Collect gathers all geometries into one MultiGeometry
    collected = ds.query().collect()

    result = collected.to_geopandas()
    print(f"Collected into {len(result)} multi-geometry")


def repair_invalid_geometries() -> None:
    """Repair invalid geometries."""
    ds = gf.open("file:///data/buildings.parquet")

    # make_valid() repairs self-intersecting and other invalid geometries
    repaired = ds.query().make_valid().limit(100)

    result = repaired.to_geopandas()
    print(f"Repaired {len(result)} geometries")


def get_point_on_surface() -> None:
    """Get a point guaranteed to be on the surface."""
    ds = gf.open("file:///data/parcels.parquet")

    # Unlike centroid, point_on_surface is always inside the polygon
    points = ds.query().point_on_surface().limit(100)

    result = points.to_geopandas()
    print(f"Got {len(result)} points on surface")


def reverse_coordinates() -> None:
    """Reverse vertex order in geometries."""
    ds = gf.open("file:///data/roads.parquet")

    # Reverse the order of vertices
    reversed_geoms = ds.query().reverse().limit(100)

    result = reversed_geoms.to_geopandas()
    print(f"Reversed {len(result)} geometries")


def flip_coordinates() -> None:
    """Swap X and Y coordinates."""
    ds = gf.open("file:///data/points.parquet")

    # Useful for fixing lat/lon vs lon/lat issues
    flipped = ds.query().flip_coordinates().limit(100)

    result = flipped.to_geopandas()
    print(f"Flipped coordinates for {len(result)} geometries")


def chain_spatial_operations() -> None:
    """Chain multiple spatial operations."""
    ds = gf.open("file:///data/buildings.parquet")
    roi = gf.roi.bbox(-74.10, 40.60, -73.70, 40.90)

    # Chain operations for complex workflows
    result = (
        ds.query()
        .within(roi)
        .where("type = 'commercial'")
        .make_valid()  # Repair any invalid geometries
        .buffer(distance=50, unit="meters")  # Buffer by 50m
        .simplify(tolerance=0.0001)  # Simplify result
        .limit(100)
        .to_geopandas()
    )

    print(f"Processed {len(result)} geometries with chained operations")


def main() -> None:
    """Run all examples."""
    print("=" * 60)
    print("GeoFabric Spatial Operations Examples")
    print("=" * 60)

    print("\nAvailable spatial operations:")
    print("- buffer(distance, unit)")
    print("- simplify(tolerance)")
    print("- transform(to_srid)")
    print("- centroid()")
    print("- convex_hull()")
    print("- envelope()")
    print("- boundary()")
    print("- clip(wkt)")
    print("- erase(wkt)")
    print("- symmetric_difference(wkt)")
    print("- dissolve(by)")
    print("- densify(max_distance)")
    print("- explode()")
    print("- collect()")
    print("- make_valid()")
    print("- point_on_surface()")
    print("- reverse()")
    print("- flip_coordinates()")

    print("\nUncomment function calls to run with real data.")


if __name__ == "__main__":
    main()
