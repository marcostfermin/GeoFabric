# Authentication Guide

GeoFabric connects to external data sources using standard authentication methods. This guide explains how to configure credentials for each service.

## How Authentication Works

GeoFabric supports **two methods** for configuring credentials, following industry best practices (similar to boto3, Google Cloud SDK):

| Method | When to Use | Priority |
|--------|-------------|----------|
| **Programmatic** (`gf.configure_s3()`) | Scripts, testing, explicit control | Highest |
| **Environment Variables** | Production, CI/CD, containers | Default |

Programmatic configuration takes precedence over environment variables.

---

## Method 1: Programmatic Configuration (Recommended for Scripts)

Configure credentials directly in your Python code using GeoFabric's configuration API:

### S3 Configuration

```python
import geofabric as gf

# Configure S3 credentials programmatically
gf.configure_s3(
    access_key_id="AKIA...",
    secret_access_key="your-secret-key",
    region="us-east-1",
    # Optional:
    session_token="...",  # For temporary credentials (STS)
    endpoint="...",       # For S3-compatible services (MinIO, etc.)
)

# Now use gf.open() - credentials are applied automatically
ds = gf.open("s3://my-private-bucket/data.parquet?anonymous=false")
```

### GCS Configuration

```python
import geofabric as gf

# Configure GCS credentials programmatically
gf.configure_gcs(
    access_key_id="GOOG...",
    secret_access_key="your-secret-key",
)

ds = gf.open("gs://my-bucket/data.parquet")
```

### PostGIS Configuration

```python
import geofabric as gf

# Configure default PostGIS connection parameters
gf.configure_postgis(
    host="db.example.com",
    port=5432,
    user="myuser",
    password="mypassword",
    sslmode="require",  # Optional: disable, allow, prefer, require, verify-ca, verify-full
)

# Now you can use shorter connection strings
ds = gf.open("postgresql:///mydb?table=public.parcels")
```

### Azure Blob Storage Configuration

```python
import geofabric as gf

# Option 1: Account name and key
gf.configure_azure(
    account_name="mystorageaccount",
    account_key="your-account-key",
)

# Option 2: Connection string
gf.configure_azure(
    connection_string="DefaultEndpointsProtocol=https;AccountName=...;AccountKey=..."
)

# Option 3: SAS token
gf.configure_azure(
    account_name="mystorageaccount",
    sas_token="sv=2021-06-08&ss=b&srt=sco..."
)

ds = gf.open("az://container/data.parquet")
```

### STAC Catalog Configuration

```python
import geofabric as gf

# Configure STAC authentication
gf.configure_stac(
    api_key="your-api-key",  # For catalogs using X-API-Key header
    headers={                 # Custom headers
        "Authorization": "Bearer eyJ...",
        "X-Custom-Header": "value"
    },
    default_catalog="https://planetarycomputer.microsoft.com/api/stac/v1"
)

ds = gf.open("stac://catalog.example.com/collection")
```

### HTTP Configuration (Global)

```python
import geofabric as gf

# Configure global HTTP settings for all web requests
gf.configure_http(
    proxy="http://corporate-proxy:8080",  # HTTP proxy
    timeout=60,                            # Timeout in seconds
    headers={"User-Agent": "MyApp/1.0"},  # Custom headers
    verify_ssl=True,                       # SSL certificate verification
)
```

### Reset Configuration

```python
import geofabric as gf

# Clear all programmatic credentials (revert to env vars)
gf.reset_config()
```

### Complete Configuration Reference

| Function | Parameters | Description |
|----------|------------|-------------|
| `configure_s3()` | access_key_id, secret_access_key, region, session_token, endpoint, use_ssl | AWS S3 credentials |
| `configure_gcs()` | access_key_id, secret_access_key, project | Google Cloud Storage |
| `configure_azure()` | account_name, account_key, connection_string, sas_token | Azure Blob Storage |
| `configure_postgis()` | host, port, database, user, password, sslmode | PostgreSQL/PostGIS |
| `configure_stac()` | api_key, headers, default_catalog | STAC catalogs |
| `configure_http()` | proxy, timeout, headers, verify_ssl | Global HTTP settings |
| `reset_config()` | - | Clear all config |
| `get_config()` | - | Get current config |

### When to Use Programmatic Configuration

- **Scripts and notebooks**: Explicit control over credentials
- **Testing**: Easily switch between different credentials
- **Multi-account access**: Access multiple AWS accounts in same script
- **Secret managers**: Load credentials from Vault, AWS Secrets Manager, etc.

