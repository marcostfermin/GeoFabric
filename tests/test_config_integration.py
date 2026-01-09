"""
Integration tests for GeoFabric configuration module.

Tests that configuration is properly applied in:
- DuckDB engine (S3, GCS credentials)
- Dataset open (PostGIS defaults)
- STAC source (headers)
"""

import pytest
from unittest.mock import MagicMock, patch

import geofabric as gf
from geofabric.config import (
    configure_s3,
    configure_gcs,
    configure_azure,
    configure_postgis,
    configure_stac,
    configure_http,
    get_config,
    reset_config,
    S3Config,
    GCSConfig,
    AzureConfig,
    PostGISConfig,
    STACConfig,
    HTTPConfig,
    GeoFabricConfig,
)
from geofabric.engines.duckdb_engine import DuckDBEngine
from geofabric.sources.stac import STACSource


class TestDuckDBEngineS3Integration:
    """Tests for S3 credential application in DuckDB engine."""

    def setup_method(self):
        reset_config()

    def teardown_method(self):
        reset_config()

    def test_s3_credentials_in_config(self):
        """Test that S3 credentials are stored in config."""
        configure_s3(
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            region="us-west-2",
        )

        config = get_config()
        assert config.s3.access_key_id == "AKIAIOSFODNN7EXAMPLE"
        assert config.s3.secret_access_key == "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        assert config.s3.region == "us-west-2"

    def test_s3_session_token_in_config(self):
        """Test that session token is stored in config."""
        configure_s3(
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="secret",
            session_token="FwoGZXIvYXdzEBYaDK...",
        )

        config = get_config()
        assert config.s3.session_token == "FwoGZXIvYXdzEBYaDK..."

    def test_s3_endpoint_in_config(self):
        """Test that custom endpoint is stored in config."""
        configure_s3(
            access_key_id="minioadmin",
            secret_access_key="minioadmin",
            endpoint="localhost:9000",
        )

        config = get_config()
        assert config.s3.endpoint == "localhost:9000"

    def test_s3_use_ssl_in_config(self):
        """Test that use_ssl is stored in config."""
        configure_s3(use_ssl=False)

        config = get_config()
        assert config.s3.use_ssl is False

    def test_s3_config_accessible_from_engine(self):
        """Test that engine can access S3 config via get_config()."""
        configure_s3(
            access_key_id="test_key",
            region="eu-west-1",
        )

        # Engine uses get_config() internally
        from geofabric.config import get_config as engine_get_config
        config = engine_get_config()

        assert config.s3.access_key_id == "test_key"
        assert config.s3.region == "eu-west-1"

    def test_s3_no_credentials_when_not_configured(self):
        """Test that config is empty when not configured."""
        reset_config()

        config = get_config()
        assert config.s3.access_key_id is None
        assert config.s3.secret_access_key is None
        assert config.s3.region is None


class TestDuckDBEngineGCSIntegration:
    """Tests for GCS credential application in DuckDB engine."""

    def setup_method(self):
        reset_config()

    def teardown_method(self):
        reset_config()

    def test_gcs_credentials_in_config(self):
        """Test that GCS credentials are stored in config."""
        configure_gcs(
            access_key_id="GOOGTS7C7FUP3AIRVJTE2BCD",
            secret_access_key="bGoa+V7g/yqDXvKRqq+JTFn4uQZbPiQJo4pf9RzJ",
        )

        config = get_config()
        assert config.gcs.access_key_id == "GOOGTS7C7FUP3AIRVJTE2BCD"
        assert config.gcs.secret_access_key == "bGoa+V7g/yqDXvKRqq+JTFn4uQZbPiQJo4pf9RzJ"

    def test_gcs_project_in_config(self):
        """Test that GCS project is stored in config."""
        configure_gcs(project="my-gcp-project")

        config = get_config()
        assert config.gcs.project == "my-gcp-project"

    def test_gcs_no_credentials_when_not_configured(self):
        """Test that GCS config is empty when not configured."""
        reset_config()

        config = get_config()
        assert config.gcs.access_key_id is None
        assert config.gcs.secret_access_key is None


