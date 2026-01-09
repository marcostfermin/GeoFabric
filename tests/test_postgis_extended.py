"""Extended tests for PostGIS source module."""

from __future__ import annotations

import pytest


class TestPostGISSourceFromURI:
    """Tests for PostGISSource.from_uri method."""

    def test_postgis_source_from_uri_postgres_scheme(self) -> None:
        """Test from_uri with postgres:// scheme."""
        from geofabric.sources.postgis import PostGISSource

        src = PostGISSource.from_uri(
            "postgres://user:pass@localhost:5432/mydb?table=mytable"
        )
        assert src.host == "localhost"
        assert src.port == 5432

    def test_postgis_source_from_uri_postgis_scheme(self) -> None:
        """Test from_uri with postgis:// scheme."""
        from geofabric.sources.postgis import PostGISSource

        src = PostGISSource.from_uri(
            "postgis://user:pass@localhost:5432/mydb?table=mytable"
        )
        assert src.host == "localhost"

    def test_postgis_source_from_uri_default_port(self) -> None:
        """Test from_uri uses default port 5432 if not specified."""
        from geofabric.sources.postgis import PostGISSource

        src = PostGISSource.from_uri("postgresql://user:pass@localhost/mydb?table=mytable")
        assert src.port == 5432

    def test_postgis_source_from_uri_custom_schema(self) -> None:
        """Test from_uri with custom schema."""
        from geofabric.sources.postgis import PostGISSource

        src = PostGISSource.from_uri(
            "postgresql://user:pass@localhost/mydb?table=mytable&schema=custom"
        )
        assert src.schema == "custom"

    def test_postgis_source_from_uri_custom_geometry_column(self) -> None:
        """Test from_uri with custom geometry column."""
        from geofabric.sources.postgis import PostGISSource

        src = PostGISSource.from_uri(
            "postgresql://user:pass@localhost/mydb?table=mytable&geometry_column=the_geom"
        )
        assert src.geometry_column == "the_geom"

    def test_postgis_source_from_uri_missing_host(self) -> None:
        """Test from_uri with missing host raises error."""
        from geofabric.errors import InvalidURIError
        from geofabric.sources.postgis import PostGISSource

        with pytest.raises(InvalidURIError, match="Missing host"):
            PostGISSource.from_uri("postgresql:///mydb?table=mytable")

    def test_postgis_source_from_uri_missing_database(self) -> None:
        """Test from_uri with missing database raises error."""
        from geofabric.errors import InvalidURIError
        from geofabric.sources.postgis import PostGISSource

        with pytest.raises(InvalidURIError, match="Missing database"):
            PostGISSource.from_uri("postgresql://user:pass@localhost/?table=mytable")

    def test_postgis_source_from_uri_empty_credentials(self) -> None:
        """Test from_uri with empty username/password."""
        from geofabric.sources.postgis import PostGISSource

        src = PostGISSource.from_uri("postgresql://localhost/mydb?table=mytable")
        assert src.user == ""
        assert src.password == ""


class TestPostGISSourceQualifiedTableName:
    """Tests for PostGISSource.qualified_table_name method."""

    def test_qualified_table_name(self) -> None:
        """Test qualified_table_name returns schema.table format."""
        from geofabric.sources.postgis import PostGISSource

        src = PostGISSource(
            host="localhost",
            port=5432,
            database="test",
            user="user",
            password="pass",
            table="mytable",
            schema="myschema",
        )
        assert src.qualified_table_name() == "myschema.mytable"

    def test_qualified_table_name_public_schema(self) -> None:
        """Test qualified_table_name with default public schema."""
        from geofabric.sources.postgis import PostGISSource

        src = PostGISSource(
            host="localhost",
            port=5432,
            database="test",
            user="user",
            password="pass",
            table="mytable",
        )
        assert src.qualified_table_name() == "public.mytable"


class TestPostGISSourceConnectionString:
    """Tests for PostGISSource.connection_string method."""

    def test_connection_string_format(self) -> None:
        """Test connection_string returns postgresql:// format."""
        from geofabric.sources.postgis import PostGISSource

        src = PostGISSource(
            host="db.example.com",
            port=5433,
            database="mydb",
            user="admin",
            password="secret123",
            table="data",
        )
        conn_str = src.connection_string()
        assert conn_str == "postgresql://admin:secret123@db.example.com:5433/mydb"


class TestPostGISSourceSourceKind:
    """Tests for PostGISSource.source_kind method."""

    def test_source_kind(self) -> None:
        """Test source_kind returns 'postgis'."""
        from geofabric.sources.postgis import PostGISSource

        src = PostGISSource(
            host="localhost",
            port=5432,
            database="test",
            user="user",
            password="pass",
            table="mytable",
        )
        assert src.source_kind() == "postgis"
