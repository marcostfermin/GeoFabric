from __future__ import annotations

import os
import tempfile

import pandas as pd

import geofabric as gf


def test_open_and_query_parquet_roundtrip(
    write_tiny_parquet_with_wkb_geometry,
) -> None:
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "t.parquet")
        write_tiny_parquet_with_wkb_geometry(path)

        ds = gf.open(path)
        q = ds.select(["id", "geometry"]).limit(1)
        df = q.to_pandas()

        assert isinstance(df, pd.DataFrame)
        assert df.shape[0] == 1
        assert "geometry" in df.columns


def test_open_file_uri_scheme_roundtrip(write_tiny_parquet_with_wkb_geometry) -> None:
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "t.parquet")
        write_tiny_parquet_with_wkb_geometry(path)

        ds = gf.open(f"file://{path}")
        df = ds.limit(2).to_pandas()

        assert df.shape[0] == 2
        assert "geometry" in df.columns


def test_open_unknown_scheme_raises() -> None:
    from geofabric.errors import InvalidURIError

    try:
        gf.open("unknown:/somewhere")
    except InvalidURIError as e:
        assert "Unsupported URI scheme" in str(e)
    else:
        raise AssertionError("Expected InvalidURIError")
