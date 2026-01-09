"""Extended tests for Dataset module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


class TestDatasetOpenFunction:
    """Tests for the gf.open function."""

    def test_open_s3_uri(self) -> None:
        """Test open with s3:// URI."""
        import geofabric as gf
        from geofabric.sources.cloud import S3Source

        ds = gf.open("s3://bucket/path/to/file.parquet")
        assert isinstance(ds.source, S3Source)
        assert ds.source.bucket == "bucket"
        assert ds.source.key == "path/to/file.parquet"

    def test_open_gs_uri(self) -> None:
        """Test open with gs:// URI."""
        import geofabric as gf
        from geofabric.sources.cloud import GCSSource

        ds = gf.open("gs://bucket/path/to/file.parquet")
        assert isinstance(ds.source, GCSSource)
        assert ds.source.bucket == "bucket"
        assert ds.source.key == "path/to/file.parquet"

    def test_open_postgresql_uri(self) -> None:
        """Test open with postgresql:// URI."""
        import geofabric as gf
        from geofabric.sources.postgis import PostGISSource

        ds = gf.open("postgresql://user:pass@localhost/db?table=test")
        assert isinstance(ds.source, PostGISSource)
        assert ds.source.host == "localhost"
        assert ds.source.table == "test"


class TestDatasetQuery:
    """Tests for Dataset.query method."""

    def test_dataset_query_returns_query(self) -> None:
        """Test that Dataset.query returns a Query object."""
        from geofabric.dataset import Dataset
        from geofabric.query import Query

        mock_engine = MagicMock()
        ds = Dataset(source=MagicMock(), engine=mock_engine)
        q = ds.query()

        assert isinstance(q, Query)
        assert q.dataset is ds

    def test_dataset_limit(self) -> None:
        """Test Dataset.limit method."""
        from geofabric.dataset import Dataset

        mock_engine = MagicMock()
        ds = Dataset(source=MagicMock(), engine=mock_engine)
        q = ds.limit(10)

        assert q._limit == 10


class TestDatasetCount:
    """Tests for Dataset.count method."""

    def test_dataset_count(self) -> None:
        """Test Dataset.count method."""
        from geofabric.dataset import Dataset

        mock_engine = MagicMock()
        mock_engine.query_to_df.return_value = pd.DataFrame({"cnt": [42]})
        ds = Dataset(source=MagicMock(), engine=mock_engine)

        count = ds.count()
        assert count == 42


class TestDatasetHead:
    """Tests for Dataset.head method."""

    def test_dataset_head(self) -> None:
        """Test Dataset.head method."""
        from geofabric.dataset import Dataset

        mock_engine = MagicMock()
        mock_engine.query_to_df.return_value = pd.DataFrame({"id": [1, 2, 3]})
        ds = Dataset(source=MagicMock(), engine=mock_engine)

        df = ds.head(3)
        assert isinstance(df, pd.DataFrame)


class TestDatasetSample:
    """Tests for Dataset.sample method."""

    def test_dataset_sample(self) -> None:
        """Test Dataset.sample method."""
        from geofabric.dataset import Dataset

        mock_engine = MagicMock()
        mock_engine.query_to_df.return_value = pd.DataFrame({"id": [1, 2]})
        ds = Dataset(source=MagicMock(), engine=mock_engine)

        df = ds.sample(2, seed=42)
        assert isinstance(df, pd.DataFrame)


class TestDatasetColumns:
    """Tests for Dataset.columns property."""

    def test_dataset_columns(self) -> None:
        """Test Dataset.columns property."""
        from geofabric.dataset import Dataset

        mock_engine = MagicMock()
        mock_engine.query_to_df.return_value = pd.DataFrame({
            "id": pd.Series(dtype="int64"),
            "name": pd.Series(dtype="object"),
        })
        ds = Dataset(source=MagicMock(), engine=mock_engine)

        cols = ds.columns
        assert "id" in cols
        assert "name" in cols


class TestDatasetDtypes:
    """Tests for Dataset.dtypes property."""

    def test_dataset_dtypes(self) -> None:
        """Test Dataset.dtypes property."""
        from geofabric.dataset import Dataset

        mock_engine = MagicMock()
        mock_engine.query_to_df.return_value = pd.DataFrame({
            "id": pd.Series(dtype="int64"),
            "name": pd.Series(dtype="object"),
        })
        ds = Dataset(source=MagicMock(), engine=mock_engine)

        dtypes = ds.dtypes
        assert "id" in dtypes
        assert "name" in dtypes
