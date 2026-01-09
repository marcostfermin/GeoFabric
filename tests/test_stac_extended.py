"""Extended tests for STAC source module."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from geofabric.errors import InvalidURIError


class TestSTACSourceFromURI:
    """Tests for STACSource.from_uri method."""

    def test_stac_source_from_uri_basic(self) -> None:
        """Test basic STAC URI parsing."""
        from geofabric.sources.stac import STACSource

        src = STACSource.from_uri("stac://example.com/api/stac?collection=test")
        assert src.catalog_url == "https://example.com/api/stac"
        assert src.collection == "test"
        assert src.asset_key == "data"  # default

    def test_stac_source_from_uri_with_bbox(self) -> None:
        """Test STAC URI with bbox parameter."""
        from geofabric.sources.stac import STACSource

        src = STACSource.from_uri(
            "stac://example.com/stac?collection=test&bbox=-122.5,37.5,-122.0,38.0"
        )
        assert src.bbox == (-122.5, 37.5, -122.0, 38.0)

    def test_stac_source_from_uri_with_datetime(self) -> None:
        """Test STAC URI with datetime parameter."""
        from geofabric.sources.stac import STACSource

        src = STACSource.from_uri(
            "stac://example.com/stac?collection=test&datetime=2024-01-01/2024-12-31"
        )
        assert src.datetime == "2024-01-01/2024-12-31"

    def test_stac_source_from_uri_with_asset(self) -> None:
        """Test STAC URI with custom asset key."""
        from geofabric.sources.stac import STACSource

        src = STACSource.from_uri(
            "stac://example.com/stac?collection=test&asset=visual"
        )
        assert src.asset_key == "visual"

    def test_stac_source_from_uri_invalid_scheme(self) -> None:
        """Test STAC URI with invalid scheme raises error."""
        from geofabric.errors import InvalidURIError
        from geofabric.sources.stac import STACSource

        with pytest.raises(InvalidURIError, match="Not a STAC URI"):
            STACSource.from_uri("http://example.com/stac")

    def test_stac_source_from_uri_incomplete_bbox(self) -> None:
        """Test STAC URI with incomplete bbox (not 4 parts) raises error."""
        from geofabric.sources.stac import STACSource

        # Only 3 parts - should raise an error
        with pytest.raises(InvalidURIError, match="must have 4 values"):
            STACSource.from_uri(
                "stac://example.com/stac?collection=test&bbox=-122.5,37.5,-122.0"
            )

    def test_stac_source_from_uri_all_params(self) -> None:
        """Test STAC URI with all parameters."""
        from geofabric.sources.stac import STACSource

        src = STACSource.from_uri(
            "stac://earth-search.aws.element84.com/v1"
            "?collection=sentinel-2-l2a"
            "&asset=visual"
            "&bbox=-122.5,37.5,-122.0,38.0"
            "&datetime=2024-01-01/2024-06-01"
        )
        assert src.catalog_url == "https://earth-search.aws.element84.com/v1"
        assert src.collection == "sentinel-2-l2a"
        assert src.asset_key == "visual"
        assert src.bbox == (-122.5, 37.5, -122.0, 38.0)
        assert src.datetime == "2024-01-01/2024-06-01"


class TestSTACSourceSearchItemsAdvanced:
    """Advanced tests for STACSource.search_items method."""

    def test_search_items_with_bbox(self) -> None:
        """Test search_items with bbox filter."""
        from geofabric.sources.stac import STACSource

        src = STACSource(
            catalog_url="https://example.com/stac",
            collection="test",
            bbox=(-122.5, 37.5, -122.0, 38.0),
        )

        mock_pystac_client = MagicMock()
        mock_client_class = MagicMock()
        mock_search = MagicMock()
        mock_item = MagicMock()
        mock_item.assets = {"data": MagicMock(href="https://example.com/data.tif")}
        mock_search.items.return_value = [mock_item]
        mock_client_class.open.return_value.search.return_value = mock_search
        mock_pystac_client.Client = mock_client_class

        with patch.dict(sys.modules, {"pystac_client": mock_pystac_client}):
            items = src.search_items()
            assert len(items) == 1
            # Verify bbox was passed
            call_kwargs = mock_client_class.open.return_value.search.call_args[1]
            assert call_kwargs["bbox"] == (-122.5, 37.5, -122.0, 38.0)

    def test_search_items_with_datetime(self) -> None:
        """Test search_items with datetime filter."""
        from geofabric.sources.stac import STACSource

        src = STACSource(
            catalog_url="https://example.com/stac",
            collection="test",
            datetime="2024-01-01/2024-12-31",
        )

        mock_pystac_client = MagicMock()
        mock_client_class = MagicMock()
        mock_search = MagicMock()
        mock_item = MagicMock()
        mock_item.assets = {"data": MagicMock(href="https://example.com/data.tif")}
        mock_search.items.return_value = [mock_item]
        mock_client_class.open.return_value.search.return_value = mock_search
        mock_pystac_client.Client = mock_client_class

        with patch.dict(sys.modules, {"pystac_client": mock_pystac_client}):
            items = src.search_items()
            call_kwargs = mock_client_class.open.return_value.search.call_args[1]
            assert call_kwargs["datetime"] == "2024-01-01/2024-12-31"

    def test_search_items_missing_asset(self) -> None:
        """Test search_items when item doesn't have the requested asset."""
        from geofabric.sources.stac import STACSource

        src = STACSource(
            catalog_url="https://example.com/stac",
            collection="test",
            asset_key="missing_asset",
        )

        mock_pystac_client = MagicMock()
        mock_client_class = MagicMock()
        mock_search = MagicMock()
        mock_item = MagicMock()
        mock_item.assets = {"other_asset": MagicMock(href="https://example.com/data.tif")}
        mock_search.items.return_value = [mock_item]
        mock_client_class.open.return_value.search.return_value = mock_search
        mock_pystac_client.Client = mock_client_class

        with patch.dict(sys.modules, {"pystac_client": mock_pystac_client}):
            items = src.search_items()
            # Item should be skipped since asset_key doesn't exist
            assert len(items) == 0


class TestSTACSourceKind:
    """Tests for STACSource.source_kind method."""

    def test_source_kind(self) -> None:
        """Test source_kind returns 'stac'."""
        from geofabric.sources.stac import STACSource

        src = STACSource(catalog_url="https://example.com/stac")
        assert src.source_kind() == "stac"
