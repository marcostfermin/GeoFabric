from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

from geofabric.errors import EngineError, InvalidURIError, MissingDependencyError
from geofabric.util import ensure_dir, run_cmd

# Pattern for valid Overture identifiers (release, theme, type)
# Alphanumeric, dots, hyphens, underscores only - prevents argument injection
_VALID_IDENTIFIER_PATTERN = re.compile(r"^[a-zA-Z0-9._-]+$")


def _validate_overture_identifier(value: str, field_name: str) -> str:
    """Validate Overture identifier to prevent argument injection.

    Args:
        value: The identifier value to validate
        field_name: Name of the field for error messages

    Returns:
        The validated value

    Raises:
        InvalidURIError: If the value contains invalid characters
    """
    if not value:
        raise InvalidURIError(f"Overture {field_name} cannot be empty")
    if not _VALID_IDENTIFIER_PATTERN.match(value):
        raise InvalidURIError(
            f"Overture {field_name} contains invalid characters: {value!r}. "
            "Only alphanumeric, dots, hyphens, and underscores are allowed."
        )
    # Prevent values that look like CLI flags
    if value.startswith("-"):
        raise InvalidURIError(
            f"Overture {field_name} cannot start with '-': {value!r}"
        )
    return value


@dataclass(frozen=True)
class OvertureSource:
    """Source specification for Overture Maps data.

    OvertureSource is a virtual specification - it describes what data
    you want but cannot be queried directly. You must download the data
    first using the Overture helper class.

    Example:
        >>> overture = Overture(release="2024-01-17-alpha.0", theme="buildings", type_="building")
        >>> dest = overture.download("/tmp/overture_buildings")
        >>> # Now open the downloaded data with geofabric.open(dest)
    """

    release: str
    theme: str
    type_: str

    def __post_init__(self) -> None:
        """Validate Overture source parameters to prevent argument injection."""
        _validate_overture_identifier(self.release, "release")
        _validate_overture_identifier(self.theme, "theme")
        _validate_overture_identifier(self.type_, "type")

    def source_kind(self) -> str:
        return "overture"

    def to_duckdb_relation_sql(self, engine: object) -> str:
        """OvertureSource cannot be queried directly - download first.

        Implements SourceWithDuckDBRelation protocol but always raises
        an error with instructions, following the Open/Closed Principle.

        Raises:
            EngineError: Always - OvertureSource must be downloaded first
        """
        raise EngineError(
            "OvertureSource is a virtual specification that cannot be queried directly. "
            "Download the data first using:\n\n"
            "  from geofabric.sources.overture import Overture\n"
            f"  overture = Overture(release='{self.release}', theme='{self.theme}', type_='{self.type_}')\n"
            "  dest = overture.download('/path/to/destination')\n"
            "  dataset = geofabric.open(dest)\n"
        )

    @staticmethod
    def from_uri(uri: str) -> OvertureSource:
        parsed = urlparse(uri)
        if parsed.scheme != "overture":
            raise InvalidURIError(f"Not an overture URI: {uri}")

        query = parsed.query
        if parsed.netloc and not query:
            query = parsed.netloc

        qs = parse_qs(query)

        def one(key: str) -> str:
            v = qs.get(key)
            if not v or not v[0]:
                raise InvalidURIError(f"Missing '{key}' in overture URI: {uri}")
            return v[0]

        return OvertureSource(
            release=one("release"),
            theme=one("theme"),
            type_=one("type"),
        )

    def s3_prefix(self) -> str:
        # Public Overture AWS bucket prefix convention
        return f"s3://overturemaps-us-west-2/release/{self.release}/theme={self.theme}/type={self.type_}/"


@dataclass
class Overture:
    """Helper class for downloading Overture Maps data."""

    release: str
    theme: str
    type_: str

    def __post_init__(self) -> None:
        """Validate Overture parameters to prevent argument injection."""
        _validate_overture_identifier(self.release, "release")
        _validate_overture_identifier(self.theme, "theme")
        _validate_overture_identifier(self.type_, "type")

    def source(self) -> OvertureSource:
        return OvertureSource(release=self.release, theme=self.theme, type_=self.type_)

    def download(self, dest: str) -> str:
        """Download Overture data to destination directory.

        Args:
            dest: Destination directory path

        Returns:
            Path to the destination directory

        Raises:
            MissingDependencyError: If AWS CLI is not installed
        """
        # Check for AWS CLI before doing any work
        if shutil.which("aws") is None:
            raise MissingDependencyError(
                "AWS CLI is required for Overture downloads but was not found in PATH. "
                "Install from: https://aws.amazon.com/cli/"
            )

        dest_dir = ensure_dir(dest)
        prefix = self.source().s3_prefix()
        run_cmd(
            ["aws", "s3", "cp", "--no-sign-request", "--recursive", prefix, dest_dir], check=True
        )
        return dest_dir


from geofabric.registry import SourceClassFactory

# Use generic factory instead of boilerplate class
OvertureSourceFactory = SourceClassFactory(OvertureSource)
