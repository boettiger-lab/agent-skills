---
name: duckdb-spatial
description: "Critical gotchas for DuckDB spatial extension: the ST_Read() vs read_parquet() distinction, vendored GDAL limitations, S3 secret configuration for non-AWS endpoints, and URL style rules. Use when working with geospatial data in DuckDB, especially with remote files on S3 or HTTPS, or when hitting errors with ST_Read() and Parquet files."
license: Apache-2.0
metadata:
  author: boettiger-lab
  version: "1.0"
---

# DuckDB Spatial: Gotchas and Non-Obvious Behavior

For general DuckDB spatial usage (functions, geometry types, spatial predicates), see the [DuckDB spatial docs](https://duckdb.org/docs/extensions/spatial/overview). This skill covers the parts that commonly trip up LLMs.

## The Critical Distinction: Two Independent Readers

DuckDB has two completely separate ways to read geospatial data, and **they do not share URL conventions**:

| Function | Reads via | URL style | Can read GeoParquet? |
|----------|-----------|-----------|----------------------|
| `ST_Read('path')` | DuckDB's vendored GDAL | `/vsicurl/`, `/vsis3/` | **No** |
| `read_parquet('url')` | DuckDB native reader | `s3://`, `https://` | **Yes** |

Passing `s3://` to `ST_Read()` fails. Passing `/vsicurl/` to `read_parquet()` fails. These errors are not always obvious from the error message.

## ST_Read(): Remote Files Need VSI Prefixes

`ST_Read()` uses DuckDB's bundled GDAL. All remote paths must use GDAL's VSI prefixes:

```sql
-- Public HTTPS file
SELECT * FROM ST_Read('/vsicurl/https://example.com/data.gdb', layer='MyLayer');

-- Authenticated S3 (requires GDAL AWS env vars, not DuckDB secrets)
SELECT * FROM ST_Read('/vsis3/bucket/path/data.gpkg', layer='MyLayer');
```

### What DuckDB's vendored GDAL cannot do

- **Read GeoParquet** — vendored GDAL lacks Arrow/Parquet libraries; `ST_Read('file.parquet')` will error
- **Write to S3** — vendored GDAL cannot write to `/vsis3/`; use DuckDB's native `COPY ... TO 's3://...'` instead

## read_parquet(): GeoParquet Requires spatial Extension Loaded

The `spatial` extension must be loaded for DuckDB to recognize WKB geometry blobs in Parquet:

```sql
INSTALL spatial;
LOAD spatial;

-- Then read_parquet() will correctly interpret the geometry column
SELECT * FROM read_parquet('s3://public-padus/padus-4-1/fee.parquet') LIMIT 10;
SELECT * FROM read_parquet('https://s3-west.nrp-nautilus.io/public-padus/padus-4-1/fee.parquet');
```

Without `LOAD spatial`, geometry columns appear as raw binary blobs.

## S3 Secrets for Non-AWS Endpoints

See the [DuckDB Secrets Manager docs](https://duckdb.org/docs/stable/configuration/secrets_manager) for the full reference.

DuckDB's `s3://` defaults to AWS. For Ceph-based endpoints (NRP Nautilus, MinIO, etc.), a secret with the custom endpoint is required — otherwise DuckDB silently sends requests to AWS and fails.

```sql
-- Public bucket on a custom endpoint (no credentials needed)
CREATE SECRET nrp (
    TYPE s3,
    ENDPOINT 's3-west.nrp-nautilus.io',
    URL_STYLE 'path'
);

-- Private bucket
CREATE SECRET nrp_private (
    TYPE s3,
    KEY_ID 'your-key',
    SECRET 'your-secret',
    ENDPOINT 's3-west.nrp-nautilus.io',
    URL_STYLE 'path'
);
```

`URL_STYLE 'path'` is required for Ceph/MinIO; the default `vhost` style will fail.

For NRP Nautilus specifically, the correct endpoint depends on whether you are inside a k8s pod or not — see the `nrp-s3` skill for endpoint values and SSL settings.

## Accessing Multiple S3 Endpoints Simultaneously

When reading from buckets on different endpoints (e.g., NRP and AWS S3), DuckDB needs to know which secret applies to which `s3://` URL. Since only the bucket name appears in an `s3://` address — not the endpoint — this is resolved with **secret scopes**.

A secret's `SCOPE` is a path prefix. When multiple secrets match, the longest prefix wins. Use per-bucket scopes to route cleanly:

```sql
-- Bucket on NRP Nautilus
CREATE SECRET nrp_bucket (
    TYPE s3,
    ENDPOINT 's3-west.nrp-nautilus.io',
    URL_STYLE 'path',
    SCOPE 's3://my-nrp-bucket'
);

-- Bucket on AWS (or source.coop)
CREATE SECRET aws_bucket (
    TYPE s3,
    KEY_ID 'aws-key',
    SECRET 'aws-secret',
    SCOPE 's3://my-aws-bucket'
);

-- Now each s3:// path routes to the correct endpoint automatically
SELECT * FROM read_parquet('s3://my-nrp-bucket/data.parquet');   -- uses nrp_bucket secret
SELECT * FROM read_parquet('s3://my-aws-bucket/data.parquet');   -- uses aws_bucket secret
```

To debug which secret DuckDB selects for a given path:

```sql
FROM which_secret('s3://my-nrp-bucket/file.parquet', 's3');
```

Without scopes, if two secrets exist for the same type, DuckDB's selection is ambiguous and one endpoint's credentials will silently be sent to the wrong endpoint.

## Common Pitfalls

1. **`s3://` passed to `ST_Read()`** — `ST_Read()` is GDAL-based; it requires `/vsicurl/` or `/vsis3/`, not `s3://`.
2. **`/vsicurl/` passed to `read_parquet()`** — Native reader uses `s3://` or `https://`, not GDAL prefixes.
3. **`ST_Read('file.parquet')`** — Vendored GDAL cannot read Parquet. Use `read_parquet()` with spatial extension loaded.
4. **Missing S3 secret for custom endpoint** — Omitting a secret causes silent routing to AWS. Always create a secret with the correct endpoint and `URL_STYLE 'path'` for non-AWS S3.
5. **Writing to `/vsis3/` from DuckDB** — Use `COPY ... TO 's3://...'` with a configured secret; vendored GDAL write to S3 does not work.
