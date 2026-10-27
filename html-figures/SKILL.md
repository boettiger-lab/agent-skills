---
name: html-figures
description: Make conceptual figures for grants, papers and talks — architecture or flow diagrams, Gantt/timelines, site or concept panels, composite figures that pair photos or map tiles with a few big numbers — by authoring HTML/CSS (Inter font, Lucide icons) and rendering to PNG + vector PDF with headless Chromium. Use INSTEAD of hand-drawn matplotlib boxes-and-arrows or raw SVG whenever a figure is not a plain data chart.
---

# HTML figures

Carl's verdict on matplotlib/SVG box-and-arrow figures: "the 5-yr-old-with-marker-pen look". Author these figures as a small web page instead, then export it.

## Design rules
- **Icons over words.** Give each concept a big icon tile (rounded square with a gradient fill in the role color). Labels are 1–3 words and must fit on one line (`white-space:nowrap`). If a label wraps, shorten it.
- **Few elements, a little pop.**
  - White or `#f8fafc` cards, 1px `#e2e8f0` border, 16px radius.
  - One soft colored shadow on the accent tiles.
  - At most one dark band, such as the infrastructure base.
- **Color is meaning.** Fix one color per role across every figure in a project, and state the mapping once in the visuals doc.
- **Hierarchy:** one big bold title or number per panel (800 weight), muted gray secondary text, and no body paragraphs inside figures. Captions carry the detail.
- **Prefer two clean figures over one busy multi-panel.**
  - Photos go full-bleed with a gradient overlay and white text.
  - Maps are exported as bare tiles (no legend or frame) and composed in HTML next to a headline number, a 100% stacked bar and a small legend.
- **Print scale:** design at 1000px wide for a 6.5in text width (×0.624). Keep text ≥ 11px in design units.
- **Photos must be open-license.** Find them on Wikimedia Commons, record credit and license in `photos/CREDITS.md`, and put a credit line in the figure or caption. Avoid people in hero shots unless the user wants them.
- **Data charts** (bars, lines, maps with real axes) stay in matplotlib, using the same font and palette. Load the `dataviz` skill for those.

## Mechanics
1. Copy `assets/fig.css` (tokens, Inter import, `.ic` icon class) and `scripts/build.py` into the project's `figures/html/`.
2. Write `figures/html/<name>.html`:
   - `<link rel="stylesheet" href="../fig.css">`. The build writes to `_build/`, so paths are relative to that folder: photos at `../../photos/x.jpg`, tiles at `../assets/x.png`.
   - Wrap everything in `<div id="fig" style="width:1000px">`.
   - Templating:
     - `{{icon:NAME}}` inlines a Lucide icon (names at lucide.dev; fetched once into `icons/`).
     - `{{json:assets/x.json}}` inlines data for small JS-generated layouts (Gantt rows, stats).
   - CSS grid or flex for layout. Small inline `<script>` blocks are fine for repetitive rows.
3. Render with `python3 figures/html/build.py [name]`. It writes `figures/<name>.png` (3× scale) and a vector `<name>.pdf` sized to `#fig`.
   - If `playwright` is missing: `pip install playwright`. The Chromium binary is `~/.cache/ms-playwright/chromium-*/chrome-linux64/chrome`; build.py finds the newest one automatically.
4. **Look at every render** (Read the PNG). Check for wrapped labels, overlaps, elements hidden under overlays (`z-index`), and text crossing a photo's subject. Then fix and re-render.
5. Commit the HTML source, the `icons/` and `assets/` folders and both outputs. Gitignore `_build/`.

## Patterns that worked (grants-nsf-ai-data)
- **Pipeline:** numbered stage cards (`01`…`05`) in a grid with chevrons between them, chips inside each card, and a dark full-width infrastructure band underneath.
- **Gantt:** a CSS grid with columns = label + 12 quarters.
  - Part blocks on the left: a colored gradient pill with an icon, spanning that part's rows.
  - Bars: rounded gradient pills. Milestones: a white circle with a flag icon plus a bold label.
  - Personnel rows: soft gray bars.
- **Site hero:** two full-bleed photo cards (site name in an overlay at the top, a tag pill at the bottom), then theme cards joined by a bidirectional arrow.
