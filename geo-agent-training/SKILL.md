---
name: geo-agent-training
description: "Analyze geo-agent app behavior from LLM proxy and MCP server logs, identify inefficiencies, and trace root causes to the correct layer: STAC metadata, MCP tool descriptions, geo-agent framework, or app system prompt. TRIGGER when: reviewing agent behavior, analyzing LLM logs, improving system prompts based on observed failures, debugging tool-use loops, or optimizing query patterns in geo-agent apps."
license: Apache-2.0
metadata:
  author: boettiger-lab
  version: "2.0"
---

# Geo-Agent Training Workflow

Iterative cycle: observe app behavior via logs, diagnose inefficiencies, trace each issue to the correct architectural layer, and fix it there.

## Architecture: Where Information Lives

Each geo-agent app's LLM context is assembled from four layers, each with a specific responsibility. **Fixes must go to the correct layer.**

### Layer 1: STAC Catalog (canonical data source)
- **Owns:** Dataset paths (S3 URLs), column schemas (names, types, descriptions), coded values, dataset descriptions
- **How it reaches the LLM:** `geo-agent/app/dataset-catalog.js` fetches STAC collections at boot, calls `generatePromptCatalog()` to inject dataset metadata (paths, columns, coded values) into the system prompt automatically
- **Also:** The MCP server's `list_datasets` and `get_dataset_details` tools read from the same STAC catalog
- **Fix here when:** Model doesn't know a column name, guesses coded values, uses wrong paths, or lacks dataset descriptions
- **Managed by:** `boettiger-lab/data-workflows` repo (STAC collection JSON files)

### Layer 2: MCP Tool Descriptions (shared query guidance)
- **Owns:** SQL construction patterns, H3 join rules, partition pruning, area calculations, deduplication strategies, raster vs vector aggregation
- **How it reaches the LLM:** `mcp-data-server/query-optimization.md` and `h3-guide.md` are injected into the `query` tool's docstring at server startup
- **Fix here when:** Model writes structurally wrong SQL (bad join patterns, missing h0, wrong aggregation), or doesn't know how to handle H3 resolution mismatches
- **Managed by:** `boettiger-lab/mcp-data-server` repo

### Layer 3: geo-agent Framework (tool orchestration)
- **Owns:** When to use which tool, enforcement of STAC-first patterns, tool descriptions for map tools, the `list_datasets`/`get_dataset_details` local tools, prompt assembly
- **How it reaches the LLM:** Framework code in `geo-agent/app/` — tool registry, map-tools.js, agent.js, dataset-catalog.js
- **Fix here when:** Model skips STAC tools and explores schemas with DESCRIBE/SELECT*, model doesn't call get_dataset_details before using coded values, model uses wrong tool type (SQL vs map), ListToolsRequest spam
- **Managed by:** `boettiger-lab/geo-agent` repo

### Layer 4: App System Prompt (app-specific flavor only)
- **Owns:** ONLY information that cannot live anywhere else — app persona, domain-specific caveats about data interpretation (e.g. "don't say TPL-protected land"), disambiguation rules specific to this app's audience
- **Does NOT own:** SQL examples, S3 paths, column schemas, query patterns, H3 join instructions, tool choice guidance. These belong in layers 1-3.
- **Fix here when:** The issue is purely about how the app presents results or interprets data for its specific audience
- **Goal:** This file should be as small as possible. If you're tempted to add an SQL example here, ask: "Could this be fixed by improving STAC metadata, MCP tool descriptions, or geo-agent framework instead?"

### Design Principle: Information Flows Down, Not Up

```
STAC Catalog (data truth)
    ↓ auto-injected by
geo-agent Framework (tool orchestration + prompt assembly)
    ↓ assembles context from
MCP Tool Descriptions (SQL patterns)
    ↓ all combined into
LLM Context = system-prompt.md + catalog text + MCP tool docstrings
```

**The system-prompt.md should NEVER duplicate information available from STAC or MCP tool descriptions.** If the model needs to know a column name, that column should be documented in STAC. If the model needs to know a join pattern, that should be in query-optimization.md or h3-guide.md.

---

## HARD BOUNDARY: Cross-Repo Changes

Changes to core infrastructure repos require opening issues — **do not directly implement changes** in these repos:

