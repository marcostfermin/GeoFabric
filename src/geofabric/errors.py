"""GeoFabric error hierarchy.

This module defines a comprehensive error hierarchy following these principles:

1. **Single Responsibility**: Each error type represents one failure category
2. **Liskov Substitution**: Subclasses can substitute for their parents
3. **Error Specificity**: More specific errors extend generic ones
4. **Recoverability**: Some errors are marked as potentially recoverable

Error Categories:
- Configuration errors: InvalidURIError, ConfigurationError
- Runtime errors: EngineError, SourceError, SinkError
- External failures: NetworkError, ExternalToolError
- Validation errors: ValidationError, GeometryError
- Security errors: SecurityError, SQLInjectionError

Usage:
    try:
        result = some_operation()
    except NetworkError:
        # Retry logic for transient failures
    except ValidationError:
        # User input error, provide feedback
    except GeoFabricError:
        # Catch-all for library errors
"""

from __future__ import annotations

import re

__all__ = [
    # Base
    "GeoFabricError",
    # Configuration
    "ConfigurationError",
    "InvalidURIError",
    # Engine/Query
    "EngineError",
    "QueryError",
    "ExtensionError",
    # Source/Sink
    "SourceError",
    "SinkError",
    # External
    "ExternalToolError",
    "MissingDependencyError",
    "NetworkError",
    # Validation
    "ValidationError",
    "GeometryError",
    "SchemaError",
    # Registry
    "NotFoundError",
    # Security
    "SecurityError",
    "SQLInjectionError",
]


class GeoFabricError(Exception):
    """Base error for GeoFabric.

    All GeoFabric-specific exceptions inherit from this class,
    allowing callers to catch all library errors with a single handler.

    Attributes:
        message: Human-readable error description
        recoverable: Hint whether retry might help (default False)
    """

    def __init__(self, message: str, *, recoverable: bool = False) -> None:
        super().__init__(message)
        self.message = message
        self.recoverable = recoverable

    def __str__(self) -> str:
        return self.message


# ============================================================================
# Configuration Errors
# ============================================================================


class ConfigurationError(GeoFabricError):
    """Raised when configuration is invalid or missing.

    This includes missing required settings, invalid option values,
    or conflicting configuration options.
    """

    pass


class InvalidURIError(ConfigurationError):
    """Raised when a URI cannot be parsed or is unsupported.

    This is raised during URI parsing when the format is wrong,
    the scheme is unsupported, or required components are missing.

    Attributes:
        uri: The invalid URI that caused the error (if provided)
        scheme: The URI scheme that was problematic (if applicable)
    """

    def __init__(
        self,
        message: str,
        *,
        uri: str | None = None,
        scheme: str | None = None,
    ) -> None:
        super().__init__(message)
        self.uri = uri
        self.scheme = scheme


# ============================================================================
# Engine/Query Errors
# ============================================================================


class EngineError(GeoFabricError):
    """Raised for engine-related failures.

    This includes connection failures, query execution errors,
    and internal engine errors.
    """

    pass


class QueryError(EngineError):
    """Raised when a SQL query fails to execute.

    Contains the original SQL for debugging purposes.
    SQL output is sanitized to remove credentials before display.
    """

    # Patterns for credential redaction in SQL strings
    _CREDENTIAL_PATTERNS = [
        # PostgreSQL password in connection strings
        (re.compile(r"password='[^']*'", re.IGNORECASE), "password='***'"),
        (re.compile(r"password=[^\s;]+", re.IGNORECASE), "password=***"),
        # S3 credentials in SET commands
        (re.compile(r"s3_secret_access_key='[^']*'", re.IGNORECASE), "s3_secret_access_key='***'"),
        (re.compile(r"s3_access_key_id='[^']*'", re.IGNORECASE), "s3_access_key_id='***'"),
        (re.compile(r"s3_session_token='[^']*'", re.IGNORECASE), "s3_session_token='***'"),
        # GCS credentials
        (re.compile(r"gcs_secret_access_key='[^']*'", re.IGNORECASE), "gcs_secret_access_key='***'"),
        (re.compile(r"gcs_access_key_id='[^']*'", re.IGNORECASE), "gcs_access_key_id='***'"),
        # Azure credentials
        (re.compile(r"azure_storage_connection_string='[^']*'", re.IGNORECASE), "azure_storage_connection_string='***'"),
        (re.compile(r"azure_account_key='[^']*'", re.IGNORECASE), "azure_account_key='***'"),
        (re.compile(r"SharedAccessSignature=[^;'\"]+", re.IGNORECASE), "SharedAccessSignature=***"),
        # Generic patterns for URLs with embedded credentials
        (re.compile(r"://[^:]+:[^@]+@"), "://***:***@"),
    ]

    def __init__(self, message: str, *, sql: str | None = None) -> None:
        super().__init__(message)
        self.sql = sql

    @classmethod
    def _sanitize_sql(cls, sql: str) -> str:
        """Remove credentials from SQL string for safe display.

        Args:
            sql: SQL string that may contain credentials

        Returns:
            SQL string with credentials redacted
        """
        result = sql
        for pattern, replacement in cls._CREDENTIAL_PATTERNS:
            result = pattern.sub(replacement, result)
        return result

    def __str__(self) -> str:
        if self.sql:
            # Sanitize SQL to remove credentials before display
            sanitized_sql = self._sanitize_sql(self.sql)
            # Truncate long SQL for readability
            sql_preview = sanitized_sql[:200] + "..." if len(sanitized_sql) > 200 else sanitized_sql
            return f"{self.message}\n\nSQL: {sql_preview}"
        return self.message


