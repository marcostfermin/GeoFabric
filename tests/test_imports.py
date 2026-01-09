from __future__ import annotations


def test_package_imports() -> None:
    import geofabric.cli
    import geofabric.engines
    import geofabric.protocols
    import geofabric.sinks
    import geofabric.sources

    assert geofabric.cli is not None
    assert geofabric.engines is not None
    assert geofabric.sinks is not None
    assert geofabric.sources is not None
    assert geofabric.protocols is not None
