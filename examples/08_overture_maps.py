#!/usr/bin/env python3
"""
Overture Maps Examples for GeoFabric

This script demonstrates working with Overture Maps data:
- Downloading Overture data releases
- Querying downloaded data
- Processing specific themes and types
- Building workflows with Overture data
"""

import geofabric as gf
from geofabric.sources.overture import Overture


# =============================================================================
# Understanding Overture Maps
# =============================================================================

"""
Overture Maps Foundation provides open map data organized by themes:

Themes:
- addresses      - Address points
- base           - Land/water boundaries, infrastructure
- buildings      - Building footprints
- divisions      - Administrative boundaries
- places         - Points of interest
- transportation - Roads, paths, ferry routes

Each theme has multiple types. For example:
- base: infrastructure, land, land_cover, land_use, water
- buildings: building
- places: place
- transportation: connector, segment

Releases are versioned by date (e.g., "2025-12-17.0")
"""


# =============================================================================
# Downloading Overture Data
# =============================================================================


def download_buildings() -> None:
    """Download Overture buildings data.

    Requires AWS CLI to be installed and configured.
    """
    ov = Overture(
        release="2025-12-17.0",
        theme="buildings",
        type_="building",
    )

    # Download to local directory
    local_path = ov.download("./data/overture/buildings")

    print(f"Downloaded buildings to: {local_path}")


def download_infrastructure() -> None:
    """Download base infrastructure data."""
    ov = Overture(
        release="2025-12-17.0",
        theme="base",
        type_="infrastructure",
    )

    local_path = ov.download("./data/overture/infrastructure")
    print(f"Downloaded infrastructure to: {local_path}")


def download_places() -> None:
    """Download places (POI) data."""
    ov = Overture(
        release="2025-12-17.0",
        theme="places",
        type_="place",
    )

    local_path = ov.download("./data/overture/places")
    print(f"Downloaded places to: {local_path}")


def download_transportation() -> None:
    """Download transportation segments (roads)."""
    ov = Overture(
        release="2025-12-17.0",
        theme="transportation",
        type_="segment",
    )

    local_path = ov.download("./data/overture/roads")
    print(f"Downloaded transportation segments to: {local_path}")


def download_divisions() -> None:
    """Download administrative divisions."""
    ov = Overture(
        release="2025-12-17.0",
        theme="divisions",
        type_="division",
    )

    local_path = ov.download("./data/overture/divisions")
    print(f"Downloaded divisions to: {local_path}")


# =============================================================================
# Querying Overture Data
# =============================================================================


def query_overture_buildings() -> None:
    """Query downloaded Overture buildings."""
    # Open downloaded data
    ds = gf.open("file:///data/overture/buildings")

    # Define region of interest (NYC)
    roi = gf.roi.bbox(-74.10, 40.60, -73.70, 40.90)

    # Query with filters
    result = (
        ds.within(roi)
        .select(["id", "names", "height", "geometry"])
        .where("height > 50")  # Tall buildings
        .limit(1000)
        .to_pandas()
    )

    print(f"Found {len(result)} tall buildings in NYC")


def query_overture_places() -> None:
    """Query Overture places (POIs)."""
    ds = gf.open("file:///data/overture/places")

    roi = gf.roi.bbox(-74.10, 40.60, -73.70, 40.90)

    # Query restaurants
    result = (
        ds.within(roi)
        .where("categories LIKE '%restaurant%'")
        .limit(500)
        .to_pandas()
    )

    print(f"Found {len(result)} restaurants in NYC")


def query_overture_roads() -> None:
    """Query Overture transportation data."""
    ds = gf.open("file:///data/overture/roads")

    roi = gf.roi.bbox(-74.10, 40.60, -73.70, 40.90)

    # Query major roads
    result = (
        ds.within(roi)
        .where("class IN ('primary', 'secondary', 'tertiary')")
        .limit(5000)
        .to_pandas()
    )

    print(f"Found {len(result)} major road segments in NYC")


# =============================================================================
# Processing Workflows
# =============================================================================


def extract_city_buildings() -> None:
    """Extract buildings for a specific city."""
    ds = gf.open("file:///data/overture/buildings")

    # San Francisco bounding box
    sf_bbox = gf.roi.bbox(-122.52, 37.70, -122.35, 37.82)

    # Extract and save
    query = (
        ds.within(sf_bbox)
        .select(["id", "names", "height", "class", "geometry"])
        .with_area(col_name="footprint_area")
    )

    query.to_parquet("sf_buildings.parquet")
    query.to_geojson("sf_buildings.geojson")

    print("Extracted San Francisco buildings")


