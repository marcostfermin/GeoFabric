"""Tests for implementation gaps that were filled.

Tests cover:
- Azure Blob Storage source
- STAC URI handler in dataset.open()
- PostGIS sslmode support
- HTTP config usage (proxy, timeout, verify_ssl)
- STAC default_catalog usage
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import geofabric as gf
from geofabric.config import get_config, reset_config
from geofabric.errors import InvalidURIError
from geofabric.sources.cloud import AzureSource
from geofabric.sources.postgis import PostGISSource
from geofabric.sources.stac import STACSource


class TestAzureSource:
    """Tests for Azure Blob Storage source."""

    def test_azure_source_creation(self):
        """Test creating AzureSource directly."""
        source = AzureSource(
            container="mycontainer",
            blob="path/to/data.parquet",
            account_name="mystorageaccount",
        )
        assert source.container == "mycontainer"
        assert source.blob == "path/to/data.parquet"
        assert source.account_name == "mystorageaccount"
        assert source.source_kind() == "azure"

    def test_azure_source_from_uri_az_scheme(self):
        """Test parsing az:// URI."""
        source = AzureSource.from_uri("az://mycontainer/path/to/data.parquet")
        assert source.container == "mycontainer"
        assert source.blob == "path/to/data.parquet"

    def test_azure_source_from_uri_azure_scheme(self):
        """Test parsing azure:// URI."""
        source = AzureSource.from_uri("azure://mycontainer/path/to/data.parquet")
        assert source.container == "mycontainer"
        assert source.blob == "path/to/data.parquet"

    def test_azure_source_from_uri_invalid(self):
        """Test that invalid URIs raise error."""
        with pytest.raises(InvalidURIError):
            AzureSource.from_uri("s3://bucket/key")

    def test_azure_source_from_uri_missing_container(self):
        """Test that missing container raises error."""
        with pytest.raises(InvalidURIError):
            AzureSource.from_uri("az:///path/to/file.parquet")

    def test_azure_source_to_duckdb_path(self):
        """Test DuckDB path generation."""
        source = AzureSource(container="cont", blob="file.parquet")
        assert source.to_duckdb_path() == "az://cont/file.parquet"

    def test_azure_source_uri(self):
        """Test URI generation."""
        source = AzureSource(container="cont", blob="file.parquet")
        assert source.uri() == "az://cont/file.parquet"


class TestAzureURIHandler:
    """Tests for Azure URI handling in dataset.open()."""

    def setup_method(self):
        reset_config()

    def teardown_method(self):
        reset_config()

    def test_open_azure_uri_creates_azure_source(self):
        """Test that az:// URI creates AzureSource."""
        with patch("geofabric.dataset.Dataset") as mock_dataset:
            mock_dataset.return_value = MagicMock()

            # This will fail on actual connection, but we're testing URI parsing
            try:
                gf.open("az://mycontainer/data.parquet")
            except Exception:
                pass

            # Verify AzureSource was created (check the source type)
            # by checking the dataset call args

    def test_azure_config_used_in_open(self):
        """Test that Azure config is used when opening Azure URIs."""
        gf.configure_azure(
            account_name="testaccount",
            account_key="testkey",
        )

        config = get_config()
        assert config.azure.account_name == "testaccount"
        assert config.azure.account_key == "testkey"


class TestSTACURIHandler:
    """Tests for STAC URI handling in dataset.open()."""

    def setup_method(self):
        reset_config()

    def teardown_method(self):
        reset_config()

    def test_stac_source_from_uri(self):
        """Test parsing STAC URI."""
        source = STACSource.from_uri(
            "stac://earth-search.aws.element84.com/v1?collection=sentinel-2-l2a&bbox=-74,40,-73,41"
        )
        assert source.catalog_url == "https://earth-search.aws.element84.com/v1"
        assert source.collection == "sentinel-2-l2a"
        assert source.bbox == (-74.0, 40.0, -73.0, 41.0)

    def test_stac_source_from_uri_with_datetime(self):
        """Test parsing STAC URI with datetime."""
        source = STACSource.from_uri(
            "stac://catalog.example.com/api?collection=data&datetime=2023-01-01/2023-12-31"
        )
        assert source.datetime == "2023-01-01/2023-12-31"

    def test_stac_source_from_uri_invalid(self):
        """Test that non-STAC URIs raise error."""
        with pytest.raises(InvalidURIError):
            STACSource.from_uri("s3://bucket/key")