```python
import geofabric as gf
import boto3

# Example: Load credentials from AWS Secrets Manager
secrets = boto3.client('secretsmanager')
creds = secrets.get_secret_value(SecretId='my-s3-creds')

gf.configure_s3(
    access_key_id=creds['AccessKeyId'],
    secret_access_key=creds['SecretAccessKey'],
)
```

---

## Method 2: Environment Variables (Recommended for Production)

Set credentials in your shell before running Python. GeoFabric automatically picks them up.

### How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: Set environment variables in your shell                 │
│                                                                 │
│   $ export AWS_ACCESS_KEY_ID="AKIA..."                         │
│   $ export AWS_SECRET_ACCESS_KEY="..."                         │
│                                                                 │
│   These are now stored in the shell's environment              │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 2: Start Python                                            │
│                                                                 │
│   $ python my_script.py                                        │
│                                                                 │
│   Python inherits ALL environment variables from the shell     │
│   (You can verify: import os; print(os.environ))               │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: GeoFabric loads httpfs                                  │
│                                                                 │
│   # GeoFabric runs this internally:                            │
│   INSTALL httpfs;                                              │
│   LOAD httpfs;                                                 │
│                                                                 │
│   httpfs (C++ code inside DuckDB) calls getenv() to read:      │
│   - AWS_ACCESS_KEY_ID                                          │
│   - AWS_SECRET_ACCESS_KEY                                      │
│   - AWS_DEFAULT_REGION                                         │
│   - AWS_SESSION_TOKEN (if present)                             │
└─────────────────────────────────────────────────────────────────┘
```

### Quick Start Example (Environment Variables)

```bash
# Step 1: Set environment variables (do this ONCE in your terminal)
export AWS_ACCESS_KEY_ID="AKIA..."
export AWS_SECRET_ACCESS_KEY="..."
export AWS_DEFAULT_REGION="us-east-1"

# Step 2: Run your Python script
python my_workflow.py
```

```python
# my_workflow.py
import geofabric as gf

# Credentials are picked up automatically from environment
buildings = gf.open("s3://my-company-data/buildings.parquet?anonymous=false")

result = (
    buildings.query()
    .within(gf.roi.bbox(-74.0, 40.7, -73.9, 40.8))
    .with_area()
)
result.to_parquet("output.parquet")
```

### When to Use Environment Variables

- **Production deployments**: Credentials managed by infrastructure
- **CI/CD pipelines**: Secrets injected by CI system
- **Containers**: Credentials passed via Docker/Kubernetes
- **Cloud VMs**: IAM roles provide credentials automatically

---

## Credential Precedence

GeoFabric checks credentials in this order (highest priority first):

1. **Programmatic configuration** (`gf.configure_s3(...)`)
2. **Environment variables** (`AWS_ACCESS_KEY_ID`, etc.)
3. **Credential files** (`~/.aws/credentials`)
4. **Instance metadata** (IAM roles on EC2/ECS/Lambda)

This matches the behavior of boto3 and other industry-standard libraries.

---

## What Happens Internally

When you call `gf.open("s3://...")`, GeoFabric:

1. **Creates a DuckDB connection** (in-memory database)
2. **Installs and loads httpfs** extension automatically
3. **Applies programmatic credentials** (if configured via `gf.configure_s3()`)
4. **Falls back to environment variables** (if no programmatic config)
5. **Executes the query** against the cloud storage

You don't need to manage DuckDB or httpfs directly - GeoFabric handles everything.

---

## Local Files

For local data, no authentication is needed. GeoFabric supports multiple ways to reference local files:

### Using `file://` URI Scheme

```python
import geofabric as gf

# Absolute path with file:// scheme
ds = gf.open("file:///home/user/data/parcels.parquet")

# On Windows
ds = gf.open("file:///C:/Users/user/data/parcels.parquet")
```

### Using Plain File Paths

```python
import geofabric as gf

# Absolute path (recommended)
ds = gf.open("/home/user/data/parcels.parquet")

# Relative path
ds = gf.open("./data/parcels.parquet")
ds = gf.open("data/parcels.parquet")

# Home directory expansion (~)
ds = gf.open("~/data/parcels.parquet")
```

### Supported Local Formats

GeoFabric automatically detects the format based on file extension:

