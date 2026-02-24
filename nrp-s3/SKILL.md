---
name: nrp-s3
description: "Manage S3 object storage on the NRP (National Research Platform) Nautilus cluster, which uses Ceph S3 (not AWS). Covers public vs internal endpoints, rclone usage, bucket creation, public-read policies, CORS configuration, credential handling, and syncing to source.coop. Use when working with S3 buckets on NRP Nautilus, uploading or downloading data, configuring bucket access, or syncing datasets to source.coop."
license: Apache-2.0
compatibility: "Requires kubectl configured for the NRP Nautilus cluster, rclone with an 'nrp' remote, and optionally the AWS CLI."
metadata:
  author: boettiger-lab
  version: "1.0"
---

# NRP S3 Storage

The NRP Nautilus cluster provides S3-compatible object storage powered by Ceph (Rook). This is **not** AWS S3 — it has its own endpoints, credential system, and quirks.

## Two Endpoints

| Endpoint | URL | Use |
|----------|-----|-----|
| **Public** | `s3-west.nrp-nautilus.io` | External access, browsers, public data URLs |
| **Internal** | `rook-ceph-rgw-nautiluss3.rook` | Inside k8s pods (faster, no TLS overhead) |

The **internal endpoint** handles high-concurrency workloads well (DuckDB parallel reads, many pod threads). The **public endpoint** throttles with 503 SlowDown errors under concurrent load — always use the internal endpoint for heavy parallel reads inside the cluster.

### Public URL format

Always use **path-style** URLs (not virtual-hosted):

```
https://s3-west.nrp-nautilus.io/<bucket>/<path>
```

Never use `<bucket>.s3-west.nrp-nautilus.io` — it won't work.

## Credentials

### Kubernetes secrets

Two secrets are pre-configured in the `biodiversity` namespace:

1. **`aws`** — Contains `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`
2. **`rclone-config`** — Contains a complete rclone configuration (includes `nrp` and `source` remotes)

```yaml
env:
  - name: AWS_ACCESS_KEY_ID
    valueFrom:
      secretKeyRef: { name: aws, key: AWS_ACCESS_KEY_ID }
  - name: AWS_SECRET_ACCESS_KEY
    valueFrom:
      secretKeyRef: { name: aws, key: AWS_SECRET_ACCESS_KEY }
volumes:
  - name: rclone-config
    secret:
      secretName: rclone-config
volumeMounts:
  - name: rclone-config
    mountPath: /root/.config/rclone
    readOnly: true
```

### Local credentials

Rclone is configured locally with a remote named `nrp`. Set `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` as environment variables when using the AWS CLI directly.

## Environment Variables for K8s Pods

```yaml
env:
  - name: AWS_ACCESS_KEY_ID
    valueFrom:
      secretKeyRef: { name: aws, key: AWS_ACCESS_KEY_ID }
  - name: AWS_SECRET_ACCESS_KEY
    valueFrom:
      secretKeyRef: { name: aws, key: AWS_SECRET_ACCESS_KEY }
  - name: AWS_S3_ENDPOINT
    value: "rook-ceph-rgw-nautiluss3.rook"
  - name: AWS_HTTPS
    value: "false"                  # Internal endpoint is plain HTTP
  - name: AWS_VIRTUAL_HOSTING
    value: "FALSE"                  # Path-style URLs required
```

## Tool-Specific Endpoint Notes

**DuckDB** (see `duckdb-spatial` skill for secret syntax):
- External: `ENDPOINT 's3-west.nrp-nautilus.io'`, `USE_SSL 'TRUE'`
- Inside pods: `ENDPOINT 'rook-ceph-rgw-nautiluss3.rook'`, `USE_SSL 'FALSE'`, `REGION 'us-east-1'`
- For public (anonymous) access: empty `KEY_ID` and `SECRET` work

**GDAL/OGR** (see `gdal-spatial` skill for VSI prefix syntax):
- External: use `/vsicurl/https://s3-west.nrp-nautilus.io/...`
- Inside pods: use `/vsis3/...` with the env vars above

## Rclone

The remote is named `nrp`. Inside k8s pods, the config is mounted from `rclone-config` secret — no additional setup needed.

## Bucket Management

### Creating a bucket

```bash
rclone mkdir nrp:<bucket-name>
```

### Setting public read access

```bash
aws s3api put-bucket-policy \
  --bucket <bucket-name> \
  --endpoint-url https://s3-west.nrp-nautilus.io \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {"AWS": ["*"]},
        "Action": ["s3:GetBucketLocation", "s3:ListBucket"],
        "Resource": ["arn:aws:s3:::<bucket-name>"]
      },
      {
        "Effect": "Allow",
        "Principal": {"AWS": ["*"]},
        "Action": ["s3:GetObject"],
        "Resource": ["arn:aws:s3:::<bucket-name>/*"]
      }
    ]
  }'
```

### Setting CORS (required for browser access to PMTiles, etc.)

```bash
aws s3api put-bucket-cors \
  --bucket <bucket-name> \
  --endpoint-url https://s3-west.nrp-nautilus.io \
  --cors-configuration '{
    "CORSRules": [{
      "AllowedOrigins": ["*"],
      "AllowedMethods": ["GET", "HEAD"],
      "AllowedHeaders": ["*"],
      "ExposeHeaders": ["ETag", "Content-Length", "Content-Type", "Accept-Ranges", "Content-Range"],
      "MaxAgeSeconds": 3600
    }]
  }'
```

### Verifying configuration

```bash
aws s3api get-bucket-policy --bucket <bucket-name> --endpoint-url https://s3-west.nrp-nautilus.io
aws s3api get-bucket-cors --bucket <bucket-name> --endpoint-url https://s3-west.nrp-nautilus.io
```

## Standard Bucket Layout

```
<bucket>/
├── raw/                              # Source/original data (uploaded once)
├── <dataset>.parquet                 # Cloud-optimized GeoParquet
├── <dataset>.pmtiles                 # Vector tiles for web maps
├── <dataset>/
│   └── hex/
│       └── h0={cell}/data_0.parquet  # H3 hex-indexed, hive-partitioned
├── README.md                         # Data dictionary and usage docs
└── stac-collection.json              # STAC metadata
```

## Syncing to Source.coop

[Source.coop](https://source.coop) mirrors processed datasets for broader public access using the `source` rclone remote (pre-configured in `rclone-config` secret). Run large syncs as k8s jobs, not from a local machine.

## Common Pitfalls

1. **Virtual-hosted URLs** — Always use path-style: `https://s3-west.nrp-nautilus.io/<bucket>/...`
2. **Public endpoint inside pods** — Use the internal endpoint for all S3 ops inside the cluster
3. **High concurrency on public endpoint** — Causes 503 SlowDown; use the internal endpoint
4. **Forgetting CORS** — Required for browser-based tools (PMTiles, map viewers)
5. **HTTPS on internal endpoint** — Internal is HTTP; set `AWS_HTTPS=false`
6. **Hardcoding credentials** — Always use k8s secrets
7. **New buckets are private** — Must explicitly set public read policy
8. **Syncing large data locally** — Always use a k8s job for large transfers to source.coop
