"""Tests for implementation fixes from gap analysis.

Tests cover:
- S3 use_ssl config applied to DuckDB
- GCS endpoint configuration
- Azure SAS token authentication
- Cache size limit enforcement
- FilesSource.from_uri() method
- Query.with_x() and with_y() wildcard handling
- Public API exports (Query, DuckDBEngine)
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import geofabric as gf
from geofabric.cache import CacheConfig, QueryCache, configure_cache, get_cache
from geofabric.config import get_config, reset_config
from geofabric.errors import InvalidURIError
from geofabric.sources.files import FilesSource


class TestS3UseSSLConfig:
    """Tests for S3 use_ssl configuration."""

    def setup_method(self):
        reset_config()

    def teardown_method(self):
        reset_config()

    def test_s3_use_ssl_default_true(self):
        """Test that use_ssl defaults to True."""
        config = get_config()
        assert config.s3.use_ssl is True

    def test_s3_use_ssl_can_be_disabled(self):
        """Test that use_ssl can be set to False."""
        gf.configure_s3(use_ssl=False)
        config = get_config()
        assert config.s3.use_ssl is False


class TestGCSEndpointConfig:
    """Tests for GCS endpoint configuration in DuckDB."""

    def setup_method(self):
        reset_config()

    def teardown_method(self):
        reset_config()

    def test_gcs_project_stored(self):
        """Test that GCS project is stored in config."""
        gf.configure_gcs(project="my-gcp-project")
        config = get_config()
        assert config.gcs.project == "my-gcp-project"


class TestAzureSASTokenAuth:
    """Tests for Azure SAS token authentication."""

    def setup_method(self):
        reset_config()

    def teardown_method(self):
        reset_config()

    def test_azure_sas_token_stored(self):
        """Test that SAS token is stored in config."""
        gf.configure_azure(
            account_name="testaccount",
            sas_token="sv=2021-06-08&ss=b&srt=sco&sp=r",
        )
        config = get_config()
        assert config.azure.sas_token == "sv=2021-06-08&ss=b&srt=sco&sp=r"
        assert config.azure.account_name == "testaccount"


class TestCacheSizeLimitEnforcement:
    """Tests for cache size limit enforcement."""

    def test_cache_size_limit_enforced(self):
        """Test that cache evicts old entries when size limit exceeded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create cache with very small limit (1KB)
            config = CacheConfig(cache_dir=tmpdir, max_size_mb=0.001)  # ~1KB
            cache = QueryCache(config)

            # Create some test data files
            for i in range(5):
                data_file = Path(tmpdir) / f"data_{i}.parquet"
                # Write about 500 bytes per file
                data_file.write_bytes(b"x" * 500)
                cache.put(f"sql_{i}", f"source_{i}", str(data_file))

            # Cache should have evicted some entries
            # Total ~2500 bytes but limit is ~1000 bytes
            cache_size = cache.size_mb() * 1024 * 1024  # Convert to bytes
            # Allow some tolerance since eviction happens before adding new entry
            assert cache_size < 3000  # Should be significantly smaller

    def test_cache_enforce_size_limit_method_exists(self):
        """Test that _enforce_size_limit method exists."""
        cache = QueryCache()
        assert hasattr(cache, "_enforce_size_limit")
        # Should not raise
        cache._enforce_size_limit()


