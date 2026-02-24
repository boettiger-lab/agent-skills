---
name: gdal-spatial
description: "Read and convert remote geospatial files with GDAL/OGR. Covers the VSI virtual filesystem layer (/vsicurl/, /vsis3/) that enables remote access without downloading, when to use each prefix, ogrinfo and ogr2ogr patterns, geometry edge cases, and when to use DuckDB instead. Use when inspecting or converting GDB, GPKG, Shapefile, GeoTIFF, GeoParquet, or other formats locally or from remote URLs."
license: Apache-2.0
metadata:
  author: boettiger-lab
  version: "2.0"
---

# GDAL/OGR for Remote Geospatial Data

GDAL/OGR is the foundational library for reading and writing geospatial vector and raster formats. Its **virtual filesystem (VSI) layer** makes it possible to read remote files over HTTP or S3 without downloading them first.

## The VSI Virtual Filesystem: Why Prefixes Matter

GDAL was designed around local file paths. To extend it to remote storage, GDAL uses a **virtual filesystem (VSI) layer** that intercepts path strings and transparently handles the I/O. Any GDAL tool (`ogrinfo`, `ogr2ogr`, Python GDAL, and even DuckDB's bundled GDAL via `ST_Read()`) can read remote files simply by prepending the right prefix.

Without VSI prefixes, you would have to download the entire file before GDAL could inspect or convert it — which is impractical for large files and impossible for selective layer reads.

### Core VSI Prefixes

| Prefix | Protocol | Read | Write | Auth |
|--------|----------|------|-------|------|
| `/vsicurl/` | HTTP/HTTPS | yes | no | none (public) |
| `/vsis3/` | S3 API | yes | yes | AWS credentials |
| `/vsistdout/` | stdout pipe | — | yes | — |
| `/vsizip/` | ZIP archive | yes | no | none |
| `/vsicurl_streaming/` | HTTP (sequential) | yes | no | none |

### `/vsicurl/` vs `/vsis3/` — When to Use Each

**Use `/vsicurl/`** when:
- The file is publicly accessible via an HTTPS URL
- You are reading from any S3-compatible endpoint using its public HTTP URL (e.g., `https://s3-west.nrp-nautilus.io/bucket/file.gdb`)
- You do not have or need S3 credentials

**Use `/vsis3/`** when:
- You have S3 credentials configured and the bucket requires authentication
- You need to **write** output directly to S3 (only `/vsis3/` supports write)
- The file is in a private bucket, or you want efficient authenticated range requests via the S3 API

The key differences:
- `/vsicurl/` is read-only; `/vsis3/` supports both read and write
- `/vsicurl/` requires a full HTTPS URL; `/vsis3/` takes `bucket/path` (no protocol or hostname)
- `/vsis3/` requires credentials and optionally a custom endpoint

### Converting Between URL Styles

```
# Public HTTPS URL → vsicurl
https://s3-west.nrp-nautilus.io/bucket/path/data.gdb
→ /vsicurl/https://s3-west.nrp-nautilus.io/bucket/path/data.gdb

# s3:// URL → vsis3 (authenticated) or vsicurl (public endpoint)
s3://bucket/path/data.gdb
→ /vsis3/bucket/path/data.gdb                                        (authenticated S3)
→ /vsicurl/https://s3-west.nrp-nautilus.io/bucket/path/data.gdb     (public HTTP access)
```

### S3 Credentials for `/vsis3/`

```bash
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_S3_ENDPOINT=rook-ceph-rgw-nautiluss3.rook   # internal k8s endpoint
export AWS_HTTPS=NO
export AWS_VIRTUAL_HOSTING=FALSE
```

For public S3 endpoints, `/vsicurl/` with the full HTTPS URL requires no configuration.

## Choosing the Right Tool

| Task | Best tool |
|------|-----------|
| Inspect layers in a remote GDB/GPKG | `ogrinfo` with `/vsicurl/` |
| Convert GDB/Shapefile → GeoParquet | `ogr2ogr` |
| Query/filter a GeoParquet file | DuckDB native `read_parquet()` |
| Spatial joins and aggregation | DuckDB spatial extension |
| Convert GeoParquet → GeoJSONSeq | `ogr2ogr` |
| Stream output to tippecanoe | `ogr2ogr` with `/vsistdout/` |
| Reproject raster data | `gdalwarp` |
| Create COG from GeoTIFF | `gdal_translate` / `gdalwarp` |

**Key principle:** Use GDAL for format conversion and inspection; use DuckDB for analytics on Parquet. See the `duckdb-spatial` skill for DuckDB usage.

## GDAL Parquet Driver Availability

**GDAL is often not built with the Parquet (Arrow) driver.** Check before assuming:

```bash
ogrinfo --formats | grep -i parquet
ogrinfo --formats | grep -i arrow
```

No output means GDAL cannot read or write Parquet. The `ghcr.io/osgeo/gdal:ubuntu-full-latest` Docker image includes the Parquet driver. Most system installs (`apt install gdal-bin`) do not.

When GDAL lacks Parquet support, use DuckDB's native `read_parquet()` for reading and DuckDB `COPY ... TO 's3://...'` for writing.

## OGR: Inspecting Remote Data

### List layers in a multi-layer source

```bash
ogrinfo /vsicurl/https://s3-west.nrp-nautilus.io/public-padus/raw/PADUS4_1Geodatabase.gdb
```

### Get layer schema and feature count

```bash
# Summary only — essential for remote files (without -so, ogrinfo dumps every feature)
ogrinfo -so /vsicurl/https://example.com/data.gdb LayerName

# All layers summary
ogrinfo -so -al /vsicurl/https://example.com/data.gdb
```

### Count features in a layer

```bash
ogrinfo -so /vsicurl/https://example.com/data.gdb LayerName | grep "Feature Count"
```

## OGR: Format Conversion

### GDB layer → GeoParquet

```bash
ogr2ogr -f Parquet output.parquet /vsicurl/https://example.com/data.gdb "LayerName"
```

### GDB layer → GeoJSONSeq

```bash
ogr2ogr -f GeoJSONSeq output.geojsonl /vsicurl/https://example.com/data.gdb "LayerName" -progress
```

### Write directly to S3

```bash
# Read from S3, write to S3 (requires credentials set via AWS_* env vars)
ogr2ogr -f Parquet /vsis3/bucket/output.parquet /vsis3/bucket/raw/source.gdb "LayerName" -progress
```

### Stream to tippecanoe for PMTiles

```bash
ogr2ogr -f GeoJSONSeq /vsistdout/ /vsis3/bucket/data.gdb "LayerName" \
  | tippecanoe -o output.pmtiles -l layername \
    --drop-densest-as-needed --extend-zooms-if-still-dropping --force
```

## Geometry Edge Cases

### Curved geometries (MULTISURFACE, CURVEPOLYGON)

Some GDB files contain curved geometry types that downstream tools cannot handle. Linearize during conversion:

```bash
ogr2ogr -f GPKG \
  -nlt CONVERT_TO_LINEAR \
  -nlt PROMOTE_TO_MULTI \
  output.gpkg input.gdb "LayerName"
```

- `-nlt CONVERT_TO_LINEAR` — converts CircularString, CompoundCurve, CurvePolygon, MultiSurface to linear equivalents
- `-nlt PROMOTE_TO_MULTI` — ensures consistent multi-geometry types

For large files with mixed curved/linear geometry, a two-step pipeline (GDB → GPKG → Parquet) is more reliable than a single pass.

### FID issues

Some formats (GDB especially) include an FID column that can cause Arrow type mapping issues:

```bash
ogr2ogr -f Parquet output.parquet input.gdb "LayerName" -unsetFid
```

## Common Pitfalls

1. **Forgetting `-so` with remote ogrinfo** — Without summary-only mode, ogrinfo tries to dump every feature over the network.
2. **Assuming GDAL has Parquet support** — Check `ogrinfo --formats | grep -i parquet`. Most system installs lack it; use DuckDB instead.
3. **Using `/vsicurl/` when you need to write** — `/vsicurl/` is read-only. Use `/vsis3/` for output to S3.
4. **Passing `s3://` URLs to GDAL tools** — GDAL does not understand `s3://` protocol strings. Convert to `/vsis3/bucket/path` or `/vsicurl/https://endpoint/bucket/path`.
5. **Curved geometries breaking downstream tools** — Always check with `ogrinfo` and linearize GDB sources if MULTISURFACE or CURVEPOLYGON types are present.
