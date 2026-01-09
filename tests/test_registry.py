from __future__ import annotations

import pytest

from geofabric.errors import GeoFabricError
from geofabric.registry import Registry


def test_registry_empty() -> None:
    """Test Registry with empty dictionaries."""
    r = Registry(sources={}, engines={}, sinks={})

    with pytest.raises(GeoFabricError):
        r.get_engine("nonexistent")

    with pytest.raises(GeoFabricError):
        r.get_sink("nonexistent")

    with pytest.raises(GeoFabricError):
        r.get_source_factory("nonexistent")


def test_registry_with_factories() -> None:
    """Test Registry returns factories correctly."""

    def dummy_engine_factory():
        return "engine_instance"

    def dummy_sink_factory():
        return "sink_instance"

    def dummy_source_factory():
        return "source_class"

    r = Registry(
        sources={"dummy": dummy_source_factory},
        engines={"dummy": dummy_engine_factory},
        sinks={"dummy": dummy_sink_factory},
    )

    assert r.get_engine("dummy") == "engine_instance"
    assert r.get_sink("dummy") == "sink_instance"
    assert r.get_source_factory("dummy") == dummy_source_factory