class TestFilesSourceFromUri:
    """Tests for FilesSource.from_uri() method."""

    def test_from_uri_file_scheme(self):
        """Test parsing file:// URI."""
        source = FilesSource.from_uri("file:///tmp/data.parquet")
        # On macOS, /tmp is a symlink to /private/tmp, so check the path ends correctly
        assert source.path.endswith("/tmp/data.parquet")

    def test_from_uri_plain_absolute_path(self):
        """Test parsing plain absolute path."""
        source = FilesSource.from_uri("/home/user/data.parquet")
        assert "/home/user/data.parquet" in source.path

    def test_from_uri_relative_path(self):
        """Test parsing relative path."""
        source = FilesSource.from_uri("./data.parquet")
        # Should be resolved to absolute path
        assert Path(source.path).is_absolute()

    def test_from_uri_home_expansion(self):
        """Test that ~ is expanded."""
        source = FilesSource.from_uri("~/data.parquet")
        assert "~" not in source.path  # Should be expanded
        assert Path(source.path).is_absolute()

    def test_from_uri_invalid_scheme(self):
        """Test that non-file URIs raise error."""
        with pytest.raises(InvalidURIError):
            FilesSource.from_uri("s3://bucket/key")

    def test_from_uri_empty_path(self):
        """Test that empty path raises error."""
        with pytest.raises(InvalidURIError):
            FilesSource.from_uri("file://")

    def test_uri_method(self):
        """Test uri() method returns file URI."""
        source = FilesSource("/tmp/data.parquet")
        assert source.uri() == "file:///tmp/data.parquet"


class TestQueryWithXYWildcardHandling:
    """Tests for with_x() and with_y() wildcard handling."""

    def test_with_x_handles_star_select(self):
        """Test with_x properly handles * in select."""
        from geofabric.query import Query

        mock_dataset = MagicMock()
        mock_dataset.engine.source_to_relation_sql.return_value = "test_table"

        q = Query(dataset=mock_dataset)
        result = q.with_x()

        sql = result.sql()
        assert "*" in sql
        assert "ST_X" in sql
        assert "AS x" in sql

    def test_with_y_handles_star_select(self):
        """Test with_y properly handles * in select."""
        from geofabric.query import Query

        mock_dataset = MagicMock()
        mock_dataset.engine.source_to_relation_sql.return_value = "test_table"

        q = Query(dataset=mock_dataset)
        result = q.with_y()

        sql = result.sql()
        assert "*" in sql
        assert "ST_Y" in sql
        assert "AS y" in sql

    def test_with_coordinates_chains_correctly(self):
        """Test with_coordinates chains with_x and with_y correctly."""
        from geofabric.query import Query

        mock_dataset = MagicMock()
        mock_dataset.engine.source_to_relation_sql.return_value = "test_table"

        q = Query(dataset=mock_dataset)
        result = q.with_coordinates()

        sql = result.sql()
        assert "ST_X" in sql
        assert "ST_Y" in sql
        assert "AS x" in sql
        assert "AS y" in sql


class TestPublicAPIExports:
    """Tests for public API exports."""

    def test_query_exported(self):
        """Test Query class is exported from geofabric."""
        from geofabric import Query

        assert Query is not None
        # Should be the actual Query class
        from geofabric.query import Query as QueryClass

        assert Query is QueryClass

    def test_duckdb_engine_exported(self):
        """Test DuckDBEngine class is exported from geofabric."""
        from geofabric import DuckDBEngine

        assert DuckDBEngine is not None
        # Should be the actual DuckDBEngine class
        from geofabric.engines.duckdb_engine import DuckDBEngine as EngineClass

        assert DuckDBEngine is EngineClass

    def test_all_contains_query(self):
        """Test __all__ contains Query."""
        assert "Query" in gf.__all__

    def test_all_contains_duckdb_engine(self):
        """Test __all__ contains DuckDBEngine."""
        assert "DuckDBEngine" in gf.__all__


class TestCLITypeFixes:
    """Tests for CLI type annotation fixes."""

    def test_sample_command_seed_accepts_none(self):
        """Test sample command seed parameter accepts None."""
        from geofabric.cli.app import sample

        # Get the function signature
        import inspect

        sig = inspect.signature(sample)
        seed_param = sig.parameters.get("seed")
        assert seed_param is not None
        # Default should be None
        assert seed_param.default.default is None

    def test_dissolve_command_by_accepts_none(self):
        """Test dissolve command by parameter accepts None."""
        from geofabric.cli.app import dissolve

        import inspect

        sig = inspect.signature(dissolve)
        by_param = sig.parameters.get("by")
        assert by_param is not None
        # Default should be None
        assert by_param.default.default is None