| Format | Extensions | Example |
|--------|------------|---------|
| GeoParquet | `.parquet`, `.geoparquet` | `gf.open("data.parquet")` |
| GeoJSON | `.geojson`, `.json` | `gf.open("data.geojson")` |
| Shapefile | `.shp` | `gf.open("data.shp")` |
| GeoPackage | `.gpkg` | `gf.open("data.gpkg")` |
| FlatGeoBuf | `.fgb` | `gf.open("data.fgb")` |
| CSV (with geometry) | `.csv` | `gf.open("data.csv")` |

### Directory of Partitioned Files

For partitioned datasets (common with large GeoParquet files):

```python
import geofabric as gf

# Point to the directory containing partitioned parquet files
ds = gf.open("file:///data/buildings/")
# Or simply:
ds = gf.open("/data/buildings/")
```

---

## Amazon S3

GeoFabric uses DuckDB's **httpfs extension** to access S3. When you call `gf.open("s3://...")`, GeoFabric:

1. Loads the httpfs extension in DuckDB
2. httpfs automatically discovers credentials from your environment
3. Uses those credentials to authenticate with S3

Authentication follows the standard AWS credential chain (checked in order):

### Option 1: Environment Variables (Recommended for Development)

```bash
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_DEFAULT_REGION="us-east-1"

# Optional: for temporary credentials (STS)
export AWS_SESSION_TOKEN="your-session-token"
```

### Option 2: AWS Credentials File

Create or edit `~/.aws/credentials`:

```ini
[default]
aws_access_key_id = your-access-key
aws_secret_access_key = your-secret-key

[production]
aws_access_key_id = prod-access-key
aws_secret_access_key = prod-secret-key
```

Select a profile with:
```bash
export AWS_PROFILE="production"
```

### Option 3: AWS CLI Configuration

```bash
# Configure default profile
aws configure

# Configure named profile
aws configure --profile production
```

### Option 4: IAM Roles (Recommended for Production)

When running on AWS infrastructure (EC2, ECS, Lambda), use IAM roles:

1. Attach an IAM role to your EC2 instance/ECS task/Lambda function
2. The role should have S3 read permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::your-bucket",
                "arn:aws:s3:::your-bucket/*"
            ]
        }
    ]
}
```

No environment variables needed - credentials are automatic.

### Public S3 Buckets

For public buckets (like Overture Maps), no credentials are required:

```python
import geofabric as gf

# Public bucket - works without credentials
ds = gf.open("s3://overturemaps-us-west-2/release/2025-01-22.0/...")
```

### Private S3 Buckets

For private buckets, ensure your credentials are configured (see options above), then:

```python
import geofabric as gf

# Private bucket - uses credentials from environment
# Add ?anonymous=false to explicitly use authenticated access
ds = gf.open("s3://my-private-bucket/data.parquet?anonymous=false")

# Specify region if needed
ds = gf.open("s3://my-private-bucket/data.parquet?anonymous=false&region=us-west-2")
```

**Note**: By default, GeoFabric attempts anonymous access for S3 URIs. For private buckets, add `?anonymous=false` to force authenticated access using your configured credentials.

---

## Google Cloud Storage (GCS)

GeoFabric uses DuckDB's **httpfs extension** to access GCS. Similar to S3, httpfs automatically discovers credentials from your environment.

### Option 1: Application Default Credentials (Recommended)

```bash
# Login with your Google account
gcloud auth application-default login

# This creates credentials at:
# ~/.config/gcloud/application_default_credentials.json
```

### Option 2: Service Account Key File

1. Create a service account in Google Cloud Console
2. Download the JSON key file
3. Set the environment variable:

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
```

### Option 3: Environment Variables

```bash
export GCS_ACCESS_KEY_ID="your-access-key"
export GCS_SECRET_ACCESS_KEY="your-secret-key"
```

### Service Account Permissions

The service account needs these roles:
- `roles/storage.objectViewer` - Read objects
- `roles/storage.legacyBucketReader` - List bucket contents

Or the specific permissions:
- `storage.objects.get`
- `storage.objects.list`
- `storage.buckets.get`

### Public GCS Buckets

For public buckets, no credentials are required:

```python
import geofabric as gf

# Public bucket - works without credentials
ds = gf.open("gs://public-bucket/data.parquet")
```

---

## PostGIS / PostgreSQL

GeoFabric connects to PostGIS using standard PostgreSQL connection strings.

### Connection String Format

```
postgresql://username:password@host:port/database?table=schema.tablename
```

