# Geo-Agent App Configuration

Geo-agent apps are static sites (MapLibre map + LLM chat) configured by three files: `layers-input.json`, `system-prompt.md`, and optionally `k8s/` manifests. The JavaScript is loaded from CDN — **you do not write JavaScript**.

Full docs: [`geo-agent` repo](https://github.com/boettiger-lab/geo-agent), template: [`geo-agent-template` repo](https://github.com/boettiger-lab/geo-agent-template).

## The #1 Gotcha: collection_id must match the STAC `"id"` field exactly

`collection_id` in `layers-input.json` is **not a label you invent** — it must exactly match the `"id"` field in the STAC collection JSON. The catalog code stores datasets under `collection.id` (from STAC) and looks them up by `collection_id` (from config). A mismatch causes the layer to silently disappear.

**Always fetch the STAC collection and check its `id` before writing the config:**

```bash
curl -s <collection_url> | python3 -c "import json,sys; d=json.load(sys.stdin); print('id:', d['id']); print('asset keys:', list(d.get('assets',{}).keys()))"
```

This gives you both the correct `collection_id` and the valid asset `id` values in one step.

## layers-input.json structure

```json
{
    "catalog": "https://s3-west.nrp-nautilus.io/public-data/stac/catalog.json",
    "titiler_url": "https://titiler.nrp-nautilus.io",
    "mcp_url": "https://duckdb-mcp.nrp-nautilus.io/mcp",
    "view": { "center": [-119.5, 37.5], "zoom": 6 },
    "collections": [ ... ]
}
```

### Collection entry fields

| Field | Required | Notes |
|---|---|---|
| `collection_id` | Yes | Must match STAC `"id"` exactly — fetch and verify |
| `collection_url` | No | Direct URL to STAC JSON; bypasses root catalog traversal. Required for collections not in the root catalog |
| `assets` | No | If omitted, all visual assets are loaded with defaults |

### Asset entry fields

| Field | Notes |
|---|---|
| `id` | STAC asset key — must match exactly. Fetch and verify (see above) |
| `display_name` | Label in layer toggle UI |
| `group` | Groups layers in the UI panel (e.g., `"Carbon"`, `"Political Boundaries"`) |
| `visible` | Default `false` |
| `default_style` | MapLibre fill paint properties |
| `outline_style` | Auto-adds a line layer on top of the fill for polygon outlines |
| `default_filter` | MapLibre filter expression applied at load time |
| `tooltip_fields` | Property names shown on hover |
| `colormap` | COG only: TiTiler colormap name (`"reds"`, `"viridis"`, etc.) |
| `rescale` | COG only: `"min,max"` for color scaling |
| `alias` | Creates a second logical layer from the same STAC asset |

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

### Don't duplicate STAC metadata in system-prompt.md

STAC collection titles, descriptions, column schemas, and S3 parquet paths are injected automatically into the LLM system prompt by `dataset-catalog.js`. Only add domain-specific guidance, query examples, and tool-use rules to `system-prompt.md`.

### LLM config: k8s vs GitHub Pages

- **Kubernetes**: Omit the `"llm"` block entirely. The k8s ConfigMap injects `config.json` with keys at deploy time.
- **GitHub Pages / static hosting**: Include an `"llm"` block with `"user_provided": true` so visitors enter their own API key.

## Deploying changes (k8s)

The pod git-clones the repo at startup — changes only take effect after a push + rollout restart:

```bash
git add layers-input.json system-prompt.md && git commit -m "..." && git push
kubectl -n biodiversity rollout restart deployment/<app-name>
```