class ExtensionError(EngineError):
    """Raised when a database extension cannot be loaded.

    Common causes: network issues downloading extensions,
    missing dependencies, or platform incompatibility.
    """

    def __init__(self, extension: str, message: str) -> None:
        super().__init__(message, recoverable=True)
        self.extension = extension


# ============================================================================
# Source/Sink Errors
# ============================================================================


class SourceError(GeoFabricError):
    """Raised when a data source operation fails.

    This includes connection failures, authentication errors,
    and data access issues.
    """

    pass


class SinkError(GeoFabricError):
    """Raised when a data sink operation fails.

    This includes write failures, permission errors,
    and format conversion issues.
    """

    pass


# ============================================================================
# External Errors
# ============================================================================


class MissingDependencyError(GeoFabricError):
    """Raised when an optional dependency is required but not installed.

    Provides installation instructions for the missing package.
    """

    def __init__(self, message: str, *, package: str | None = None) -> None:
        super().__init__(message)
        self.package = package


class ExternalToolError(GeoFabricError):
    """Raised when an external tool invocation fails.

    This includes subprocess failures, missing executables,
    and tool-specific errors (e.g., tippecanoe, ogr2ogr).
    """

    def __init__(
        self,
        message: str,
        *,
        tool: str | None = None,
        exit_code: int | None = None,
        stderr: str | None = None,
    ) -> None:
        super().__init__(message)
        self.tool = tool
        self.exit_code = exit_code
        self.stderr = stderr


class NetworkError(GeoFabricError):
    """Raised for network-related failures (transient, may be retried).

    This error is marked as recoverable since network issues
    are often transient.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message, recoverable=True)


# ============================================================================
# Validation Errors
# ============================================================================


class ValidationError(GeoFabricError):
    """Raised when data validation fails.

    This includes schema validation, constraint violations,
    and data type mismatches.
    """

    pass


class GeometryError(ValidationError):
    """Raised for geometry-related errors.

    This includes invalid geometries, unsupported geometry types,
    and coordinate system issues.
    """

    pass


class SchemaError(ValidationError):
    """Raised when data schema doesn't match expectations.

    This includes missing columns, wrong data types,
    and incompatible schemas during operations.
    """

    def __init__(
        self,
        message: str,
        *,
        expected: list[str] | None = None,
        actual: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.expected = expected
        self.actual = actual


# ============================================================================
# Security Errors
# ============================================================================


class SecurityError(GeoFabricError):
    """Raised for security-related issues.

    This is the base class for security errors that should
    be treated with extra caution in logging and error handling.
    """

    pass


class SQLInjectionError(SecurityError):
    """Raised when potential SQL injection is detected.

    This error is raised when user input contains patterns
    that could be used for SQL injection attacks.
    """

    pass


# ============================================================================
# Registry Errors
# ============================================================================


class NotFoundError(GeoFabricError):
    """Raised when a required component or resource is not found.

    This includes missing sources, sinks, engines, or other
    registered components.

    Attributes:
        component_type: Type of component that was not found (e.g., 'source', 'sink')
        component_name: Name of the missing component
    """

    def __init__(
        self,
        message: str,
        *,
        component_type: str | None = None,
        component_name: str | None = None,
    ) -> None:
        super().__init__(message)
        self.component_type = component_type
        self.component_name = component_name
