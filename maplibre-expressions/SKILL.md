---
name: maplibre-expressions
description: "Non-obvious MapLibre GL JS expression gotchas: legacy vs modern filter syntax, when to use 'match' vs 'in' for categorical membership, and other traps LLMs commonly fall into. Use when writing filters, paint expressions, or default_filter/default_style config for MapLibre layers."
license: Apache-2.0
metadata:
  author: boettiger-lab
  version: "1.0"
---

# MapLibre GL JS Expressions: Gotchas and Non-Obvious Behavior

For general MapLibre expression syntax and available functions, see the [MapLibre expression docs](https://maplibre.org/maplibre-gl-js/docs/style-spec/expressions/). This skill covers only the parts that commonly trip up LLMs.

## Legacy vs Modern Filter Syntax

MapLibre has two filter syntaxes. The legacy one is still parsed but deprecated and should never be written in new code.

### The trap: `"in"` with a bare string field name

```json
// WRONG — legacy syntax (deprecated)
["in", "RANGE", "CRUWYL", "CRUWIN", "CRUSWR"]
```

This looks plausible but uses the old style where the field is a bare string rather than a `["get", ...]` expression. It works in some MapLibre versions but is not the expression system.

### Correct: `match` for categorical membership (preferred)

```json
// RIGHT — modern expression, preferred for categorical membership
["match", ["get", "RANGE"], ["CRUWYL", "CRUWIN", "CRUSWR"], true, false]
```

`match` is the right tool when checking if a property equals one of several known values. It returns any output value, so it works identically in both filters and paint expressions.

### Correct: `in` with `literal` array (modern form)

```json
// RIGHT — modern expression using in + literal
["in", ["get", "RANGE"], ["literal", ["CRUWYL", "CRUWIN", "CRUSWR"]]]
```

The modern `in` operator takes `(needle, haystack)`. The haystack must be a `["literal", [...]]` expression — a plain JSON array is not valid here. Use this form when the set of values is dynamic or computed at runtime.

### When to use `match` vs `in`

| Situation | Use |
|-----------|-----|
| Check if property equals one of several known string/number values | `match` |
| Same check in a paint expression (e.g. `fill-color`) | `match` |
| Check membership in a runtime-computed or large array | `in` + `["literal", [...]]` |
| Substring check within a string value | `in` (needle is a string, haystack is `["get", ...]`) |

**Default to `match`** for categorical membership — it's more readable, consistent between filters and paint, and avoids the `literal` wrapping requirement.

## Categorical Paint Expressions

The same `match` expression works directly as a paint property value:

```json
{
  "fill-color": ["match", ["get", "RANGE"],
    "WIN",    "#5B9BD5",
    "CRUWIN", "#0D47A1",
    "SWR",    "#FF8C00",
    "#BDBDBD"
  ],
  "fill-opacity": 0.5
}
```

The final argument is always the fallback (no corresponding key).

## Common Pitfalls

1. **Bare string field in legacy `in`** — `["in", "FIELD", ...]` is legacy syntax. Use `["match", ["get", "FIELD"], [...], true, false]` instead.
2. **`["in", ["get", "FIELD"], ["CRUWYL", ...]]`** — The array must be wrapped in `["literal", [...]]`; a raw JSON array is not a valid expression.
3. **Forgetting the fallback in `match`** — `match` always requires a final fallback value; omitting it is a runtime error.
4. **Using `match` in a filter without returning boolean** — Filters must evaluate to `true`/`false`; `["match", ..., true, false]` is correct, not `["match", ..., "yes", "no"]`.