| Repo | What lives there | Action |
|---|---|---|
| `boettiger-lab/geo-agent` | Framework JS (agent.js, dataset-catalog.js, map-tools.js, tool-registry.js) | Open issue with exact proposed change |
| `boettiger-lab/mcp-data-server` | query-optimization.md, h3-guide.md, server.py | Open issue with exact proposed change |
| `boettiger-lab/data-workflows` | STAC collection JSON, dataset processing pipelines | Open issue with exact proposed change |

**What you CAN directly change:** The focal app repo's `system-prompt.md`, `layers-input.json`, and `k8s/` manifests. But prefer fixing root causes in the correct layer over adding workarounds to system-prompt.md.

After tracing all issues, open a single summary issue in the focal app repo that links to all cross-repo issues and describes remaining app-level changes.

---

## Step 1: Collect Logs

You need **both** proxy and MCP logs to see the full picture.

### LLM Proxy logs (what the model decided)

```bash
# All pods, filtered to app origin — must check all pods
for pod in $(kubectl -n biodiversity get pods -l app=llm-proxy -o name); do
  kubectl -n biodiversity logs $pod --since=168h 2>/dev/null | grep '"origin":"https://APP.nrp-nautilus.io"'
done | sort
```

Request log fields: `timestamp`, `type`, `provider`, `model`, `origin`, `message_count`, `tools_count`, `user_message`

Response log format: `✓ RESPONSE: {...}` with `latency_ms`, `has_tool_calls`, `tool_calls`, `tokens`

