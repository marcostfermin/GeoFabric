# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it by:

1. **Do NOT** open a public issue
2. Send a private email to the maintainers with:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Any suggested fixes

We will respond within 48 hours and work with you to:
- Confirm the vulnerability
- Develop a fix
- Coordinate disclosure

## Security Best Practices

When using GeoFabric:

- **SQL Injection**: User inputs in `where()` clauses are passed directly to DuckDB. Always validate and sanitize user inputs before using them in queries.
- **File Access**: The `file://` URI scheme accesses local files. Ensure proper access controls on your filesystem.
- **Cloud Credentials**: When using S3 or GCS sources, credentials are handled by the respective SDKs. Follow cloud provider security best practices.
- **PostGIS Connections**: Database credentials should be stored securely (environment variables, secrets managers) rather than hardcoded.

Thank you for helping keep GeoFabric secure!
