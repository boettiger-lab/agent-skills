---
name: stac-navigation
description: Use when browsing, querying, or reasoning about what datasets exist in a STAC catalog — especially before concluding a dataset is missing or absent. Triggers include STAC browser URLs, s3 stac-collection.json links, or any question about what data is available in a catalog.
---

# STAC Catalog Navigation

## Core Rule

**Never conclude a dataset is missing until you have walked the full tree from the root catalog down.**

Stopping at a sub-collection and declaring something absent is the primary failure mode.

## Decoding STAC Browser URLs

The STAC Browser URL encodes the underlying JSON endpoint:

```
https://radiantearth.github.io/stac-browser/#/external/<S3-URL>
```

Fetch the `<S3-URL>` part directly. Example:

```
Browser URL: https://radiantearth.github.io/stac-browser/#/external/s3-west.nrp-nautilus.io/public-data/stac/catalog.json
Fetch:       https://s3-west.nrp-nautilus.io/public-data/stac/catalog.json
```

## Navigation Order

```
1. Fetch ROOT catalog first
   → Walk ALL child links
   → Then walk into sub-collections as needed

2. If given a sub-collection URL, ALSO fetch its parent link
   → Never reason from a sub-collection alone
```

A dataset may be a child of the root catalog but NOT linked from a sub-collection — both are valid locations.

## NRP Catalog Structure

- **Root:** `https://s3-west.nrp-nautilus.io/public-data/stac/catalog.json`
- **High-seas sub-collection:** `public-high-seas/stac-collection.json` (child of root)
- High-seas datasets may appear as **direct children of the root** OR as children of the sub-collection — check both before concluding anything

## What to Fetch

Each STAC JSON has a `links` array. Relevant `rel` values:

| rel | Meaning |
|-----|---------|
| `root` | Top-level catalog — always fetch this first |
| `parent` | Walk up if you started mid-tree |
| `child` | Walk down to find datasets |
| `item` | Leaf-level data asset |

## Common Mistake

> "The high-seas sub-collection only shows 4 datasets, so the others must be missing."

**Wrong.** The root catalog may link those datasets directly. Always check the root.

## Quick Checklist

- [ ] Have I fetched the root catalog?
- [ ] Have I listed all child hrefs from the root?
- [ ] Did I check both the root AND any relevant sub-collection?
- [ ] Only after all of the above: conclude a dataset is present or absent
