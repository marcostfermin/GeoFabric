from __future__ import annotations

import sys

import pytest


def test_python_m_geofabric_help() -> None:
    import geofabric.__main__ as main_mod

    assert callable(main_mod.main)

    argv_backup = sys.argv[:]
    try:
        sys.argv = ["geofabric", "--help"]
        with pytest.raises(SystemExit) as e:
            main_mod.main()
        assert e.value.code == 0
    finally:
        sys.argv = argv_backup
