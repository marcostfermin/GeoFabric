"""Extended tests for Overture source module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestOvertureSourceFromURI:
    """Tests for OvertureSource.from_uri method."""

    def test_overture_source_from_uri_basic(self) -> None:
        """Test basic overture URI parsing."""
        from geofabric.sources.overture import OvertureSource

        src = OvertureSource.from_uri(
            "overture://?release=2025-01-01.0&theme=places&type=place"
        )
        assert src.release == "2025-01-01.0"
        assert src.theme == "places"
        assert src.type_ == "place"

    def test_overture_source_from_uri_with_netloc(self) -> None:
        """Test overture URI with query in netloc position."""
        from geofabric.sources.overture import OvertureSource

        src = OvertureSource.from_uri(
            "overture://release=2025-01-01.0&theme=base&type=infrastructure"
        )
        assert src.release == "2025-01-01.0"
        assert src.theme == "base"
        assert src.type_ == "infrastructure"

    def test_overture_source_from_uri_invalid_scheme(self) -> None:
        """Test overture URI with invalid scheme raises error."""
        from geofabric.errors import InvalidURIError
        from geofabric.sources.overture import OvertureSource

        with pytest.raises(InvalidURIError, match="Not an overture URI"):
            OvertureSource.from_uri("http://example.com")

    def test_overture_source_from_uri_missing_release(self) -> None:
        """Test overture URI missing release parameter."""
        from geofabric.errors import InvalidURIError
        from geofabric.sources.overture import OvertureSource

        with pytest.raises(InvalidURIError, match="Missing 'release'"):
            OvertureSource.from_uri("overture://?theme=places&type=place")

    def test_overture_source_from_uri_missing_theme(self) -> None:
        """Test overture URI missing theme parameter."""
        from geofabric.errors import InvalidURIError
        from geofabric.sources.overture import OvertureSource

        with pytest.raises(InvalidURIError, match="Missing 'theme'"):
            OvertureSource.from_uri("overture://?release=2025-01-01.0&type=place")

    def test_overture_source_from_uri_missing_type(self) -> None:
        """Test overture URI missing type parameter."""
        from geofabric.errors import InvalidURIError
        from geofabric.sources.overture import OvertureSource

        with pytest.raises(InvalidURIError, match="Missing 'type'"):
            OvertureSource.from_uri("overture://?release=2025-01-01.0&theme=places")


class TestOvertureSourceS3Prefix:
    """Tests for OvertureSource.s3_prefix method."""

    def test_s3_prefix(self) -> None:
        """Test s3_prefix returns correct path."""
        from geofabric.sources.overture import OvertureSource

        src = OvertureSource(
            release="2025-01-01.0",
            theme="places",
            type_="place",
        )
        expected = "s3://overturemaps-us-west-2/release/2025-01-01.0/theme=places/type=place/"
        assert src.s3_prefix() == expected


class TestOvertureClass:
    """Tests for Overture helper class."""

    def test_overture_source(self) -> None:
        """Test Overture.source returns OvertureSource."""
        from geofabric.sources.overture import Overture, OvertureSource

        ov = Overture(release="2025-01-01.0", theme="places", type_="place")
        src = ov.source()
        assert isinstance(src, OvertureSource)
        assert src.release == "2025-01-01.0"

    def test_overture_download(self) -> None:
        """Test Overture.download calls aws cli."""
        from geofabric.sources.overture import Overture

        ov = Overture(release="2025-01-01.0", theme="places", type_="place")

        with patch("geofabric.sources.overture.shutil.which", return_value="/usr/bin/aws"):
            with patch("geofabric.sources.overture.ensure_dir") as mock_ensure_dir:
                with patch("geofabric.sources.overture.run_cmd") as mock_run_cmd:
                    mock_ensure_dir.return_value = "/tmp/dest"

                    result = ov.download("/tmp/dest")

                    assert result == "/tmp/dest"
                    mock_ensure_dir.assert_called_once_with("/tmp/dest")
                    mock_run_cmd.assert_called_once()
                    # Verify aws s3 cp command was called
                    call_args = mock_run_cmd.call_args[0][0]
                    assert call_args[0] == "aws"
                    assert call_args[1] == "s3"
                    assert call_args[2] == "cp"

    def test_overture_download_missing_aws_cli(self) -> None:
        """Test that download raises error when AWS CLI is not installed."""
        from geofabric.errors import MissingDependencyError
        from geofabric.sources.overture import Overture

        ov = Overture(release="2025-01-01.0", theme="places", type_="place")

        with patch("geofabric.sources.overture.shutil.which", return_value=None):
            with pytest.raises(MissingDependencyError, match="AWS CLI"):
                ov.download("/tmp/dest")


class TestOvertureSourceFactory:
    """Tests for OvertureSourceFactory."""

    def test_factory_returns_class(self) -> None:
        """Test factory returns OvertureSource class."""
        from geofabric.sources.overture import OvertureSource, OvertureSourceFactory

        # Factory is now an instance of SourceClassFactory
        assert OvertureSourceFactory() is OvertureSource
