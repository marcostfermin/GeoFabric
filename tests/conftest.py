from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock

import pyarrow as pa
import pyarrow.parquet as pq
import pytest


def create_mock_dataset_for_spatial() -> MagicMock:
    """Create a mock dataset that properly handles SQLSource for spatial ops.

    This is needed because spatial operations wrap queries in subqueries using
    SQLSource, and the mock needs to properly dispatch to SQLSource.to_duckdb_relation_sql.
    """
    from geofabric.query import SQLSource

    mock_dataset = MagicMock()

    def source_to_relation_sql_side_effect(source: object) -> str:
        if isinstance(source, SQLSource):
            return f"({source.sql})"
        return "test_table"

    mock_dataset.engine.source_to_relation_sql.side_effect = source_to_relation_sql_side_effect

    # Mock query_to_df to return empty DataFrame for type detection
    empty_df = MagicMock()
    empty_df.__len__ = lambda self: 0
    mock_dataset.engine.query_to_df.return_value = empty_df

    return mock_dataset


@pytest.fixture
def mock_dataset_for_spatial() -> MagicMock:
    """Pytest fixture providing a mock dataset for spatial operation tests."""
    return create_mock_dataset_for_spatial()


@pytest.fixture
def write_tiny_parquet_with_wkb_geometry() -> Callable[[str], None]:
    """
    Pytest fixture that returns a helper function to write a small parquet file
    with a WKB geometry column (POINT(0 0), POINT(1 1)).
    """

    def _write_tiny_parquet_with_wkb_geometry(path: str) -> None:
        geoms = [
            bytes.fromhex("010100000000000000000000000000000000000000"),
            bytes.fromhex("0101000000000000000000F03F000000000000F03F"),
        ]
        table = pa.table(
            {
                "id": pa.array([1, 2], pa.int64()),
                "geometry": pa.array(geoms, pa.binary()),
            }
        )
        pq.write_table(table, path)

    return _write_tiny_parquet_with_wkb_geometry
