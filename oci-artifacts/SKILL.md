---
name: oci-artifacts
description: Use when storing, versioning, or sharing large files alongside a GitHub repo — model checkpoints, datasets, build artifacts, binaries, fixtures — and you want collaborators to use their GitHub access rather than separate cloud credentials. Covers ghcr.io, oras CLI, content-addressing, public/private access, and the tradeoffs vs git-lfs, S3 buckets, and GitHub Releases.
---

# OCI Artifacts for Code-Adjacent Data

## Overview

OCI registries (like `ghcr.io`) were built for container images but the OCI artifact spec generalizes them to **any** file set. You can push arbitrary files as versioned, content-addressed, deduplicated artifacts. The access unit is a *package* tied to a GitHub org, so collaborators authenticate with their existing GitHub access — no separate bucket credentials to distribute.

Core properties worth knowing:

- **Content-addressed.** Every blob is identified by its `sha256:<digest>`. Pinning `pkg@sha256:...` gives immutable byte-for-byte guarantees; tags (`:v1.2.3`, `:latest`) are mutable labels on top.
- **Metadata-rich.** Artifacts carry annotations (source repo, description, labels) and can be signed (cosign/sigstore) and referred-to (SBOMs, attestations).
- **Free and scales.** Public packages on ghcr.io have no storage or bandwidth caps. Layers up to ~10GB each.
- **Access follows the code.** Linking a package to a source repo (via the `org.opencontainers.image.source` annotation) lets visibility inherit from the repo; in Actions, `GITHUB_TOKEN` gets scoped read access to packages in the same org for free.

## When to use

Good fit:

- **Model checkpoints / training artifacts** tied to code in the repo
- **Test fixtures or reference datasets** that need to travel with a repo version
- **Build outputs / compiled binaries** distributed to collaborators
- **Dataset snapshots pinned to a paper** (cite by digest for reproducibility)
- **Private artifacts inside a GitHub org** (the ergonomic sweet spot — no cred distribution)

Bad fit (reach for a bucket or GitHub Releases instead):

- **Browser-embedded media** (`<img>`, `<video>`, CSS `background-image`) — registries don't serve blobs without an `Authorization` header (see Workarounds below)
- **Cloud-optimized geospatial** (COG, GeoParquet, PMTiles) — tooling (GDAL, DuckDB, maplibre) assumes S3-style byte-range reads
- **Anonymous CDN-backed serving** — no native CDN story for ghcr blobs

## Why not git-lfs

LFS *looks* like the obvious answer and isn't:

- **Not free at scale.** GitHub's free tier is 1GB storage / 1GB bandwidth per month; a single large checkpoint blows past it. Every fresh clone draws from the bandwidth pool.
- **Breaks forks and open-source workflows.** Forked repos don't inherit the parent's LFS quota; contributors routinely hit "this repository is over its data quota."
- **Overloads git semantics.** Easy to `git add` a big file *before* activating lfs, which means the blob lands in history. Fixing requires rewriting history — hostile if your repo policy blocks force-push.
- **One-tool-for-two-jobs.** You now have "the file" and "the pointer to the file" both moving through git. OCI artifacts keep code and data cleanly separated while still versioning both.

If the file is small enough to commit directly (a few MB, rarely changes), just commit it. Everything else: OCI artifact.

## How

### Install `oras`

```bash
# see github.com/oras-project/oras/releases for current version
curl -sSL -o /tmp/oras.tar.gz \
  https://github.com/oras-project/oras/releases/download/v1.2.2/oras_1.2.2_linux_amd64.tar.gz
tar -xzf /tmp/oras.tar.gz -C ~/.local/bin/ oras
chmod +x ~/.local/bin/oras
```

### Auth (once per machine)

```bash
# Local: reuse your gh token (needs write:packages scope to push)
gh auth refresh -h github.com -s write:packages
gh auth token | oras login ghcr.io -u <your-gh-username> --password-stdin
```

In GitHub Actions, `GITHUB_TOKEN` already works — no extra setup:

```yaml
- run: echo "${{ secrets.GITHUB_TOKEN }}" | oras login ghcr.io -u $GITHUB_ACTOR --password-stdin
```

### Push

```bash
oras push ghcr.io/<org>/<pkg>:<tag> \
  --artifact-type application/vnd.<yourthing> \
  --annotation "org.opencontainers.image.source=https://github.com/<org>/<repo>" \
  --annotation "org.opencontainers.image.description=<what this is>" \
  path/to/file.ext:<mime-type>
```

