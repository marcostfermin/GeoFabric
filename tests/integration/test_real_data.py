"""
Integration tests with real Overture Maps data.

These tests verify that GeoFabric works correctly with real-world data formats
from Overture Maps. The sample data was downloaded from:

    Azure: az://release/2025-11-19.0/theme=buildings/type=building/

Key findings about Overture data format:
1. Geometry column type: GEOMETRY (DuckDB spatial type)
2. When exported with ST_AsWKB(), becomes WKB_BLOB (what GeoFabric expects)
3. Geometry is stored as bytearray in pandas

Sample data location:
    tests/data/overture_buildings_sample.geojson  (10 NYC buildings, ~12KB)
    tests/data/overture_buildings_sample.parquet  (same data as parquet, ~7KB)

To refresh the sample data, run:
    python tests/integration/download_overture_sample.py
"""

import os
import tempfile

import pytest

# Skip all tests if sample data doesn't exist
SAMPLE_GEOJSON = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "overture_buildings_sample.geojson",
)
SAMPLE_PARQUET = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "overture_buildings_sample.parquet",
)

pytestmark = pytest.mark.skipif(
    not os.path.exists(SAMPLE_GEOJSON),
    reason="Sample data not found. Run download_overture_sample.py first.",
)


class TestOvertureGeoJSON:
    """Tests using GeoJSON derived from Overture data."""

    def test_load_overture_geojson(self):
        """Load GeoJSON file derived from Overture."""
        import geofabric as gf

        ds = gf.open(f"file://{SAMPLE_GEOJSON}")
        df = ds.query().to_pandas()

        assert len(df) == 10
        assert "geometry" in df.columns
        assert "id" in df.columns

    def test_geometry_type(self):
        """Verify geometry is bytearray (WKB format)."""
        import geofabric as gf

        ds = gf.open(f"file://{SAMPLE_GEOJSON}")
        df = ds.query().to_pandas()

        assert isinstance(df["geometry"].iloc[0], bytearray)

    def test_with_area(self):
        """Calculate area of Overture buildings."""
        import geofabric as gf

        ds = gf.open(f"file://{SAMPLE_GEOJSON}")
        df = ds.query().with_area().to_pandas()

        assert "area" in df.columns
        # All buildings should have positive area
        assert (df["area"] > 0).all()

    def test_with_perimeter(self):
        """Calculate perimeter of Overture buildings."""
        import geofabric as gf

        ds = gf.open(f"file://{SAMPLE_GEOJSON}")
        df = ds.query().with_perimeter().to_pandas()

        assert "perimeter" in df.columns
        assert (df["perimeter"] > 0).all()

    def test_with_coordinates(self):
        """Get centroid coordinates of Overture buildings."""
        import geofabric as gf

        ds = gf.open(f"file://{SAMPLE_GEOJSON}")
        df = ds.query().with_coordinates().to_pandas()

        assert "x" in df.columns
        assert "y" in df.columns
        # NYC coordinates should be around -74, 40
        assert df["x"].between(-75, -73).all()
        assert df["y"].between(39, 42).all()

    def test_centroid(self):
        """Convert buildings to centroids."""
        import geofabric as gf

        ds = gf.open(f"file://{SAMPLE_GEOJSON}")
        df = ds.query().centroid().with_geometry_type().to_pandas()

        assert df["geom_type"].iloc[0] == "POINT"

    def test_buffer_then_area(self):
        """Buffer centroids and calculate area (tests operation chaining)."""
        import geofabric as gf

        ds = gf.open(f"file://{SAMPLE_GEOJSON}")
        df = ds.query().centroid().buffer(distance=100, unit="meters").with_area().to_pandas()

        # 100m buffer should have area ~31,416 sq meters (pi * 100^2)
        # DuckDB uses 32-sided polygon, so ~31,214
        assert df["area"].iloc[0] > 30000
        assert df["area"].iloc[0] < 32000

    def test_dissolve(self):
        """Dissolve all buildings into one geometry."""
        import geofabric as gf

        ds = gf.open(f"file://{SAMPLE_GEOJSON}")
        df = ds.query().dissolve().with_area().to_pandas()

        assert len(df) == 1
        assert df["area"].iloc[0] > 0


class TestOvertureParquet:
    """Tests using Parquet with WKB geometry (native Overture format)."""

    @pytest.mark.skipif(
        not os.path.exists(SAMPLE_PARQUET),
        reason="Parquet sample not found",
    )
    def test_load_overture_parquet(self):
        """Load Parquet file with WKB geometry."""
        import geofabric as gf

        ds = gf.open(f"file://{SAMPLE_PARQUET}")
        df = ds.query().to_pandas()

        assert len(df) == 10
        assert "geometry" in df.columns

    @pytest.mark.skipif(
        not os.path.exists(SAMPLE_PARQUET),
        reason="Parquet sample not found",
    )
    def test_spatial_ops_on_parquet(self):
        """Spatial operations work on parquet with WKB geometry."""
        import geofabric as gf

        ds = gf.open(f"file://{SAMPLE_PARQUET}")
        df = ds.query().with_area().with_perimeter().to_pandas()

        assert "area" in df.columns
        assert "perimeter" in df.columns
        assert (df["area"] > 0).all()


class TestExportRoundtrip:
    """Tests for export and re-import of Overture data."""

    def test_parquet_roundtrip(self):
        """Export to parquet and re-import."""
        import geofabric as gf

        ds = gf.open(f"file://{SAMPLE_GEOJSON}")
        original_count = ds.query().count()

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "test.parquet")
            ds.query().to_parquet(out_path)

            ds_reimport = gf.open(f"file://{out_path}")
            assert ds_reimport.query().count() == original_count

    def test_geojson_roundtrip(self):
        """Export to GeoJSON and re-import."""
        import geofabric as gf

        ds = gf.open(f"file://{SAMPLE_GEOJSON}")
        original_count = ds.query().count()

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "test.geojson")
            ds.query().to_geojson(out_path)

            ds_reimport = gf.open(f"file://{out_path}")
            assert ds_reimport.query().count() == original_count

    def test_spatial_ops_after_roundtrip(self):
        """Spatial operations work after export/import."""
        import geofabric as gf

        ds = gf.open(f"file://{SAMPLE_GEOJSON}")

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "test.parquet")
            ds.query().to_parquet(out_path)

            ds_reimport = gf.open(f"file://{out_path}")
            df = ds_reimport.query().with_area().to_pandas()

            assert "area" in df.columns
            assert (df["area"] > 0).all()
