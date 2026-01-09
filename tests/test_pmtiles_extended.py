"""Extended tests for PMTiles sink module."""

from __future__ import annotations

import tempfile
from unittest.mock import MagicMock, patch

import pytest


class TestPMTilesSink:
    """Tests for PMTilesSink class."""

    def test_pmtiles_sink_write(self) -> None:
        """Test PMTilesSink.write method."""
        from geofabric.sinks.pmtiles import PMTilesSink

        sink = PMTilesSink()
        mock_engine = MagicMock()

        with patch("geofabric.sinks.pmtiles.geoquery_to_pmtiles") as mock_geoquery:
            mock_geoquery.return_value = "/tmp/output.pmtiles"

            result = sink.write(
                engine=mock_engine,
                sql="SELECT * FROM test",
                out_path="/tmp/output.pmtiles",
                options={"layer": "test_layer", "maxzoom": 12, "minzoom": 2},
            )

            assert result == "/tmp/output.pmtiles"
            mock_geoquery.assert_called_once_with(
                engine=mock_engine,
                sql="SELECT * FROM test",
                pmtiles_path="/tmp/output.pmtiles",
                layer="test_layer",
                maxzoom=12,
                minzoom=2,
                geometry_col="geometry",
            )

    def test_pmtiles_sink_write_defaults(self) -> None:
        """Test PMTilesSink.write with default options."""
        from geofabric.sinks.pmtiles import PMTilesSink

        sink = PMTilesSink()
        mock_engine = MagicMock()

        with patch("geofabric.sinks.pmtiles.geoquery_to_pmtiles") as mock_geoquery:
            mock_geoquery.return_value = "/tmp/output.pmtiles"

            sink.write(
                engine=mock_engine,
                sql="SELECT * FROM test",
                out_path="/tmp/output.pmtiles",
                options={},
            )

            # Check default values
            call_kwargs = mock_geoquery.call_args[1]
            assert call_kwargs["layer"] == "features"
            assert call_kwargs["maxzoom"] == 14
            assert call_kwargs["minzoom"] == 0
            assert call_kwargs["geometry_col"] == "geometry"

    def test_pmtiles_sink_write_custom_geometry_col(self) -> None:
        """Test PMTilesSink.write with custom geometry column."""
        from geofabric.sinks.pmtiles import PMTilesSink

        sink = PMTilesSink()
        mock_engine = MagicMock()

        with patch("geofabric.sinks.pmtiles.geoquery_to_pmtiles") as mock_geoquery:
            mock_geoquery.return_value = "/tmp/output.pmtiles"

            sink.write(
                engine=mock_engine,
                sql="SELECT * FROM test",
                out_path="/tmp/output.pmtiles",
                options={"geometry_col": "geom"},
            )

            call_kwargs = mock_geoquery.call_args[1]
            assert call_kwargs["geometry_col"] == "geom"


class TestGeoQueryToPMTiles:
    """Tests for geoquery_to_pmtiles function."""

    def test_geoquery_to_pmtiles(self) -> None:
        """Test geoquery_to_pmtiles function."""
        from geofabric.sinks.pmtiles import geoquery_to_pmtiles

        mock_engine = MagicMock()

        with patch("geofabric.sinks.pmtiles.shutil.which", return_value="/usr/bin/tippecanoe"):
            with patch("geofabric.sinks.pmtiles.ensure_dir"):
                with patch("geofabric.sinks.pmtiles.run_cmd") as mock_run_cmd:
                    with tempfile.TemporaryDirectory() as td:
                        output_path = f"{td}/output.pmtiles"

                        result = geoquery_to_pmtiles(
                            engine=mock_engine,
                            sql="SELECT * FROM test",
                            pmtiles_path=output_path,
                            layer="test_layer",
                            maxzoom=14,
                            minzoom=0,
                        )

                        # Verify tippecanoe was called
                        mock_run_cmd.assert_called_once()
                        call_args = mock_run_cmd.call_args[0][0]
                        assert call_args[0] == "tippecanoe"
                        assert "-o" in call_args
                        assert "-l" in call_args
                        assert "test_layer" in call_args

    def test_geoquery_to_pmtiles_missing_tippecanoe(self) -> None:
        """Test that geoquery_to_pmtiles raises error when tippecanoe is missing."""
        from geofabric.errors import MissingDependencyError
        from geofabric.sinks.pmtiles import geoquery_to_pmtiles

        mock_engine = MagicMock()

        with patch("geofabric.sinks.pmtiles.shutil.which", return_value=None):
            with pytest.raises(MissingDependencyError, match="tippecanoe"):
                geoquery_to_pmtiles(
                    engine=mock_engine,
                    sql="SELECT * FROM test",
                    pmtiles_path="/tmp/output.pmtiles",
                    layer="test_layer",
                    maxzoom=14,
                    minzoom=0,
                )


class TestPMTilesSinkFactory:
    """Tests for PMTilesSinkFactory."""

    def test_factory_returns_instance(self) -> None:
        """Test factory returns PMTilesSink instance."""
        from geofabric.sinks.pmtiles import PMTilesSink, PMTilesSinkFactory

        # Factory is now an instance of SinkClassFactory
        sink = PMTilesSinkFactory()
        assert isinstance(sink, PMTilesSink)