### Option 1: Connection String with Credentials

```python
import geofabric as gf

# Credentials in connection string
ds = gf.open(
    "postgresql://myuser:mypassword@db.example.com:5432/geodatabase?table=public.buildings"
)
```

### Option 2: Environment Variables (Recommended)

```bash
export PGUSER="myuser"
export PGPASSWORD="mypassword"
export PGHOST="db.example.com"
export PGPORT="5432"
export PGDATABASE="geodatabase"
```

Then use a simpler connection string:

```python
import geofabric as gf

# Uses environment variables for auth
ds = gf.open("postgresql:///geodatabase?table=public.buildings")
```

### Option 3: Password File (~/.pgpass)

Create `~/.pgpass` with restricted permissions:

```bash
# Format: hostname:port:database:username:password
db.example.com:5432:geodatabase:myuser:mypassword
```

```bash
chmod 600 ~/.pgpass
```

### Option 4: SSL/TLS Connection

For secure connections:

```python
import geofabric as gf

# With SSL
ds = gf.open(
    "postgresql://user:pass@host:5432/db?table=schema.table&sslmode=require"
)
```

SSL modes:
- `disable` - No SSL
- `allow` - Try SSL, fall back to non-SSL
- `prefer` - Try SSL first (default)
- `require` - Require SSL
- `verify-ca` - Require SSL + verify CA
- `verify-full` - Require SSL + verify CA + hostname

### Network Security

Ensure your database allows connections from your IP:

1. Configure `pg_hba.conf` on the PostgreSQL server
2. Open firewall port 5432
3. For cloud databases (RDS, Cloud SQL), configure security groups/firewall rules

---

## STAC Catalogs

STAC (SpatioTemporal Asset Catalog) APIs typically don't require authentication for public catalogs.

### Public STAC Catalogs

```python
import geofabric as gf

# Microsoft Planetary Computer (public)
ds = gf.open("stac://https://planetarycomputer.microsoft.com/api/stac/v1/collections/sentinel-2-l2a")

# AWS Earth Search (public)
ds = gf.open("stac://https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a")
```

### Authenticated STAC Catalogs

For private STAC catalogs, authentication varies by provider. Set environment variables as required:

```bash
# Example for a private catalog
export STAC_API_KEY="your-api-key"
```

---

## Overture Maps

Overture Maps data is hosted on public AWS S3 buckets and requires no authentication.

However, the download process uses the AWS CLI, which should be installed:

```bash
# Install AWS CLI
pip install awscli

# Or on macOS
brew install awscli

# No configuration needed for public Overture data
```

Usage:
```python
from geofabric.sources.overture import Overture

# No credentials needed
ov = Overture(release="2025-12-17.0", theme="buildings", type_="building")
local_path = ov.download("./data/overture/buildings")
```

---

## Best Practices

### 1. Never Commit Credentials

Add to `.gitignore`:
```
.env
*.pem
*credentials*
service-account*.json
```

### 2. Use Environment Variables

Create a `.env` file (not committed):
```bash
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
PGPASSWORD=xxx
GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
```

Load with:
```bash
source .env
# Or use python-dotenv
```

### 3. Use IAM Roles in Production

When running on cloud infrastructure:
- AWS: Use IAM instance roles
- GCP: Use service account attached to VM/container
- Avoid long-lived credentials

### 4. Principle of Least Privilege

Grant only the permissions needed:
- Read-only access for analysis workloads
- No delete permissions unless required
- Scope to specific buckets/tables

### 5. Rotate Credentials

- Rotate access keys regularly (90 days recommended)
- Use temporary credentials when possible (STS)
- Audit credential usage

---

## Troubleshooting

### AWS S3

```
Error: Access Denied
```
- Check credentials are set: `aws sts get-caller-identity`
- Verify bucket permissions
- Check bucket region matches your config

### GCS

```
Error: 403 Forbidden
```
- Check credentials: `gcloud auth application-default print-access-token`
- Verify service account permissions
- Check bucket IAM policy

### PostGIS

```
Error: Connection refused
```
- Verify host and port are correct
- Check firewall rules
- Verify `pg_hba.conf` allows your IP

```
Error: Authentication failed
```
- Verify username/password
- Check `pg_hba.conf` authentication method
- Try connecting with `psql` first to debug

### STAC

```
Error: 401 Unauthorized
```
- Check if catalog requires authentication
- Verify API key is set correctly
- Contact catalog provider for access
