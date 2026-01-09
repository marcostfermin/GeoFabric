"""Extended tests for Registry module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestRegistryLoad:
    """Tests for Registry.load()."""

    def test_registry_load(self) -> None:
        """Test Registry.load loads entry points."""
        from geofabric.registry import Registry

        # Should load without error
        registry = Registry.load()
        assert hasattr(registry, "sources")
        assert hasattr(registry, "engines")
        assert hasattr(registry, "sinks")

    def test_registry_load_with_entry_points(self) -> None:
        """Test Registry.load with mocked entry points."""
        from geofabric.registry import Registry

        mock_source_ep = MagicMock()
        mock_source_ep.name = "test_source"
        mock_source_ep.load.return_value = MagicMock()

        mock_engine_ep = MagicMock()
        mock_engine_ep.name = "test_engine"
        mock_engine_ep.load.return_value = MagicMock()

        mock_sink_ep = MagicMock()
        mock_sink_ep.name = "test_sink"
        mock_sink_ep.load.return_value = MagicMock()

        mock_eps = MagicMock()
        mock_eps.select.side_effect = [
            [mock_source_ep],  # sources
            [mock_engine_ep],  # engines
            [mock_sink_ep],  # sinks
        ]

        with patch("geofabric.registry.entry_points", return_value=mock_eps):
            registry = Registry.load()
            assert "test_source" in registry.sources
            assert "test_engine" in registry.engines
            assert "test_sink" in registry.sinks


class TestRegistryGetters:
    """Tests for Registry getter methods."""

    def test_get_engine_not_found(self) -> None:
        """Test get_engine raises error for unknown engine."""
        from geofabric.errors import GeoFabricError
        from geofabric.registry import Registry

        registry = Registry(sources={}, engines={}, sinks={})
        with pytest.raises(GeoFabricError, match="Engine 'unknown' not found"):
            registry.get_engine("unknown")

    def test_get_sink_not_found(self) -> None:
        """Test get_sink raises error for unknown sink."""
        from geofabric.errors import GeoFabricError
        from geofabric.registry import Registry

        registry = Registry(sources={}, engines={}, sinks={})
        with pytest.raises(GeoFabricError, match="Sink 'unknown' not found"):
            registry.get_sink("unknown")

    def test_get_source_factory_not_found(self) -> None:
        """Test get_source_factory raises error for unknown source."""
        from geofabric.errors import GeoFabricError
        from geofabric.registry import Registry

        registry = Registry(sources={}, engines={}, sinks={})
        with pytest.raises(GeoFabricError, match="Source 'unknown' not found"):
            registry.get_source_factory("unknown")

    def test_get_engine_success(self) -> None:
        """Test get_engine returns engine instance."""
        from geofabric.registry import Registry

        mock_factory = MagicMock(return_value="engine_instance")
        registry = Registry(sources={}, engines={"test": mock_factory}, sinks={})
        result = registry.get_engine("test")
        assert result == "engine_instance"
        mock_factory.assert_called_once()

    def test_get_sink_success(self) -> None:
        """Test get_sink returns sink instance."""
        from geofabric.registry import Registry

        mock_factory = MagicMock(return_value="sink_instance")
        registry = Registry(sources={}, engines={}, sinks={"test": mock_factory})
        result = registry.get_sink("test")
        assert result == "sink_instance"
        mock_factory.assert_called_once()

    def test_get_source_factory_success(self) -> None:
        """Test get_source_factory returns factory."""
        from geofabric.registry import Registry

        mock_factory = MagicMock()
        registry = Registry(sources={"test": mock_factory}, engines={}, sinks={})
        result = registry.get_source_factory("test")
        assert result == mock_factory