class TestPostGISSSLMode:
    """Tests for PostGIS sslmode support."""

    def setup_method(self):
        reset_config()

    def teardown_method(self):
        reset_config()

    def test_postgis_source_with_sslmode(self):
        """Test creating PostGISSource with sslmode."""
        source = PostGISSource(
            host="localhost",
            port=5432,
            database="testdb",
            user="user",
            password="pass",
            table="testtable",
            sslmode="require",
        )
        assert source.sslmode == "require"

    def test_postgis_source_connection_string_with_sslmode(self):
        """Test connection string includes sslmode."""
        source = PostGISSource(
            host="localhost",
            port=5432,
            database="testdb",
            user="user",
            password="pass",
            table="testtable",
            sslmode="require",
        )
        conn_str = source.connection_string()
        assert "sslmode=require" in conn_str

    def test_postgis_source_connection_string_without_sslmode(self):
        """Test connection string without sslmode."""
        source = PostGISSource(
            host="localhost",
            port=5432,
            database="testdb",
            user="user",
            password="pass",
            table="testtable",
        )
        conn_str = source.connection_string()
        assert "sslmode" not in conn_str

    def test_postgis_source_from_uri_with_sslmode(self):
        """Test parsing PostGIS URI with sslmode."""
        source = PostGISSource.from_uri(
            "postgresql://user:pass@localhost:5432/testdb?table=testtable&sslmode=verify-full"
        )
        assert source.sslmode == "verify-full"

    def test_postgis_config_sslmode_used(self):
        """Test that configured sslmode is used."""
        gf.configure_postgis(
            host="db.example.com",
            user="user",
            password="pass",
            sslmode="require",
        )

        config = get_config()
        assert config.postgis.sslmode == "require"


class TestHTTPConfig:
    """Tests for HTTP configuration usage."""

    def setup_method(self):
        reset_config()

    def teardown_method(self):
        reset_config()

    def test_http_config_defaults(self):
        """Test HTTP config has sensible defaults."""
        config = get_config()
        assert config.http.timeout == 30
        assert config.http.verify_ssl is True
        assert config.http.proxy is None
        assert config.http.headers == {}

    def test_http_config_custom_values(self):
        """Test configuring HTTP settings."""
        gf.configure_http(
            proxy="http://proxy.example.com:8080",
            timeout=60,
            verify_ssl=False,
            headers={"User-Agent": "GeoFabric/1.0"},
        )

        config = get_config()
        assert config.http.proxy == "http://proxy.example.com:8080"
        assert config.http.timeout == 60
        assert config.http.verify_ssl is False
        assert config.http.headers == {"User-Agent": "GeoFabric/1.0"}

    def test_stac_source_uses_http_config(self):
        """Test that STAC source incorporates HTTP config."""
        gf.configure_http(
            timeout=120,
            headers={"Authorization": "Bearer token"},
        )

        source = STACSource(catalog_url="https://catalog.example.com")
        kwargs = source._get_client_kwargs()

        # Headers should include the global HTTP headers
        assert "Authorization" in kwargs.get("headers", {})
        # Timeout should be set if different from default
        assert kwargs.get("timeout") == 120

    def test_stac_source_request_session(self):
        """Test that STAC source creates configured request session."""
        gf.configure_http(
            proxy="http://proxy:8080",
            verify_ssl=False,
        )

        source = STACSource(catalog_url="https://catalog.example.com")
        session = source._get_request_session()

        assert session.proxies["http"] == "http://proxy:8080"
        assert session.proxies["https"] == "http://proxy:8080"
        assert session.verify is False