**Known limitations:**
- `user_message` captures the last message in the conversation, which in a tool-use loop is usually a tool result — not the human's question
- Responses lack an `origin` field (fix tracked in boettiger-lab/open-llm-proxy#2)
- No request_id to correlate request/response pairs (fix tracked in boettiger-lab/open-llm-proxy#1)

### MCP Server logs (what SQL was executed)

```bash
for pod in $(kubectl -n biodiversity get pods -l app=duckdb-mcp -o name); do
  kubectl -n biodiversity logs $pod --since=168h 2>/dev/null | grep -E '🔍 Executing|SQL Error'
done | sort
```

### Historical logs (S3 backup)

```bash
rclone copy nrp:logs-wetlands/ ./logs
```

## Step 2: Reconstruct Conversations

Sort all entries by timestamp and interleave proxy + MCP logs. Key signals:

- **message_count growth** — tracks round-trips per session. A single user question producing message_count 2→20 means 9 tool-call rounds.
- **Errors followed by retries** — the model hit an error and self-corrected (or repeated the same mistake).
- **DESCRIBE/SELECT* spam** — model is exploring schemas instead of using STAC tools. This is a geo-agent enforcement issue.
- **ListToolsRequest spam** — client re-fetches the tool list on every turn (client-side issue in geo-agent).

## Step 3: Classify Each Issue to Its Correct Layer

For every inefficiency found, ask these questions in order:

### 3a. Is the model guessing data paths or column names?

**Symptom:** DESCRIBE queries, SELECT * LIMIT 2, wrong S3 paths, wrong column names, "No results found" from typos.

**Root cause:** Model isn't using STAC tools, OR STAC metadata is incomplete.

**Diagnosis steps:**
1. Call `mcp__duckdb-geo__get_dataset` for the relevant dataset — does it return the columns the model needs?
2. Check if the column info includes descriptions and coded values
3. If STAC metadata is complete but model still guesses → **geo-agent issue** (framework not enforcing STAC-first)
4. If STAC metadata is missing/wrong → **data-workflows issue** (STAC collection needs patching)

### 3b. Is the model writing structurally wrong SQL?

**Symptom:** SQL errors on join patterns, aggregation, partition access, nested aggregates, wrong H3 usage.

**Root cause:** Missing or unclear guidance in MCP tool descriptions.

**Diagnosis steps:**
1. Read `../mcp-data-server/query-optimization.md` and `../mcp-data-server/h3-guide.md`
2. Does the guidance cover this pattern? If not → **mcp-data-server issue**
3. Is the guidance there but the model ignores it? → Check if it's buried or ambiguous → still **mcp-data-server issue** (improve clarity)

### 3c. Is the model using the wrong tool type?

**Symptom:** Running SQL when a map tool would suffice, or vice versa. Calling query tool without calling list_datasets/get_dataset first.

**Root cause:** geo-agent framework tool descriptions or orchestration.

**Diagnosis:** → **geo-agent issue**

### 3d. Is the model misinterpreting data or presenting results incorrectly?

**Symptom:** Says "TPL-protected land" when it should say "land tracked by the Almanac". Misunderstands what a dataset represents. Doesn't apply appropriate caveats.

**Root cause:** This is genuinely app-specific domain knowledge.

**Fix:** system-prompt.md in the app repo. This is the ONE case where app-level fixes are appropriate.

## Step 4: Verify Fixes Against Live Data

**Always test proposed SQL patterns against the actual MCP tool** before recommending them. The public MCP endpoint handles both public and private data — private apps just require credentials passed per-call.

### Public apps

```
mcp__duckdb-geo__query(sql_query="YOUR SQL HERE")
mcp__duckdb-geo__get_dataset(dataset_id="COLLECTION_ID")
```

### Apps with private data

The same public MCP endpoint is used, but credentials must be passed per-call:

```
mcp__duckdb-geo__query(
  sql_query="SELECT column_name FROM (DESCRIBE SELECT * FROM read_parquet('s3://my-private-bucket/...') LIMIT 0)",
  s3_key="...",
  s3_secret="...",
  s3_endpoint="my-s3-endpoint.example.org"
)
```

For a private STAC catalog:
```
mcp__duckdb-geo__get_dataset(
  dataset_id="my-dataset",
  catalog_url="https://my-app.example.org/stac/catalog.json",
  catalog_token="..."
)
```

**If you do not have the credentials in your session**, ask the user to provide them before proceeding. Do not attempt to verify data by going to raw source files — MCP is always the right path.

## Step 5: File Issues and Apply Fixes

### For cross-repo issues (HARD BOUNDARY)

Open a GitHub issue in each affected repo with:
1. **What's failing:** The exact log evidence (error messages, query patterns)
2. **Root cause:** Why the current state causes this failure
3. **Proposed fix:** Exact text/code change needed
4. **Verification:** How to test that the fix works

Use `gh issue create` via Bash tool.

### For app-level fixes

Only modify `system-prompt.md` for genuinely app-specific content:
- Domain interpretation rules (e.g., attribution language for data sources)
- Audience-specific disambiguation (e.g., "when user says 'my district', ask which one")
- Caveats about data limitations specific to this app's context

**Do NOT add to system-prompt.md:**
- SQL examples (these teach the model to hardcode instead of using STAC)
- S3 paths (STAC is the canonical source)
- Column schemas (STAC provides these)
- H3 join patterns (MCP tool descriptions cover these)
- Generic tool-use guidance (geo-agent framework handles this)

### Summary issue

Open one issue in the focal app repo linking all cross-repo issues and listing any remaining app-level changes needed.

## Step 6: Deploy and Validate

Most deploy like this but check the app's AGENTS.md file, some apps with private data have configmap-based deployment instead of pulls from github.

```bash
# For k8s-deployed apps (only needed if system-prompt.md changed)
kubectl -n biodiversity rollout restart deployment/APP_NAME
kubectl -n biodiversity rollout status deployment/APP_NAME
```

Then test by asking the same questions that triggered issues. Check MCP logs for fewer errors and fewer tool calls.

---

## Reference: Key File Locations

| File | Purpose | Repo |
|---|---|---|
| `APP_REPO/system-prompt.md` | App-specific flavor ONLY | App repo |
| `APP_REPO/layers-input.json` | Map layers, welcome message, view config | App repo |
| `mcp-data-server/query-optimization.md` | Shared SQL optimization rules | mcp-data-server |
| `mcp-data-server/h3-guide.md` | Shared H3 spatial math guide | mcp-data-server |
| `mcp-data-server/server.py` | MCP server, tool registration | mcp-data-server |
| `geo-agent/app/agent.js` | Tool-use loop, LLM orchestration | geo-agent |
| `geo-agent/app/dataset-catalog.js` | STAC metadata -> system prompt generation | geo-agent |
| `geo-agent/app/map-tools.js` | Map tool definitions and descriptions | geo-agent |

## Reference: App Inventory

Claude should be running from the repo of the app in question when debugging any specific app.  

