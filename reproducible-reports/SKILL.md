---
name: reproducible-reports
description: How to deliver reports, write-ups, analyses and replications for Carl, using an open, reproducible academic stack (pandoc + LaTeX PDF, markdown source, scripts and SQL in the repo, Makefile) rather than Claude Docs, Word or other proprietary or hosted formats. Use whenever asked to "write up", "make a report", or replicate or summarise an analysis.
---

# Reproducible reports

Carl wants reports he can rebuild, version and share as an academic would. **Do not make a Claude Doc, a .docx or a hosted page for this.** Use those only if he asks for one by name.

## Default stack

- **Source:** `report.md` (pandoc markdown) plus `references.bib`, cited with `--citeproc`.
- **Output:** a PDF article via LaTeX (`pandoc --pdf-engine=xelatex`). Fall back to stand-alone HTML (`pandoc -s --embed-resources`) only when LaTeX truly cannot be installed.
- **Code:** the queries (`queries/*.sql`) and scripts that produce every number, table and figure live next to the report. Do not type numbers into the prose by hand. Generate them (for example, `build/values.json` substituted into `{{placeholders}}`) so a rerun updates the text.
- **Build:** a `Makefile` that goes `results → analysis → report.pdf`. Keep the slow data step as its own target so results can be cached.
- **Figures:** matplotlib or ggplot written to files, 300 dpi PNG or vector PDF.
- **Prose:** follow the `writing-voice` skill: plain headings, declarative sentences, and caveats stated as facts.

## Tools are installable

The pods have passwordless `sudo apt-get`. If pandoc, LaTeX or a font is missing, install it rather than downgrading the output. A typical install:

```bash
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y texlive-xetex texlive-latex-recommended \
  texlive-latex-extra texlive-fonts-recommended lmodern
```

Quarto is also available (`/usr/lib/rstudio-server/bin/quarto`) if executable chunks are a better fit. Plain pandoc is the default.

## Data from the MCP servers

To keep the analysis reproducible outside a chat session, call the MCP server from a script rather than pasting tool results into the report. Use JSON-RPC over HTTP: `initialize`, then `tools/call` with `query`. The server returns markdown tables previewed at about 50 rows. For larger results, pack them into one cell (`string_agg(concat_ws(',', ...), ';')`) and unpack them in the script. A working client is at `~/boettiger-lab/oneill2026-replication/mcp_query.py`.

## Disclosure

Do not credit Claude as an author. Follow the `disclose-tool-use` skill.
