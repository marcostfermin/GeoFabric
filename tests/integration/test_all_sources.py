"""
Integration tests for all GeoFabric data sources.

This module tests each data source type against real public data:
- Files: Local GeoJSON, Parquet, GeoPackage, Shapefile, FlatGeoBuf, CSV
- S3: AWS public datasets (Overture Maps)
- Azure: Azure Blob Storage (Overture Maps)
- GCS: Google Cloud Storage (when available)
- STAC: SpatioTemporal Asset Catalogs (Earth Search, Planetary Computer)
- PostGIS: PostgreSQL/PostGIS databases (requires Docker)

Sample data is stored in tests/data/ for offline testing.
"""

import os
import tempfile

import pytest

# Test data paths
TEST_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
SAMPLE_GEOJSON = os.path.join(TEST_DATA_DIR, "overture_buildings_sample.geojson")
SAMPLE_PARQUET = os.path.join(TEST_DATA_DIR, "overture_buildings_sample.parquet")
SAMPLE_PLACES = os.path.join(TEST_DATA_DIR, "overture_places_sample.parquet")


# =============================================================================
# FILES SOURCE TESTS
# =============================================================================
class TestFilesSource:
    """Tests for local file sources."""

    @pytest.mark.skipif(not os.path.exists(SAMPLE_GEOJSON), reason="Sample data not found")
    def test_geojson_source(self):
        """Load GeoJSON file."""
        import geofabric as gf

        ds = gf.open(f"file://{SAMPLE_GEOJSON}")
        df = ds.query().to_pandas()

        assert len(df) > 0
        assert "geometry" in df.columns
        assert isinstance(df["geometry"].iloc[0], bytearray)

    @pytest.mark.skipif(not os.path.exists(SAMPLE_PARQUET), reason="Sample data not found")
    def test_parquet_source(self):
        """Load Parquet file with WKB geometry."""
        import geofabric as gf

        ds = gf.open(f"file://{SAMPLE_PARQUET}")
        df = ds.query().to_pandas()

        assert len(df) > 0
        assert "geometry" in df.columns

    @pytest.mark.skipif(not os.path.exists(SAMPLE_GEOJSON), reason="Sample data not found")
    def test_geoparquet_roundtrip(self):
        """Export to GeoParquet (geopandas) and re-import."""
        import geofabric as gf

        ds = gf.open(f"file://{SAMPLE_GEOJSON}")

        with tempfile.TemporaryDirectory() as tmpdir:
            # Export with geopandas (creates GeoParquet with GEOMETRY type)
            out_path = os.path.join(tmpdir, "test.parquet")
            ds.query().to_parquet(out_path)

            # Re-import and verify spatial operations work
            ds2 = gf.open(f"file://{out_path}")
            df = ds2.query().with_area().to_pandas()

            assert "area" in df.columns
            assert (df["area"] > 0).all()

    @pytest.mark.skipif(not os.path.exists(SAMPLE_GEOJSON), reason="Sample data not found")
    def test_csv_with_wkt_geometry(self):
        """Load CSV file with WKT geometry column."""
        import geofabric as gf
        import duckdb
        import json

        # Create CSV with WKT from sample GeoJSON
        with open(SAMPLE_GEOJSON) as f:
            geojson = json.load(f)

        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = os.path.join(tmpdir, "test.csv")

            # Create CSV with WKT
            conn = duckdb.connect()
            conn.execute("INSTALL spatial; LOAD spatial;")

            rows = []
            for feature in geojson["features"][:3]:
                geom_json = json.dumps(feature["geometry"])
                wkt = conn.execute(f"SELECT ST_AsText(ST_GeomFromGeoJSON('{geom_json}'))").fetchone()[0]
                rows.append({
                    "id": feature["properties"].get("id", ""),
                    "name": feature["properties"].get("class", ""),
                    "geometry": wkt,
                })

            import csv
            with open(csv_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["id", "name", "geometry"])
                writer.writeheader()
                writer.writerows(rows)

            # Load with GeoFabric
            ds = gf.open(f"file://{csv_path}")
            df = ds.query().to_pandas()

            assert len(df) == 3
            assert "geometry" in df.columns


