"""
Tests for GeoFabric configuration module.

Tests programmatic credential configuration for all supported platforms.
"""

import pytest

import geofabric as gf
from geofabric.config import (
    AzureConfig,
    GCSConfig,
    GeoFabricConfig,
    HTTPConfig,
    PostGISConfig,
    S3Config,
    STACConfig,
    configure_azure,
    configure_gcs,
    configure_http,
    configure_postgis,
    configure_s3,
    configure_stac,
    get_config,
    reset_config,
)


class TestS3Configuration:
    """Tests for S3 configuration."""

    def setup_method(self):
        """Reset config before each test."""
        reset_config()

    def teardown_method(self):
        """Reset config after each test."""
        reset_config()

    def test_configure_s3_basic(self):
        """Test basic S3 configuration."""
        configure_s3(
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            region="us-east-1",
        )

        config = get_config()
        assert config.s3.access_key_id == "AKIAIOSFODNN7EXAMPLE"
        assert config.s3.secret_access_key == "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        assert config.s3.region == "us-east-1"

    def test_configure_s3_with_session_token(self):
        """Test S3 configuration with session token."""
        configure_s3(
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="secret",
            session_token="AQoDYXdzEJr...",
        )

        config = get_config()
        assert config.s3.session_token == "AQoDYXdzEJr..."

    def test_configure_s3_with_endpoint(self):
        """Test S3 configuration with custom endpoint (MinIO, etc.)."""
        configure_s3(
            access_key_id="minioadmin",
            secret_access_key="minioadmin",
            endpoint="http://localhost:9000",
            use_ssl=False,
        )

        config = get_config()
        assert config.s3.endpoint == "http://localhost:9000"
        assert config.s3.use_ssl is False

    def test_configure_s3_partial(self):
        """Test partial S3 configuration (only some params)."""
        configure_s3(region="eu-west-1")

        config = get_config()
        assert config.s3.region == "eu-west-1"
        assert config.s3.access_key_id is None

    def test_configure_s3_default_use_ssl(self):
        """Test S3 configuration default use_ssl is True."""
        configure_s3(access_key_id="test")

        config = get_config()
        assert config.s3.use_ssl is True


class TestGCSConfiguration:
    """Tests for GCS configuration."""

    def setup_method(self):
        reset_config()

    def teardown_method(self):
        reset_config()

    def test_configure_gcs_basic(self):
        """Test basic GCS configuration."""
        configure_gcs(
            access_key_id="GOOGTS7C7FUP3AIRVJTE2BCD",
            secret_access_key="bGoa+V7g/yqDXvKRqq+JTFn4uQZbPiQJo4pf9RzJ",
        )

        config = get_config()
        assert config.gcs.access_key_id == "GOOGTS7C7FUP3AIRVJTE2BCD"
        assert config.gcs.secret_access_key == "bGoa+V7g/yqDXvKRqq+JTFn4uQZbPiQJo4pf9RzJ"

    def test_configure_gcs_with_project(self):
        """Test GCS configuration with project."""
        configure_gcs(
            access_key_id="GOOGTS7C7FUP3AIRVJTE2BCD",
            secret_access_key="secret",
            project="my-gcp-project",
        )

        config = get_config()
        assert config.gcs.project == "my-gcp-project"


class TestAzureConfiguration:
    """Tests for Azure Blob Storage configuration."""

    def setup_method(self):
        reset_config()

    def teardown_method(self):
        reset_config()

    def test_configure_azure_with_key(self):
        """Test Azure configuration with account key."""
        configure_azure(
            account_name="mystorageaccount",
            account_key="accountkey123...",
        )

        config = get_config()
        assert config.azure.account_name == "mystorageaccount"
        assert config.azure.account_key == "accountkey123..."

    def test_configure_azure_with_connection_string(self):
        """Test Azure configuration with connection string."""
        conn_str = "DefaultEndpointsProtocol=https;AccountName=myaccount;AccountKey=mykey"
        configure_azure(connection_string=conn_str)

        config = get_config()
        assert config.azure.connection_string == conn_str

    def test_configure_azure_with_sas_token(self):
        """Test Azure configuration with SAS token."""
        configure_azure(
            account_name="mystorageaccount",
            sas_token="sv=2021-06-08&ss=b&srt=sco&sp=r...",
        )

        config = get_config()
        assert config.azure.sas_token == "sv=2021-06-08&ss=b&srt=sco&sp=r..."