def analyze_building_heights() -> None:
    """Analyze building heights from Overture data."""
    ds = gf.open("file:///data/overture/buildings")

    roi = gf.roi.bbox(-74.10, 40.60, -73.70, 40.90)

    # Get buildings with height data
    result = (
        ds.within(roi)
        .where("height IS NOT NULL")
        .select(["id", "height", "geometry"])
        .limit(10000)
        .to_pandas()
    )

    # Analyze heights
    if len(result) > 0:
        print("Building Height Analysis:")
        print(f"  Count: {len(result)}")
        print(f"  Min height: {result['height'].min():.1f}m")
        print(f"  Max height: {result['height'].max():.1f}m")
        print(f"  Mean height: {result['height'].mean():.1f}m")
        print(f"  Median height: {result['height'].median():.1f}m")


def create_building_centroids() -> None:
    """Create centroid points from building footprints."""
    ds = gf.open("file:///data/overture/buildings")

    roi = gf.roi.bbox(-74.10, 40.60, -73.70, 40.90)

    # Convert to centroids
    result = (
        ds.within(roi)
        .centroid()
        .with_coordinates(x_col="lon", y_col="lat")
        .limit(50000)
    )

    result.to_parquet("building_centroids.parquet")
    result.to_csv("building_centroids.csv")

    print("Created building centroid points")


def buffer_infrastructure() -> None:
    """Buffer infrastructure features."""
    ds = gf.open("file:///data/overture/infrastructure")

    roi = gf.roi.bbox(-74.10, 40.60, -73.70, 40.90)

    # Buffer power lines by 50 meters
    result = (
        ds.within(roi)
        .where("subtype = 'power_line'")
        .buffer(distance=50, unit="meters")
        .limit(1000)
    )

    result.to_parquet("power_line_buffers.parquet")
    print("Created power line buffer zones")


def create_vector_tiles() -> None:
    """Generate PMTiles from Overture data."""
    ds = gf.open("file:///data/overture/buildings")

    roi = gf.roi.bbox(-74.10, 40.60, -73.70, 40.90)

    query = (
        ds.within(roi)
        .select(["id", "height", "class", "geometry"])
        .simplify(tolerance=0.00001)  # Simplify for tiles
        .limit(100000)
    )

    # Generate PMTiles (requires tippecanoe)
    query.to_pmtiles(
        "nyc_buildings.pmtiles",
        layer="buildings",
        maxzoom=16,
    )

    print("Generated PMTiles for NYC buildings")


def spatial_join_buildings_places() -> None:
    """Join Overture buildings with places."""
    buildings = gf.open("file:///data/overture/buildings")
    places = gf.open("file:///data/overture/places")

    roi = gf.roi.bbox(-74.05, 40.70, -73.95, 40.80)  # Manhattan

    # Find places within buildings
    joined = (
        places.query()
        .within(roi)
        .sjoin(
            buildings.query().within(roi),
            predicate="within",
            how="inner",
        )
        .limit(1000)
    )

    result = joined.to_pandas()
    print(f"Found {len(result)} places within buildings")


# =============================================================================
# CLI Integration
# =============================================================================


def cli_download_example() -> None:
    """Example CLI commands for Overture data.

    These commands can be run from the terminal:

    # Download buildings
    gf overture download --release 2025-12-17.0 --theme buildings --type building --dest ./data

    # Download places
    gf overture download --release 2025-12-17.0 --theme places --type place --dest ./data

    # Download roads
    gf overture download --release 2025-12-17.0 --theme transportation --type segment --dest ./data

    # Query downloaded data
    gf sql file:///data/buildings "SELECT COUNT(*) FROM data"
    gf head file:///data/buildings --n 10
    gf stats file:///data/buildings
    """
    print("See docstring for CLI examples")


def main() -> None:
    """Run all examples."""
    print("=" * 60)
    print("GeoFabric Overture Maps Examples")
    print("=" * 60)

    print("\nOverture Maps Themes and Types:")
    print("")
    print("addresses:")
    print("  - address")
    print("")
    print("base:")
    print("  - infrastructure, land, land_cover, land_use, water")
    print("")
    print("buildings:")
    print("  - building")
    print("")
    print("divisions:")
    print("  - division, division_area, division_boundary")
    print("")
    print("places:")
    print("  - place")
    print("")
    print("transportation:")
    print("  - connector, segment")

    print("\n" + "=" * 60)
    print("Usage:")
    print("")
    print("from geofabric.sources.overture import Overture")
    print("")
    print("ov = Overture(")
    print('    release="2025-12-17.0",')
    print('    theme="buildings",')
    print('    type_="building",')
    print(")")
    print("")
    print('local_path = ov.download("./data/overture/buildings")')
    print("")
    print("# Then query with GeoFabric")
    print("ds = gf.open(local_path)")

    print("\nUncomment function calls to run with real data.")


if __name__ == "__main__":
    main()
