---
name: cng-datasets
description: "Process geospatial datasets into cloud-native formats (GeoParquet, PMTiles, H3 hex Parquet) using the cng-datasets CLI and NRP Kubernetes. Covers the full workflow: URL verification, raw S3 upload, YAML generation, cluster deployment, monitoring, and documentation. Use when processing any geospatial dataset in the data-workflows repo, or when working with the cng-datasets CLI."
license: Apache-2.0
compatibility: "Requires uv/pip for local CLI install, kubectl for NRP Nautilus cluster. `--namespace` still defaults to `biodiversity`, but current dataset workflows run in `geo-workflows` — pass it explicitly. See nrp-k8s and nrp-s3 skills for cluster/S3 details."
metadata:
  author: boettiger-lab
  version: "1.0"
---

# cng-datasets: Dataset Processing Workflow

Full reference: see `AGENTS.md` in the data-workflows repo. This skill covers the essential workflow steps and the gotchas that matter most.

## What It Produces

Each dataset results in three outputs per layer:

| Output | Path | Use |
|--------|------|-----|
| GeoParquet | `bucket/dataset.parquet` | Analytical queries (DuckDB, Polars) |
| PMTiles | `bucket/dataset.pmtiles` | Web map visualization |
| H3 Hex Parquet | `bucket/dataset/hex/h0={cell}/data_0.parquet` | Spatial joins, hive-partitioned |

**All data processing runs on the cluster. The CLI only generates YAML locally — never process data on your local machine.**

## Local Setup

```bash
uv venv && source .venv/bin/activate
uv pip install git+https://github.com/boettiger-lab/datasets.git
```

## The Six Steps

### Step 1: Verify source URLs

**Always verify URLs exist before generating workflows.** Many datasets are multi-file (per-state, per-region).

```bash
# Single file
curl -I https://example.com/data.zip         # Must return HTTP/2 200

# Multi-file: discover actual filenames
curl -s https://www2.census.gov/geo/tiger/TIGER2024/TRACT/ | grep '.zip' | head -20
```

### Step 2: Upload raw source to S3 first

**Always upload original source files to `s3://<bucket>/raw/` before any conversion.** If a later job fails, you restart from S3 rather than re-downloading from the external provider (which may be slow or rate-limited).

```bash
# Via rclone (locally or in a k8s job)
rclone copy data.gdb nrp:<bucket>/raw/
```

Check if already uploaded: `https://s3-west.nrp-nautilus.io/<bucket>/raw/<filename>`

Subsequent jobs should read from S3, not the original provider URL.

### Step 3: Generate the pipeline YAML

```bash
cng-datasets workflow \
  --dataset <name> \
  --source-url <url> \
  --bucket <bucket> \
  --namespace geo-workflows \
  --h3-resolution 10 \
  --parent-resolutions "9,8,0" \
  --hex-memory 32Gi \
  --max-completions 200 \
  --max-parallelism 50 \
  --output-dir catalog/<dataset>/k8s/<name>
```

Useful additions, none of them on by default:

| Flag | Use |
|------|-----|
| `--expect-features N` | Feature count you know independently. The convert step exits non-zero on a mismatch, so a silently truncated source fails the workflow instead of flowing into hex and PMTiles. |
| `--trim-strings` | Strip leading/trailing whitespace from every VARCHAR column, for sources with stray spaces in categorical fields (WDPA `NO_TAKE = 'All '`). |
| `--simplify-tolerance T` | Simplify geometries after reprojection; T is in target-CRS units (degrees for EPSG:4326). |
| `--lat-column` / `--lon-column` | Required shape when the source is a CSV of points rather than a spatial format. |
| `--resolution-by-area` | Stratify features into area tiers so huge features hex at coarser resolution. |
| `--backend armada` | Submit through Armada instead of k8s Jobs; see the Armada note below. |

Add `--layer <LayerName>` for multi-layer sources (GDB, GPKG). For multi-layer files, run one `workflow` command per layer:

```bash
cng-datasets workflow --dataset padus-4-1/fee --layer PADUS4_1Fee ...
cng-datasets workflow --dataset padus-4-1/easement --layer PADUS4_1Easement ...
```

### Step 3b: Raster sources use `raster-workflow`