class TestPostGISConfiguration:
    """Tests for PostGIS configuration."""

    def setup_method(self):
        reset_config()

    def teardown_method(self):
        reset_config()

    def test_configure_postgis_basic(self):
        """Test basic PostGIS configuration."""
        configure_postgis(
            host="db.example.com",
            port=5432,
            database="geodatabase",
            user="geouser",
            password="geopassword",
        )

        config = get_config()
        assert config.postgis.host == "db.example.com"
        assert config.postgis.port == 5432
        assert config.postgis.database == "geodatabase"
        assert config.postgis.user == "geouser"
        assert config.postgis.password == "geopassword"

    def test_configure_postgis_with_ssl(self):
        """Test PostGIS configuration with SSL mode."""
        configure_postgis(
            host="secure-db.example.com",
            user="admin",
            password="secret",
            sslmode="require",
        )

        config = get_config()
        assert config.postgis.sslmode == "require"

    def test_configure_postgis_partial(self):
        """Test partial PostGIS configuration."""
        configure_postgis(
            user="myuser",
            password="mypassword",
        )

        config = get_config()
        assert config.postgis.user == "myuser"
        assert config.postgis.password == "mypassword"
        assert config.postgis.host is None


class TestSTACConfiguration:
    """Tests for STAC configuration."""

    def setup_method(self):
        reset_config()

    def teardown_method(self):
        reset_config()

    def test_configure_stac_with_api_key(self):
        """Test STAC configuration with API key."""
        configure_stac(api_key="my-stac-api-key")

        config = get_config()
        assert config.stac.api_key == "my-stac-api-key"

    def test_configure_stac_with_headers(self):
        """Test STAC configuration with custom headers."""
        configure_stac(
            headers={
                "Authorization": "Bearer eyJ...",
                "X-Custom-Header": "value",
            }
        )

        config = get_config()
        assert config.stac.headers["Authorization"] == "Bearer eyJ..."
        assert config.stac.headers["X-Custom-Header"] == "value"

    def test_configure_stac_with_default_catalog(self):
        """Test STAC configuration with default catalog."""
        configure_stac(
            default_catalog="https://planetarycomputer.microsoft.com/api/stac/v1"
        )

        config = get_config()
        assert (
            config.stac.default_catalog
            == "https://planetarycomputer.microsoft.com/api/stac/v1"
        )

    def test_configure_stac_combined(self):
        """Test STAC configuration with multiple options."""
        configure_stac(
            api_key="key123",
            headers={"X-Custom": "value"},
            default_catalog="https://example.com/stac",
        )

        config = get_config()
        assert config.stac.api_key == "key123"
        assert config.stac.headers["X-Custom"] == "value"
        assert config.stac.default_catalog == "https://example.com/stac"


class TestHTTPConfiguration:
    """Tests for HTTP configuration."""

    def setup_method(self):
        reset_config()

    def teardown_method(self):
        reset_config()

    def test_configure_http_with_proxy(self):
        """Test HTTP configuration with proxy."""
        configure_http(proxy="http://proxy.example.com:8080")

        config = get_config()
        assert config.http.proxy == "http://proxy.example.com:8080"

    def test_configure_http_with_timeout(self):
        """Test HTTP configuration with custom timeout."""
        configure_http(timeout=120)

        config = get_config()
        assert config.http.timeout == 120

    def test_configure_http_with_headers(self):
        """Test HTTP configuration with custom headers."""
        configure_http(headers={"User-Agent": "GeoFabric/1.0"})

        config = get_config()
        assert config.http.headers["User-Agent"] == "GeoFabric/1.0"

    def test_configure_http_disable_ssl_verify(self):
        """Test HTTP configuration with SSL verification disabled."""
        configure_http(verify_ssl=False)

        config = get_config()
        assert config.http.verify_ssl is False

    def test_configure_http_defaults(self):
        """Test HTTP configuration defaults."""
        configure_http()

        config = get_config()
        assert config.http.timeout == 30
        assert config.http.verify_ssl is True
        assert config.http.proxy is None


