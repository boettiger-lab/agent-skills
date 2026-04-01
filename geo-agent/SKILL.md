# Geo-Agent App Configuration

Geo-agent apps are static sites (MapLibre map + LLM chat) configured by three files: `layers-input.json`, `system-prompt.md`, and optionally `k8s/` manifests. The JavaScript is loaded from CDN — **you do not write JavaScript**.

**Official docs**: https://boettiger-lab.github.io/geo-agent/guide/configuration.html

## The #1 Gotcha: collection_id must match the STAC `"id"` field exactly

`collection_id` in `layers-input.json` is **not a label you invent** — it must exactly match the `"id"` field in the STAC collection JSON. A mismatch causes the layer to silently disappear.

**Always fetch the STAC collection and check its `id` before writing the config:**

```bash
curl -s <collection_url> | python3 -c "import json,sys; d=json.load(sys.stdin); print('id:', d['id']); print('asset keys:', list(d.get('assets',{}).keys()))"
```

## Critical gotchas

### Polygon outlines: use `outline_style`, NOT `layer_type: "line"`

`layer_type: "line"` tells MapLibre the geometry IS a LineString. For polygons, it causes silent rendering failure.

```json
// WRONG — silently renders nothing for polygon data
{ "id": "my-pmtiles", "layer_type": "line", "default_style": { "line-color": "#000" } }

// CORRECT — outline_style auto-adds a line layer on top of the fill
{
    "id": "my-pmtiles",
    "default_style": { "fill-color": "rgba(0,0,0,0)", "fill-opacity": 0 },
    "outline_style": { "line-color": "#1565C0", "line-width": 1.5 }
}
```

### Collapsed groups: set `group` at the collection level, not the asset level

`collapsed` is read from the collection-level `group` field only — setting it on individual assets has no effect:

```json
{
    "collection_id": "...",
    "group": { "name": "Fishing Effort", "collapsed": true },
    "assets": [ ... ]
}
```

### Don't duplicate STAC metadata in system-prompt.md

STAC collection titles, descriptions, column schemas, and S3 parquet paths are injected automatically. Only add domain-specific guidance, query examples, and tool-use rules to `system-prompt.md`.

## Deploying changes

Deployment mechanisms differ between public and private apps — always follow the official docs:

- **Public apps**: https://boettiger-lab.github.io/geo-agent/guide/deployment.html
- **Private apps**: https://boettiger-lab.github.io/geo-agent/guide/private-deployment.html