A raster source (GeoTIFF/COG) does not go through `workflow` — that path is
vector-only (convert → PMTiles → hex → repartition). Rasters use a separate
generator producing setup-bucket → [preprocess-cog] → hex:

```bash
cng-datasets raster-workflow \
  --dataset <name> \
  --source-url <url> \
  --bucket <bucket> \
  --namespace geo-workflows \
  --h3-resolution 10 \
  --parent-resolutions "9,8,0" \
  --value-column <name> \
  --hex-resampling mean \
  --h0-subset "12,14,20,50,71,78" \
  --output-dir catalog/<dataset>/k8s/<name>
```

**`--hex-resampling` follows the source's units, not the concept.** `sum` only
for values already integrated per pixel (population counts); `mean` for
intensities and densities — summing a per-area density is the classic wrong
answer. `mode` for categorical, `fractions` for per-class area accounting,
`max`/`min` for extrema.

**`--h0-subset` matters for any regional raster.** Without it the hex job fans
out over all 122 h0 base cells. CONUS occupies 6 of them, so a CONUS raster
would start 116 pods that each localize a multi-GB COG, find no overlap and
exit. Pass the cells the source covers; the generated manifest carries the
index mapping. It does not reduce per-pod memory — it removes pods that had
nothing to do.

**Repeat `--source-url` for multiple tiles**, which adds a preprocess-cog step
that mosaics them (handling mixed CRS) into one WGS84 COG before hexing. A
non-COG source triggers that step automatically.

### Step 4: Apply to the cluster

```bash
# One-time RBAC setup (likely already done)
kubectl apply -f catalog/<dataset>/k8s/<name>/workflow-rbac.yaml

# Per workflow
kubectl apply -f catalog/<dataset>/k8s/<name>/configmap.yaml \
              -f catalog/<dataset>/k8s/<name>/workflow.yaml
```

The orchestrator runs: setup-bucket → convert → pmtiles + hex (parallel) → repartition.

### Step 5: Monitor

```bash
kubectl get jobs | grep <name>
kubectl logs job/<name>-workflow    # Orchestrator
kubectl logs job/<name>-convert     # Conversion step
```

### Step 6: Document

Create and upload to the bucket:

- `catalog/<dataset>/stac/README.md` — data dictionary, usage examples, citation
- `catalog/<dataset>/stac/stac-collection.json` — STAC metadata

**Required in every README.md:**
- A MapLibre GL JS snippet with the correct `source-layer` name
- A DuckDB example with the full public parquet URL

**Required in every stac-collection.json:**
- `"vector:layers": ["<name>"]` for any layered asset (PMTiles, GDB, GPKG)
- `"table:columns"` array

```bash
rclone copy catalog/<dataset>/stac/README.md nrp:<bucket>/
rclone copy catalog/<dataset>/stac/stac-collection.json nrp:<bucket>/
```

Then add a child link in the central catalog:

```bash
curl -s https://s3-west.nrp-nautilus.io/public-data/stac/catalog.json > /tmp/catalog.json
# Edit /tmp/catalog.json to add child link pointing to dataset's stac-collection.json URL
rclone copyto /tmp/catalog.json nrp:public-data/stac/catalog.json
```

## Critical Gotchas

### `--dataset` controls the PMTiles source-layer name

The `--dataset` last path segment becomes the PMTiles `source-layer` — not the GDB/source layer name. This is what MapLibre needs in `"source-layer"` to render tiles.

| `--dataset` | PMTiles `source-layer` | S3 path prefix |
|-------------|----------------------|----------------|
| `padus-4-1/fee` | `fee` | `padus-4-1/fee` |
| `census-2024/tract` | `tract` | `census-2024/tract` |

**Never derive `source-layer` from the GDB layer name** (e.g., `PADUS4_1Fee`). Always derive it from `--dataset`.

### Multi-file zipped datasets: don't pass multiple zip URLs

`cng-convert-to-parquet` cannot process multiple `.zip` URLs — it detects `.zip` in paths and blocks multi-source processing. The correct approach is a preprocessing k8s job:

```yaml
command: [bash, -c, |
  # Parallel download
  for fips in 01 02 04 05; do
    curl -sS -O "https://example.com/tl_2024_${fips}_tract.zip" &
  done
  wait
  unzip -q -o "*.zip"
  # Tool handles merging multiple shapefiles
  cng-convert-to-parquet /tmp/data/*.shp s3://bucket/output.parquet
]
```