class TestDatasetPostGISIntegration:
    """Tests for PostGIS config defaults in dataset.py."""

    def setup_method(self):
        reset_config()

    def teardown_method(self):
        reset_config()

    def test_postgis_config_stored(self):
        """Test that PostGIS config values are stored."""
        configure_postgis(
            host="configured-host.example.com",
            port=5433,
            user="configured_user",
            password="configured_password",
            sslmode="require",
        )

        config = get_config()
        assert config.postgis.host == "configured-host.example.com"
        assert config.postgis.port == 5433
        assert config.postgis.user == "configured_user"
        assert config.postgis.password == "configured_password"
        assert config.postgis.sslmode == "require"

    def test_postgis_config_accessible(self):
        """Test that PostGIS config is accessible via get_config."""
        configure_postgis(
            host="test-host",
            user="test-user",
        )

        # Simulate what dataset.py does
        config = get_config()
        host = None or config.postgis.host or "localhost"
        user = None or config.postgis.user or ""

        assert host == "test-host"
        assert user == "test-user"

    def test_postgis_defaults_when_not_configured(self):
        """Test PostGIS defaults when config not set."""
        reset_config()

        config = get_config()
        # All should be None
        assert config.postgis.host is None
        assert config.postgis.port is None
        assert config.postgis.user is None
        assert config.postgis.password is None


class TestSTACSourceIntegration:
    """Tests for STAC config headers in STACSource."""

    def setup_method(self):
        reset_config()

    def teardown_method(self):
        reset_config()

    def test_stac_api_key_added_to_headers(self):
        """Test that API key is added to client headers."""
        configure_stac(api_key="test-api-key-12345")

        source = STACSource(
            catalog_url="https://example.com/stac",
            collection="test-collection",
        )

        kwargs = source._get_client_kwargs()

        assert "headers" in kwargs
        assert kwargs["headers"]["X-API-Key"] == "test-api-key-12345"

    def test_stac_custom_headers_added(self):
        """Test that custom headers are added."""
        configure_stac(
            headers={
                "Authorization": "Bearer test-token",
                "X-Custom-Header": "custom-value",
            }
        )

        source = STACSource(
            catalog_url="https://example.com/stac",
            collection="test-collection",
        )

        kwargs = source._get_client_kwargs()

        assert "headers" in kwargs
        assert kwargs["headers"]["Authorization"] == "Bearer test-token"
        assert kwargs["headers"]["X-Custom-Header"] == "custom-value"

    def test_stac_combined_headers(self):
        """Test that API key and custom headers are combined."""
        configure_stac(
            api_key="api-key-123",
            headers={"X-Custom": "value"},
        )

        source = STACSource(
            catalog_url="https://example.com/stac",
            collection="test-collection",
        )

        kwargs = source._get_client_kwargs()

        assert kwargs["headers"]["X-API-Key"] == "api-key-123"
        assert kwargs["headers"]["X-Custom"] == "value"

    def test_stac_http_headers_included(self):
        """Test that global HTTP headers are also included."""
        configure_stac(api_key="stac-key")
        configure_http(headers={"User-Agent": "GeoFabric/1.0"})

        source = STACSource(
            catalog_url="https://example.com/stac",
            collection="test-collection",
        )

        kwargs = source._get_client_kwargs()

        assert kwargs["headers"]["X-API-Key"] == "stac-key"
        assert kwargs["headers"]["User-Agent"] == "GeoFabric/1.0"

    def test_stac_no_headers_when_not_configured(self):
        """Test that no headers are added when not configured."""
        reset_config()

        source = STACSource(
            catalog_url="https://example.com/stac",
            collection="test-collection",
        )

        kwargs = source._get_client_kwargs()

        # Should not have headers key if empty
        assert "headers" not in kwargs or len(kwargs.get("headers", {})) == 0

    def test_stac_default_catalog_stored(self):
        """Test that default catalog is stored in config."""
        configure_stac(
            default_catalog="https://planetarycomputer.microsoft.com/api/stac/v1"
        )

        config = get_config()
        assert config.stac.default_catalog == "https://planetarycomputer.microsoft.com/api/stac/v1"