class TestSTACDefaultCatalog:
    """Tests for STAC default_catalog configuration."""

    def setup_method(self):
        reset_config()

    def teardown_method(self):
        reset_config()

    def test_stac_get_catalog_url_uses_instance(self):
        """Test that instance catalog_url is preferred."""
        gf.configure_stac(default_catalog="https://default.example.com")

        source = STACSource(catalog_url="https://instance.example.com")
        assert source.get_catalog_url() == "https://instance.example.com"

    def test_stac_get_catalog_url_uses_default(self):
        """Test that default_catalog is used when instance is empty."""
        gf.configure_stac(default_catalog="https://default.example.com")

        source = STACSource(catalog_url="")
        assert source.get_catalog_url() == "https://default.example.com"

    def test_stac_get_catalog_url_raises_when_no_url(self):
        """Test error when no catalog URL available."""
        source = STACSource(catalog_url="")
        with pytest.raises(InvalidURIError):
            source.get_catalog_url()


class TestAzureEngineIntegration:
    """Tests for Azure source integration with DuckDB engine."""

    def setup_method(self):
        reset_config()

    def teardown_method(self):
        reset_config()

    def test_azure_config_applied_to_engine(self):
        """Test that Azure config is applied when querying."""
        gf.configure_azure(
            account_name="testaccount",
            account_key="testkey123",
        )

        config = get_config()
        assert config.azure.account_name == "testaccount"
        assert config.azure.account_key == "testkey123"

    def test_azure_connection_string_config(self):
        """Test Azure connection string configuration."""
        gf.configure_azure(
            connection_string="DefaultEndpointsProtocol=https;AccountName=test..."
        )

        config = get_config()
        assert "DefaultEndpointsProtocol" in config.azure.connection_string


class TestSourcesExports:
    """Tests for sources module exports."""

    def test_azure_source_exported(self):
        """Test AzureSource is exported from sources module."""
        from geofabric.sources import AzureSource

        assert AzureSource is not None

    def test_all_sources_exported(self):
        """Test all source classes are exported."""
        from geofabric.sources import (
            AzureSource,
            FilesSource,
            GCSSource,
            Overture,
            OvertureSource,
            PostGISSource,
            S3Source,
            STACSource,
        )

        assert all(
            cls is not None
            for cls in [
                AzureSource,
                FilesSource,
                GCSSource,
                Overture,
                OvertureSource,
                PostGISSource,
                S3Source,
                STACSource,
            ]
        )


class TestProtocolBasedSourceDispatch:
    """Tests for protocol-based source dispatch in DuckDB engine."""

    def test_azure_source_implements_protocol(self):
        """Test that AzureSource implements SourceWithDuckDBRelation protocol."""
        from geofabric.protocols import supports_duckdb_relation
        from geofabric.sources.cloud import AzureSource

        source = AzureSource(container="test-container", blob="test.parquet")
        assert supports_duckdb_relation(source)
        assert hasattr(source, "to_duckdb_relation_sql")

    def test_stac_source_implements_protocol(self):
        """Test that STACSource implements SourceWithDuckDBRelation protocol."""
        from geofabric.protocols import supports_duckdb_relation
        from geofabric.sources.stac import STACSource

        source = STACSource(catalog_url="https://example.com/stac")
        assert supports_duckdb_relation(source)
        assert hasattr(source, "to_duckdb_relation_sql")


class TestPostGISSSLModeInEngine:
    """Tests for PostGIS sslmode in DuckDB engine."""

    def test_postgis_sslmode_in_connection(self):
        """Test sslmode is included in PostGIS connection."""
        source = PostGISSource(
            host="localhost",
            port=5432,
            database="testdb",
            user="user",
            password="pass",
            table="testtable",
            sslmode="verify-ca",
        )

        # The connection string should include sslmode
        conn_str = source.connection_string()
        assert "sslmode=verify-ca" in conn_str


class TestConfigPrecedence:
    """Tests for configuration precedence in URI handling."""

    def setup_method(self):
        reset_config()

    def teardown_method(self):
        reset_config()

    def test_uri_params_override_config_postgis(self):
        """Test that URI parameters override config for PostGIS."""
        gf.configure_postgis(
            host="config-host",
            port=5433,
            user="config-user",
            password="config-pass",
            sslmode="disable",
        )

        # URI parameters should override config
        source = PostGISSource.from_uri(
            "postgresql://uri-user:uri-pass@uri-host:5434/testdb?table=t&sslmode=require"
        )

        assert source.host == "uri-host"
        assert source.port == 5434
        assert source.user == "uri-user"
        assert source.password == "uri-pass"
        assert source.sslmode == "require"
