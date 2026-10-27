---
name: writing-voice
description: Carl Boettiger's writing voice for grants, papers, reports, documentation and app text. Use whenever writing any title, heading or label for him, including strings inside code and config (app and page titles, tab names, chart titles and subtitles, legend and table labels, README headings, PR and commit titles), and whenever drafting or editing prose, topic sentences or captions. Plain noun-phrase headings with no commas, complete sentences, no AI-style slogans or headline formulas. Also covers how to frame his projects' infrastructure work.
---

# Writing in Carl's voice

Carl's verdict on typical Claude prose: "very very Claude … UGH … adds nothing." Write plainly so that the content carries the argument.

## Headings and titles

These rules cover every title, not only document headings. A title inside a JSON config,
an HTML page or a chart spec is still a title.

- **No commas in a heading or title, and no colons or dashes** except in the research-theme
  form below. A comma in a title is almost always a headline formula. If a title seems to need
  one, it holds two ideas: name one and move the other to a sentence below it.
- **No parentheticals in a heading, title or label.** Technical modifiers such as the source,
  dataset version, scenario, statistic or status ("(GMW, uncorrected)", "(SSP3-7.0)", "(mean)",
  "(provisional)", "(comparison)") go in the method text, the units, or a sentence below the
  title. Fold a modifier that matters into the noun phrase instead: "Threatened species
  richness (land, mean)" → "Mean threatened species richness on land".
- **No headline formulas.** These come from magazine and listicle headlines and read as
  Claude at once:
  - "X, ranked", "X, explained", "X, revisited", "X, at a glance", "X, by the numbers", "X, in brief";
  - "X: the Y" and "X — Y" title-plus-tagline pairs;
  - fragments that open with a preposition or a wh-word: "Against every basin at this level",
    "On the Montreux Record", "Where this basin ranks", "What the data show";
  - rhetorical questions; only a genuine research question in a theme heading is allowed (see Themes below).
- **Use the conventional name for a section: a short noun phrase, the term of art a reader expects.** Prefer the funder's own section names.
  - Good: "Background and significance", "Methods", "Capabilities and limitations", "Theme A. Connectivity", "Agentic data curation", "Spatial harmonization with H3", "Evaluation", "Partners", "Contact".
  - Never slogans: "One question, two sites: what sets…", "The pipeline is the product", "Making the stack legible to …".
- **No paraphrase headings.** Technical writers call these statement or question headings, as opposed to topic headings: a clause that spells out what the section contains instead of naming it. They read as written by Claude.
  - "What the app can and cannot do" → "Capabilities and limitations"
  - "How we did this" → "Methods"
  - "Who we work with" → "Partners"
  - "Try an app powered by X" → "Applications"
  - "Components you can use separately" → "Components"
  - "Work with us" → "Contact"
  - "The agent picks a tool" → "Tool calls"
  - Applies to UI text too: labels, nav, buttons, step titles, form fields ("How can we help?" → "Message").
- **No eyebrow labels repeating the heading** (a small kicker above an h2 that says the same thing again).
- **Themes may be stated as a substantive question in his voice,** as in his NSF CAREER proposal: "Theme I. Ecological forecasting vs tipping points: can emerging methods improve our ability to understand and predict critical transitions?" A question is fine; a slogan is not.
- **Roman-numeral or numbered sections, matching the solicitation's required structure.**
- **These rewrites come from the wetlands and coasts explorers:**
  - "Basins, ranked" → "Ranks by basin"
  - "Against every basin at this level" → "Distribution across basins"
  - "On the Montreux Record" → "Montreux Record sites"
  - "Projected warming, 2041–2070 (SSP3-7.0)" → "Projected warming by 2041–2070"
  - "Irrecoverable carbon, whole basin (comparison)" → "Irrecoverable carbon in the whole basin"
  - "Biodiversity score (provisional)" → "Provisional biodiversity score"
  - "Mangrove area 2025 (GMW, uncorrected)" → "Mangrove area in 2025"
- **Check every title before finishing.** List each heading, title and label you wrote, in
  prose and in code alike. Reject any with a comma, a parenthetical, any colon or dash outside a theme heading, any formula above, and any
  that is a clause rather than a name. Rewrite it as the plain noun phrase a reader would use
  to refer to the section.

## Sentences
- **Write in complete sentences.** Subtitles, captions, notes, tooltips and help text are
  sentences with a subject and a verb, not fragments. "Each variable's value here, marked on
  the spread of all basins" → "The dot marks this basin's value on the spread of all basins."
- **Topic sentences are plain declaratives in the first-person plural** that state content. Before/after examples:
  - "Agents propose, gates and people decide." → "No agent publishes on its own: agents propose changes, which validators and people approve."
  - "Compute goes to the data, which is why…" → "Queries run on NRP alongside the data, so users do not download or re-process it."
  - "Sustainment is designed in: …" → "Static cloud-native files are inexpensive to maintain, the tools are open source, and the procedures are documented in public repositories."
- **Avoid these patterns:**
  - "X, not Y" and "not just X but Y" antitheses;
  - colon taglines;
  - aphorisms;
  - rhetorical triplets;
  - "the point is…";
  - "here's the thing";
  - words like "crucially", "simply" and "game-changing".
- **Let the figures carry the framing.** If a figure already shows two sites, the heading doesn't need to say "two sites".
- **Figure titles and captions describe what is shown:** "Time to answer three working-lands questions", not "Prepared once, every question is fast".
- **Accessible to adjacent fields.** Ecology framing should read clearly to computer scientists, and the reverse.

## Framing his projects
- **Infrastructure and curation are the product,** never an "up-front cost" or a caveat. When comparing his stack (agent-curated, cloud-native data plus MCP services on NSF/NAIRR infrastructure) with a naive approach, say what the curation buys downstream.
- **The science is big-picture,** e.g. resilience, connectivity, disturbance. Acknowledge that "details matter and each system is different", then position the work as shared infrastructure that lets each researcher or manager pursue their own details at landscape scale. Do not promise to answer the science questions.
- **Emphasize open foundations:** NSF-supported infrastructure (NRP/NAIRR), open source, open standards and open-weight models, with broad access and no vendor lock-in.
- **Mark unverified numbers [verify]**, and never invent citations. Fetch BibTeX by DOI and cite with pandoc `[@key]`.

## Working drafts
- Outlines use bold topic sentences, each followed by 2–4 supporting bullets, so the argument reads from the bold lines alone.
- Prose comes later and keeps the same topic sentences.