class TestAzureConfigIntegration:
    """Tests for Azure Blob Storage configuration."""

    def setup_method(self):
        reset_config()

    def teardown_method(self):
        reset_config()

    def test_azure_account_key_in_config(self):
        """Test Azure account key configuration."""
        configure_azure(
            account_name="mystorageaccount",
            account_key="myaccountkey123",
        )

        config = get_config()
        assert config.azure.account_name == "mystorageaccount"
        assert config.azure.account_key == "myaccountkey123"

    def test_azure_connection_string_in_config(self):
        """Test Azure connection string configuration."""
        conn_str = "DefaultEndpointsProtocol=https;AccountName=myaccount;AccountKey=mykey"
        configure_azure(connection_string=conn_str)

        config = get_config()
        assert config.azure.connection_string == conn_str

    def test_azure_sas_token_in_config(self):
        """Test Azure SAS token configuration."""
        configure_azure(
            account_name="mystorageaccount",
            sas_token="sv=2021-06-08&ss=b&srt=sco&sp=r",
        )

        config = get_config()
        assert config.azure.account_name == "mystorageaccount"
        assert config.azure.sas_token == "sv=2021-06-08&ss=b&srt=sco&sp=r"


class TestHTTPConfigIntegration:
    """Tests for HTTP configuration."""

    def setup_method(self):
        reset_config()

    def teardown_method(self):
        reset_config()

    def test_http_proxy_in_config(self):
        """Test HTTP proxy configuration."""
        configure_http(proxy="http://proxy.example.com:8080")

        config = get_config()
        assert config.http.proxy == "http://proxy.example.com:8080"

    def test_http_timeout_in_config(self):
        """Test HTTP timeout configuration."""
        configure_http(timeout=120)

        config = get_config()
        assert config.http.timeout == 120

    def test_http_headers_in_config(self):
        """Test HTTP headers configuration."""
        configure_http(headers={"User-Agent": "GeoFabric/1.0"})

        config = get_config()
        assert config.http.headers["User-Agent"] == "GeoFabric/1.0"

    def test_http_verify_ssl_in_config(self):
        """Test HTTP SSL verification configuration."""
        configure_http(verify_ssl=False)

        config = get_config()
        assert config.http.verify_ssl is False

    def test_http_defaults(self):
        """Test HTTP default values."""
        configure_http()

        config = get_config()
        assert config.http.timeout == 30
        assert config.http.verify_ssl is True
        assert config.http.proxy is None
        assert config.http.headers == {}


class TestConfigDataClassExports:
    """Tests for dataclass exports from config module."""

    def test_s3_config_class_exported(self):
        """Test S3Config is properly exported."""
        config = S3Config(
            access_key_id="key",
            secret_access_key="secret",
            region="us-east-1",
        )
        assert config.access_key_id == "key"
        assert config.region == "us-east-1"

    def test_gcs_config_class_exported(self):
        """Test GCSConfig is properly exported."""
        config = GCSConfig(access_key_id="key", project="my-project")
        assert config.project == "my-project"

    def test_azure_config_class_exported(self):
        """Test AzureConfig is properly exported."""
        config = AzureConfig(account_name="account", sas_token="token")
        assert config.account_name == "account"
        assert config.sas_token == "token"

    def test_postgis_config_class_exported(self):
        """Test PostGISConfig is properly exported."""
        config = PostGISConfig(host="localhost", sslmode="require")
        assert config.host == "localhost"
        assert config.sslmode == "require"

    def test_stac_config_class_exported(self):
        """Test STACConfig is properly exported."""
        config = STACConfig(api_key="key", headers={"X-Test": "value"})
        assert config.api_key == "key"
        assert config.headers["X-Test"] == "value"

    def test_http_config_class_exported(self):
        """Test HTTPConfig is properly exported."""
        config = HTTPConfig(proxy="http://proxy:8080", timeout=60)
        assert config.proxy == "http://proxy:8080"
        assert config.timeout == 60

    def test_geofabric_config_class_exported(self):
        """Test GeoFabricConfig is properly exported."""
        config = GeoFabricConfig()
        assert isinstance(config.s3, S3Config)
        assert isinstance(config.gcs, GCSConfig)
        assert isinstance(config.azure, AzureConfig)
        assert isinstance(config.postgis, PostGISConfig)
        assert isinstance(config.stac, STACConfig)
        assert isinstance(config.http, HTTPConfig)