The `source` annotation auto-links the package to the repo; visibility can then be set to inherit from the repo. Multiple files go in one artifact by adding more `path:mime` pairs — they're pulled atomically as a unit.

### Pull

```bash
oras pull ghcr.io/<org>/<pkg>:<tag> -o ./outdir
# or pin by digest for immutability:
oras pull ghcr.io/<org>/<pkg>@sha256:<digest> -o ./outdir
```

### Inspect

```bash
oras manifest fetch ghcr.io/<org>/<pkg>:<tag>          # full manifest (JSON)
oras repo tags ghcr.io/<org>/<pkg>                     # list tags
oras discover ghcr.io/<org>/<pkg>:<tag>                # referrers (signatures, SBOMs, etc.)
```

## Public vs private

**Private.** New packages default to private/internal. When the package is linked to a source repo (via the `source` annotation), flip on "Inherit access from source repository" in package settings — that's the ergonomic win. In Actions, `GITHUB_TOKEN` reads them automatically. Collaborators with repo access can pull with their own `gh auth token`; no shared secrets.

**Public.** After the first push, open
`https://github.com/orgs/<org>/packages/container/<pkg>/settings` and flip visibility to **Public**. GitHub has no REST API for this one-time step (PATCH to `/orgs/<org>/packages/...` returns 404). Once public, anyone can pull anonymously.

## Anonymous access (public packages)

Once a package is public, any blob is reachable by digest with a dummy bearer token:

```bash
curl -fL --header "Authorization: Bearer QQ==" \
  "https://ghcr.io/v2/<org>/<pkg>/blobs/sha256:<digest>" -o out.bin
```

The manifest (which lists the blobs that make up a tag) is at
`https://ghcr.io/v2/<org>/<pkg>/manifests/<tag>` — same dummy-bearer trick.

`QQ==` is base64 of `A`; ghcr accepts any non-empty token for public-package reads.

## Content-addressing and its limit

The nice property: given `sha256:<digest>` for a public blob, `curl` gets you the exact bytes. Good for reproducibility — you can hardcode digests in scripts, lockfiles, or paper recipes.

The limit: addressing is **not globally content-addressable**. You still need the `<org>/<pkg>` prefix in the URL to resolve a digest, unlike IPFS/content-addressed networks where the hash alone is sufficient. Blobs are deduplicated *within* a package, not across the registry. Plan your package boundaries accordingly.

## Browser embedding — workarounds

Browsers won't send custom `Authorization` headers for `<img>`, `<video>`, CSS `background-image`, or `<link>`. Bare ghcr blob URLs return 401 from a page. Three viable patterns:

1. **Bake into deploy.** CI step `oras pull`s the artifact into the site root; HTML uses plain relative paths. Simple; adds a CI step and re-downloads per deploy.
2. **JS loader.** A script `fetch()`es the blob with the `QQ==` header, wraps with `URL.createObjectURL()`, and swaps into `src`. Keeps the repo self-contained; adds first-paint delay; doesn't cleanly handle CSS backgrounds without extra plumbing.
3. **Redirect proxy.** A small Cloudflare Worker (or similar) at a stable URL that adds the header server-side. Best UX for embeds; adds infrastructure to own.

None are ideal. **If browser embedding is the primary workload, use a bucket** (S3, NRP Ceph, etc.) — buckets serve plain HTTP without headers and integrate with CDNs.

## When to reach for something else

| Workload | Better choice |
|----------|---------------|
| Embedded media in a public webpage | S3-style bucket |
| Cloud-optimized geospatial (COG/GeoParquet/PMTiles) | S3-style bucket (ecosystem assumes it) |
| Frozen dataset snapshot with DOI for citation | Zenodo (OCI artifact alongside is fine) |
| Anonymous CDN-backed serving | GitHub Releases (2GB/file cap) or S3 + CDN |
| "These N files as one atomic version, pinned by hash" | **OCI artifact** |
| Private artifact shared across a GitHub org | **OCI artifact** |

## Common mistakes

- Forgetting the `org.opencontainers.image.source` annotation on push. Without it, the package isn't linked to the repo and can't inherit visibility.
- Expecting `<img src="https://ghcr.io/...">` to work in HTML. It won't; use one of the workarounds or a bucket.
- Assuming public visibility is API-settable. It isn't; one-time manual flip per package.
- Using `:latest` in reproducibility recipes. Pin by digest (`@sha256:...`) or an immutable tag convention.
- Pushing many unrelated files under one package. Prefer one package per logical artifact family so dedup, versioning, and access inheritance stay meaningful.