# =============================================================================
# S3 SOURCE TESTS
# =============================================================================
class TestS3Source:
    """Tests for AWS S3 sources."""

    @pytest.fixture(autouse=True)
    def configure_s3(self):
        """Configure S3 for anonymous access."""
        import geofabric as gf
        gf.configure_s3(region="us-west-2")

    @pytest.mark.skipif(
        os.environ.get("SKIP_NETWORK_TESTS", "").lower() == "true",
        reason="Network tests disabled",
    )
    def test_s3_overture_places(self):
        """Load Overture places from S3."""
        import geofabric as gf

        uri = "s3://overturemaps-us-west-2/release/2025-11-19.0/theme=places/type=place/*.parquet"
        ds = gf.open(uri)

        # Query small area to avoid timeout
        bbox = gf.roi.bbox(-74.01, 40.70, -74.00, 40.71)
        df = ds.query().within(bbox).head(5)  # head() returns DataFrame

        assert len(df) > 0
        assert "geometry" in df.columns
        assert isinstance(df["geometry"].iloc[0], bytearray)

    @pytest.mark.skipif(
        os.environ.get("SKIP_NETWORK_TESTS", "").lower() == "true",
        reason="Network tests disabled",
    )
    def test_s3_spatial_operations(self):
        """Spatial operations work on S3 data."""
        import geofabric as gf

        uri = "s3://overturemaps-us-west-2/release/2025-11-19.0/theme=places/type=place/*.parquet"
        ds = gf.open(uri)

        bbox = gf.roi.bbox(-74.01, 40.70, -74.00, 40.71)
        # Note: with_coordinates() must come before head()
        df = ds.query().within(bbox).with_coordinates().head(1)

        assert "x" in df.columns
        assert "y" in df.columns
        # NYC coordinates
        assert df["x"].iloc[0] < -73
        assert df["y"].iloc[0] > 40


# =============================================================================
# AZURE SOURCE TESTS
# =============================================================================
class TestAzureSource:
    """Tests for Azure Blob Storage sources."""

    @pytest.fixture(autouse=True)
    def configure_azure(self):
        """Configure Azure for Overture public access."""
        import geofabric as gf
        gf.configure_azure(account_name="overturemapswestus2")

    @pytest.mark.skipif(
        os.environ.get("SKIP_NETWORK_TESTS", "").lower() == "true",
        reason="Network tests disabled",
    )
    def test_azure_overture_buildings(self):
        """Load Overture buildings from Azure."""
        import geofabric as gf

        uri = "az://release/2025-11-19.0/theme=buildings/type=building/*.parquet"
        ds = gf.open(uri)

        bbox = gf.roi.bbox(-74.01, 40.70, -74.00, 40.71)
        df = ds.query().within(bbox).head(5)  # head() returns DataFrame

        assert len(df) > 0
        assert "geometry" in df.columns

    @pytest.mark.skipif(
        os.environ.get("SKIP_NETWORK_TESTS", "").lower() == "true",
        reason="Network tests disabled",
    )
    def test_azure_spatial_operations(self):
        """Spatial operations work on Azure data."""
        import geofabric as gf

        uri = "az://release/2025-11-19.0/theme=buildings/type=building/*.parquet"
        ds = gf.open(uri)

        bbox = gf.roi.bbox(-74.01, 40.70, -74.00, 40.71)
        # Note: with_area() must come before head()
        df = ds.query().within(bbox).with_area().head(1)

        assert "area" in df.columns
        assert df["area"].iloc[0] > 0


# =============================================================================
# STAC SOURCE TESTS
# =============================================================================
class TestSTACSource:
    """Tests for STAC catalog sources."""

    @pytest.fixture
    def skip_if_no_pystac(self):
        """Skip test if pystac-client not installed."""
        try:
            import pystac_client  # noqa: F401
        except ImportError:
            pytest.skip("pystac-client not installed")

    @pytest.mark.skipif(
        os.environ.get("SKIP_NETWORK_TESTS", "").lower() == "true",
        reason="Network tests disabled",
    )
    def test_stac_uri_parsing(self, skip_if_no_pystac):
        """Parse STAC URI correctly."""
        import geofabric as gf
        from geofabric.sources.stac import STACSource

        uri = "stac://earth-search.aws.element84.com/v1?collection=sentinel-2-l2a&bbox=-74,40,-73,41"
        source = STACSource.from_uri(uri)

        assert source.catalog_url == "https://earth-search.aws.element84.com/v1"
        assert source.collection == "sentinel-2-l2a"
        assert source.bbox == (-74.0, 40.0, -73.0, 41.0)

    @pytest.mark.skipif(
        os.environ.get("SKIP_NETWORK_TESTS", "").lower() == "true",
        reason="Network tests disabled",
    )
    def test_stac_catalog_connection(self, skip_if_no_pystac):
        """Connect to public STAC catalog."""
        from pystac_client import Client

        # Test Element84 Earth Search
        client = Client.open("https://earth-search.aws.element84.com/v1")
        collections = list(client.get_collections())

        assert len(collections) > 0