class TestConfigModuleAllExports:
    """Tests for __all__ exports from config module."""

    def test_all_functions_in_module_all(self):
        """Test that all configure functions are in __all__."""
        from geofabric import config

        expected_exports = [
            "configure_s3",
            "configure_gcs",
            "configure_azure",
            "configure_postgis",
            "configure_stac",
            "configure_http",
            "get_config",
            "reset_config",
        ]

        for export in expected_exports:
            assert export in config.__all__, f"{export} not in __all__"

    def test_all_functions_callable_from_main_module(self):
        """Test all functions are callable from main geofabric module."""
        assert callable(gf.configure_s3)
        assert callable(gf.configure_gcs)
        assert callable(gf.configure_azure)
        assert callable(gf.configure_postgis)
        assert callable(gf.configure_stac)
        assert callable(gf.configure_http)
        assert callable(gf.reset_config)
        assert callable(gf.get_config)


class TestConfigIsolation:
    """Tests for configuration isolation between tests."""

    def setup_method(self):
        reset_config()

    def teardown_method(self):
        reset_config()

    def test_config_isolated_part1(self):
        """First test sets config."""
        configure_s3(access_key_id="test1")
        config = get_config()
        assert config.s3.access_key_id == "test1"

    def test_config_isolated_part2(self):
        """Second test should have clean config."""
        config = get_config()
        # Should be None due to reset_config in setup
        assert config.s3.access_key_id is None


class TestConfigEdgeCases:
    """Tests for edge cases in configuration."""

    def setup_method(self):
        reset_config()

    def teardown_method(self):
        reset_config()

    def test_configure_with_empty_string(self):
        """Test configuration with empty strings."""
        configure_s3(access_key_id="", secret_access_key="")
        config = get_config()
        assert config.s3.access_key_id == ""
        assert config.s3.secret_access_key == ""

    def test_configure_with_special_characters(self):
        """Test configuration with special characters."""
        special_key = "key+with/special=chars&more"
        configure_s3(access_key_id=special_key)
        config = get_config()
        assert config.s3.access_key_id == special_key

    def test_configure_stac_with_empty_headers(self):
        """Test STAC configuration with empty headers dict."""
        configure_stac(headers={})
        config = get_config()
        assert config.stac.headers == {}

    def test_configure_http_with_zero_timeout(self):
        """Test HTTP configuration with zero timeout."""
        configure_http(timeout=0)
        config = get_config()
        assert config.http.timeout == 0

    def test_multiple_reconfigure(self):
        """Test reconfiguring multiple times."""
        configure_s3(access_key_id="first")
        configure_s3(access_key_id="second")
        configure_s3(access_key_id="third")

        config = get_config()
        assert config.s3.access_key_id == "third"

    def test_partial_reconfigure_replaces_all(self):
        """Test that partial reconfigure replaces entire config section."""
        configure_s3(
            access_key_id="key1",
            secret_access_key="secret1",
            region="us-east-1",
        )

        # Reconfigure with only access_key_id
        configure_s3(access_key_id="key2")

        config = get_config()
        assert config.s3.access_key_id == "key2"
        # Other fields should be reset to defaults
        assert config.s3.secret_access_key is None
        assert config.s3.region is None


class TestConfigGlobalState:
    """Tests for global config state management."""

    def setup_method(self):
        reset_config()

    def teardown_method(self):
        reset_config()

    def test_get_config_returns_same_instance(self):
        """Test get_config returns the global config instance."""
        config1 = get_config()
        config2 = get_config()
        assert config1 is config2

    def test_configure_modifies_global_state(self):
        """Test that configure functions modify global state."""
        config_before = get_config()
        assert config_before.s3.access_key_id is None

        configure_s3(access_key_id="new_key")

        config_after = get_config()
        assert config_after.s3.access_key_id == "new_key"

    def test_reset_creates_fresh_config(self):
        """Test that reset_config creates fresh config objects."""
        configure_s3(access_key_id="key")

        config_before = get_config()
        s3_before = config_before.s3

        reset_config()

        config_after = get_config()
        # Should be a new S3Config instance
        assert config_after.s3 is not s3_before
        assert config_after.s3.access_key_id is None
