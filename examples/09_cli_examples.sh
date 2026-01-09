#!/bin/bash
# =============================================================================
# GeoFabric CLI Examples
# =============================================================================
#
# This script demonstrates GeoFabric command-line interface usage.
# Run individual commands or source this file for reference.
#
# Prerequisites:
#   pip install geofabric
#   For PMTiles: install tippecanoe
#
# =============================================================================

# Exit on error (comment out to run interactively)
# set -e

# Sample data path (replace with your actual data)
DATA_FILE="file:///path/to/your/data.parquet"
OUTPUT_DIR="./output"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# =============================================================================
# Help and Information
# =============================================================================

echo "=== GeoFabric CLI Examples ==="
echo ""

# Show all available commands
gf --help

# Show help for a specific command
gf sql --help
gf pull --help

# =============================================================================
# Dataset Information
# =============================================================================

echo ""
echo "=== Dataset Information ==="

# Show basic info about a dataset
gf info "$DATA_FILE"

# Show first N rows (default 10)
gf head "$DATA_FILE"
gf head "$DATA_FILE" --n 20

# Show dataset statistics
gf stats "$DATA_FILE"

# Validate geometries
gf validate "$DATA_FILE"

# =============================================================================
# SQL Queries
# =============================================================================

echo ""
echo "=== SQL Queries ==="

# Run arbitrary SQL queries
gf sql "$DATA_FILE" "SELECT COUNT(*) FROM data"

gf sql "$DATA_FILE" "SELECT DISTINCT type FROM data LIMIT 10"

gf sql "$DATA_FILE" "SELECT id, name, type FROM data WHERE type = 'building' LIMIT 5"

# Aggregate queries
gf sql "$DATA_FILE" "SELECT type, COUNT(*) as count FROM data GROUP BY type ORDER BY count DESC LIMIT 10"

# =============================================================================
# Data Extraction
# =============================================================================

echo ""
echo "=== Data Extraction ==="

# Pull subset of data
gf pull "$DATA_FILE" "$OUTPUT_DIR/subset.parquet" --limit 1000

# Pull with WHERE clause
gf pull "$DATA_FILE" "$OUTPUT_DIR/buildings.parquet" --where "type='building'" --limit 5000

# Pull with bounding box (minx,miny,maxx,maxy)
gf pull "$DATA_FILE" "$OUTPUT_DIR/nyc.parquet" --bbox "-74.10,40.60,-73.70,40.90" --limit 10000

# Random sample
gf sample "$DATA_FILE" "$OUTPUT_DIR/sample.parquet" --n 1000

# Sample with seed for reproducibility
gf sample "$DATA_FILE" "$OUTPUT_DIR/sample_seeded.parquet" --n 1000 --seed 42

# =============================================================================
# Spatial Operations
# =============================================================================

echo ""
echo "=== Spatial Operations ==="

# Buffer geometries
gf buffer "$DATA_FILE" "$OUTPUT_DIR/buffered.parquet" --distance 100 --unit meters

# Simplify geometries
gf simplify "$DATA_FILE" "$OUTPUT_DIR/simplified.parquet" --tolerance 0.001

# Transform CRS
gf transform "$DATA_FILE" "$OUTPUT_DIR/web_mercator.parquet" --to-srid 3857

# Compute centroids
gf centroid "$DATA_FILE" "$OUTPUT_DIR/centroids.parquet"

# Compute convex hulls
gf convex-hull "$DATA_FILE" "$OUTPUT_DIR/hulls.parquet"

# Dissolve by attribute
gf dissolve "$DATA_FILE" "$OUTPUT_DIR/dissolved.parquet" --by zone_code

# =============================================================================
# Add Computed Columns
# =============================================================================

echo ""
echo "=== Computed Columns ==="

# Add area column
gf add-area "$DATA_FILE" "$OUTPUT_DIR/with_area.parquet"
gf add-area "$DATA_FILE" "$OUTPUT_DIR/with_area_custom.parquet" --column-name area_sqm

# Add length/perimeter column
gf add-length "$DATA_FILE" "$OUTPUT_DIR/with_length.parquet"
gf add-length "$DATA_FILE" "$OUTPUT_DIR/with_length_custom.parquet" --column-name perimeter_m

# =============================================================================
# Overture Maps
# =============================================================================

echo ""
echo "=== Overture Maps ==="

# Download Overture data
gf overture download \
    --release 2025-12-17.0 \
    --theme buildings \
    --type building \
    --dest ./data/overture

# Download places (POIs)
gf overture download \
    --release 2025-12-17.0 \
    --theme places \
    --type place \
    --dest ./data/overture

# Download transportation (roads)
gf overture download \
    --release 2025-12-17.0 \
    --theme transportation \
    --type segment \
    --dest ./data/overture

# =============================================================================
# Chained Operations (using pipes or sequential commands)
# =============================================================================

echo ""
echo "=== Workflow Examples ==="

# Extract, transform, and analyze
gf pull "$DATA_FILE" "$OUTPUT_DIR/step1.parquet" --where "type='commercial'" --limit 5000
gf buffer "file://$OUTPUT_DIR/step1.parquet" "$OUTPUT_DIR/step2.parquet" --distance 50 --unit meters
gf add-area "file://$OUTPUT_DIR/step2.parquet" "$OUTPUT_DIR/final.parquet"
gf stats "file://$OUTPUT_DIR/final.parquet"

# =============================================================================
# Output Formats
# =============================================================================

echo ""
echo "=== Output Format Notes ==="
echo ""
echo "GeoFabric CLI outputs to Parquet by default."
echo "For other formats, use the Python API:"
echo ""
echo "  import geofabric as gf"
echo "  ds = gf.open('file:///data.parquet')"
echo "  q = ds.query().limit(1000)"
echo ""
echo "  q.to_parquet('out.parquet')"
echo "  q.to_geojson('out.geojson')"
echo "  q.to_geopackage('out.gpkg')"
echo "  q.to_flatgeobuf('out.fgb')"
echo "  q.to_csv('out.csv')"
echo "  q.to_pmtiles('out.pmtiles', layer='data')"

# =============================================================================
# Summary
# =============================================================================

echo ""
echo "=== Available Commands ==="
echo ""
echo "Information:"
echo "  gf info URI          - Show dataset info"
echo "  gf stats URI         - Show statistics"
echo "  gf validate URI      - Validate geometries"
echo "  gf head URI          - Show first rows"
echo ""
echo "Query & Extract:"
echo "  gf sql URI QUERY     - Run SQL query"
echo "  gf pull URI OUT      - Extract subset"
echo "  gf sample URI OUT    - Random sample"
echo ""
echo "Spatial Operations:"
echo "  gf buffer URI OUT    - Buffer geometries"
echo "  gf simplify URI OUT  - Simplify geometries"
echo "  gf transform URI OUT - Transform CRS"
echo "  gf centroid URI OUT  - Compute centroids"
echo "  gf convex-hull URI OUT - Compute convex hulls"
echo "  gf dissolve URI OUT  - Dissolve by attribute"
echo ""
echo "Computed Columns:"
echo "  gf add-area URI OUT   - Add area column"
echo "  gf add-length URI OUT - Add length column"
echo ""
echo "Overture Maps:"
echo "  gf overture download - Download Overture data"
echo ""
echo "For detailed help: gf COMMAND --help"