Do **not** sequentially merge with `ogr2ogr -append` — `cng-convert-to-parquet` already merges multiple files efficiently.

### Memory is driven by spatial area, not feature count

The hex step unnests millions of H3 cells in memory. A US state like Alaska (~1.7M km² at resolution 10) generates ~113M hexes and requires 64Gi+. Feature count is irrelevant — 50 US states need as much chunking as 85K census tracts.

| Parameter | Guidance |
|-----------|----------|
| `--hex-memory` | Scale with spatial area per chunk. Start at 32Gi for US states. |
| `--max-completions` | Keep at 200 for any US-scale dataset. Never exceed 200 (hard etcd limit). |
| `--max-parallelism` | 50 is standard; see pod quota constraint below. |
| `--h3-resolution` | Lower (8, 6) for coarser data or very large areas. |
| `--intermediate-chunk-size` | Decrease if hex pods OOM during unnest. |

### Armada backend: non-preemptible by default, and retries do not survive

`--backend armada` also emits `armada-*.yaml` alongside the k8s YAMLs. Two
things to know before using it:

- Converted jobs default to the **non-preemptible** `armada-default`. A
  preempted Armada job is not rescheduled, unlike an opportunistic k8s pod
  which its Job controller recreates. `--armada-priority-class preemptible`
  opts back in, and is the right choice only once units are small enough that
  losing one is cheap.
- Conversion reads the podSpec, so k8s **Job-level retry settings do not
  survive it** (`backoffLimit`, `backoffLimitPerIndex`, `maxFailedIndexes`).
  Generation warns when a real retry budget is dropped.

The converter reproduces the shape of the k8s job it reads — same cpu, memory
and runtime — so today it is a transport change rather than a granularity win.

### Namespace pod quota: run hex workflows sequentially

The namespace has a **hard limit of 200 pods total**. A single hex workflow with `--max-parallelism 50` can consume 50 pods. Running multiple hex workflows simultaneously exhausts the quota.

**Rule: never submit more than one hex workflow at a time.**

```bash
for dataset in dataset-a dataset-b; do
  kubectl apply -f catalog/.../k8s/${dataset}/configmap.yaml \
                -f catalog/.../k8s/${dataset}/workflow.yaml
  kubectl wait job/${dataset}-workflow --for=condition=complete --timeout=7200s
done
```

## Reprocessing Failed Chunks

If specific hex chunks fail (e.g., OOM on extremely complex geometries):

1. Identify failed chunk IDs: `kubectl get pods | grep <name>-hex | grep -E "Error|Failed"`
2. Copy the hex job YAML as a template, edit to set `completions: <n>`, change the job name, and add a `CHUNK_MAP` array mapping `JOB_COMPLETION_INDEX` to the failed chunk IDs
3. Rerun at a coarser resolution (`--resolution 8`) if needed
4. Run repartition after completion — it merges all chunks from both resolutions

See `AGENTS.md` in data-workflows for the full rechunking YAML pattern.

## Common Pitfalls

1. **Unverified source URL** — Always `curl -I` before generating. 404s are the most common failure mode.
2. **Wrong `source-layer` in documentation** — Derive from `--dataset` last segment, never from the GDB layer name.
3. **Multiple zip URLs passed to the workflow** — Create a preprocessing job that downloads, unzips, then calls `cng-convert-to-parquet` on the unpacked files.
4. **Running multiple hex workflows in parallel** — Will exhaust the 200-pod namespace quota. Run sequentially.
5. **Sizing hex memory by feature count** — Size by spatial area. 50 states needs the same chunking as 85K tracts.
6. **Processing data locally** — The CLI generates YAML. All processing runs on the cluster.
7. **Not uploading raw data to S3 first** — If convert fails, you'll need to re-download from a slow/rate-limited provider.
8. **Assuming a clean exit means complete data** — convert reports `Wrote N rows`; check it. A source truncated upstream converts cleanly and exits 0. Pass `--expect-features` when you know the count independently.
9. **Building a raster below h8, or above it without h8 as a parent** — h8 is the catalog's universal join key. A build at h6 carries no h8 column and cannot be joined; a build at h10 only carries h8 if 8 is in `--parent-resolutions`. Generation warns in both cases.