class TestResetConfiguration:
    """Tests for reset_config()."""

    def test_reset_config_clears_all(self):
        """Test that reset_config clears all configurations."""
        # Configure everything
        configure_s3(access_key_id="key", secret_access_key="secret")
        configure_gcs(access_key_id="gcs_key")
        configure_azure(account_name="account")
        configure_postgis(host="localhost")
        configure_stac(api_key="stac_key")
        configure_http(proxy="http://proxy:8080")

        # Reset
        reset_config()

        # Verify all cleared
        config = get_config()
        assert config.s3.access_key_id is None
        assert config.gcs.access_key_id is None
        assert config.azure.account_name is None
        assert config.postgis.host is None
        assert config.stac.api_key is None
        assert config.http.proxy is None


class TestConfigDataClasses:
    """Tests for configuration dataclass defaults."""

    def test_s3_config_defaults(self):
        """Test S3Config default values."""
        config = S3Config()
        assert config.access_key_id is None
        assert config.secret_access_key is None
        assert config.region is None
        assert config.session_token is None
        assert config.endpoint is None
        assert config.use_ssl is True

    def test_gcs_config_defaults(self):
        """Test GCSConfig default values."""
        config = GCSConfig()
        assert config.access_key_id is None
        assert config.secret_access_key is None
        assert config.project is None

    def test_azure_config_defaults(self):
        """Test AzureConfig default values."""
        config = AzureConfig()
        assert config.account_name is None
        assert config.account_key is None
        assert config.connection_string is None
        assert config.sas_token is None

    def test_postgis_config_defaults(self):
        """Test PostGISConfig default values."""
        config = PostGISConfig()
        assert config.host is None
        assert config.port is None
        assert config.database is None
        assert config.user is None
        assert config.password is None
        assert config.sslmode is None

    def test_stac_config_defaults(self):
        """Test STACConfig default values."""
        config = STACConfig()
        assert config.api_key is None
        assert config.headers == {}
        assert config.default_catalog is None

    def test_http_config_defaults(self):
        """Test HTTPConfig default values."""
        config = HTTPConfig()
        assert config.proxy is None
        assert config.timeout == 30
        assert config.headers == {}
        assert config.verify_ssl is True

    def test_geofabric_config_defaults(self):
        """Test GeoFabricConfig creates all sub-configs."""
        config = GeoFabricConfig()
        assert isinstance(config.s3, S3Config)
        assert isinstance(config.gcs, GCSConfig)
        assert isinstance(config.azure, AzureConfig)
        assert isinstance(config.postgis, PostGISConfig)
        assert isinstance(config.stac, STACConfig)
        assert isinstance(config.http, HTTPConfig)


class TestModuleExports:
    """Tests for module-level exports."""

    def test_configure_functions_exported_from_geofabric(self):
        """Test all configure functions are exported from main module."""
        assert hasattr(gf, "configure_s3")
        assert hasattr(gf, "configure_gcs")
        assert hasattr(gf, "configure_azure")
        assert hasattr(gf, "configure_postgis")
        assert hasattr(gf, "configure_stac")
        assert hasattr(gf, "configure_http")
        assert hasattr(gf, "reset_config")
        assert hasattr(gf, "get_config")

    def test_configure_via_main_module(self):
        """Test configuration works via main module."""
        gf.reset_config()

        gf.configure_s3(access_key_id="test_key")

        config = gf.get_config()
        assert config.s3.access_key_id == "test_key"

        gf.reset_config()


class TestConfigurationPrecedence:
    """Tests verifying configuration is applied correctly."""

    def setup_method(self):
        reset_config()

    def teardown_method(self):
        reset_config()

    def test_s3_config_overwrite(self):
        """Test that S3 config can be overwritten."""
        configure_s3(access_key_id="first_key")
        configure_s3(access_key_id="second_key")

        config = get_config()
        assert config.s3.access_key_id == "second_key"

    def test_independent_configs(self):
        """Test that different service configs are independent."""
        configure_s3(access_key_id="s3_key")
        configure_gcs(access_key_id="gcs_key")

        config = get_config()
        assert config.s3.access_key_id == "s3_key"
        assert config.gcs.access_key_id == "gcs_key"


class TestConfigIntegration:
    """Integration tests for config usage."""

    def setup_method(self):
        reset_config()

    def teardown_method(self):
        reset_config()

    def test_get_config_returns_same_instance(self):
        """Test get_config returns the global config instance."""
        config1 = get_config()
        configure_s3(access_key_id="test")
        config2 = get_config()

        # Should be the same object
        assert config1 is config2
        assert config1.s3.access_key_id == "test"