# =============================================================================
# POSTGIS SOURCE TESTS
# =============================================================================
class TestPostGISSource:
    """Tests for PostGIS database sources.

    These tests require a running PostgreSQL/PostGIS server.
    Use Docker to start one:
        docker run -d --name geofabric-postgis-test \\
            -e POSTGRES_PASSWORD=testpass \\
            -e POSTGRES_DB=testdb \\
            -p 5433:5432 \\
            postgis/postgis:16-3.4
    """

    @pytest.fixture
    def postgis_available(self):
        """Check if PostGIS is available for testing."""
        import socket

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(("localhost", 5433))
            sock.close()
            if result != 0:
                pytest.skip("PostGIS not available on localhost:5433")
        except Exception:
            pytest.skip("Could not check PostGIS availability")

    def test_postgis_uri_parsing(self):
        """Parse PostGIS URI correctly."""
        from geofabric.sources.postgis import PostGISSource

        uri = "postgresql://user:pass@localhost:5432/mydb?table=buildings&schema=public"
        source = PostGISSource.from_uri(uri)

        assert source.host == "localhost"
        assert source.port == 5432
        assert source.database == "mydb"
        assert source.user == "user"
        assert source.password == "pass"
        assert source.table == "buildings"
        assert source.schema == "public"

    def test_postgis_connection_string(self):
        """Generate safe connection string."""
        from geofabric.sources.postgis import PostGISSource

        source = PostGISSource(
            host="localhost",
            port=5432,
            database="testdb",
            user="testuser",
            password="test'pass",  # Contains quote
            table="buildings",
        )

        # Redacted version for logging
        redacted = source.connection_string(redact_password=True)
        assert "***" in redacted
        assert "test'pass" not in redacted

    @pytest.mark.skip(reason="Requires running PostGIS - enable when Docker available")
    def test_postgis_query(self, postgis_available):
        """Query data from PostGIS."""
        import geofabric as gf

        uri = "postgresql://postgres:testpass@localhost:5433/testdb?table=test_table&schema=public"
        ds = gf.open(uri)
        df = ds.query().to_pandas()

        assert len(df) >= 0  # May be empty if no data


# =============================================================================
# CROSS-SOURCE TESTS
# =============================================================================
class TestCrossSourceOperations:
    """Tests that verify operations work consistently across sources."""

    @pytest.mark.skipif(not os.path.exists(SAMPLE_GEOJSON), reason="Sample data not found")
    def test_geometry_type_consistency(self):
        """Geometry type is consistent (bytearray) across sources."""
        import geofabric as gf

        # Test Files source
        ds_file = gf.open(f"file://{SAMPLE_GEOJSON}")
        df_file = ds_file.query().to_pandas()

        assert isinstance(df_file["geometry"].iloc[0], bytearray)

    @pytest.mark.skipif(not os.path.exists(SAMPLE_GEOJSON), reason="Sample data not found")
    def test_spatial_ops_consistency(self):
        """Spatial operations produce consistent results."""
        import geofabric as gf

        ds = gf.open(f"file://{SAMPLE_GEOJSON}")

        # Test each spatial operation
        with_area = ds.query().with_area().to_pandas()
        assert "area" in with_area.columns
        assert (with_area["area"] >= 0).all()

        with_perimeter = ds.query().with_perimeter().to_pandas()
        assert "perimeter" in with_perimeter.columns
        assert (with_perimeter["perimeter"] >= 0).all()

        with_coords = ds.query().with_coordinates().to_pandas()
        assert "x" in with_coords.columns
        assert "y" in with_coords.columns

        with_bounds = ds.query().with_bounds().to_pandas()
        assert all(c in with_bounds.columns for c in ["minx", "miny", "maxx", "maxy"])

    @pytest.mark.skipif(not os.path.exists(SAMPLE_GEOJSON), reason="Sample data not found")
    def test_export_formats(self):
        """Export to all formats works."""
        import geofabric as gf

        ds = gf.open(f"file://{SAMPLE_GEOJSON}")

        with tempfile.TemporaryDirectory() as tmpdir:
            # Parquet
            pq_path = os.path.join(tmpdir, "test.parquet")
            ds.query().to_parquet(pq_path)
            assert os.path.exists(pq_path)

            # GeoJSON
            gj_path = os.path.join(tmpdir, "test.geojson")
            ds.query().to_geojson(gj_path)
            assert os.path.exists(gj_path)

            # CSV
            csv_path = os.path.join(tmpdir, "test.csv")
            ds.query().to_csv(csv_path)
            assert os.path.exists(csv_path)
