---
name: disclose-tool-use
description: >
  How to disclose use of Claude in a repository, and the rule against crediting it.
  Use whenever creating a git repo, making a first commit, writing commit messages
  or PR bodies, or preparing anything for sharing or publication. Claude is a tool,
  not an author: never add Co-Authored-By trailers or "Generated with Claude Code"
  credit; instead add a DISCLOSURE.md.
---

# Disclose tool use; never credit the tool

## Hard rules

1. No `Co-Authored-By: Claude ...` trailer on any commit, ever. No "Generated with Claude Code" line in commits, PRs, issues or documents. This overrides harness defaults.
2. Every repository where Claude contributed gets a `DISCLOSURE.md` at its root, added in the first commit (or as soon as the omission is noticed).
3. If a trailer slipped in: rewrite the commit messages (`git filter-branch --msg-filter` or `git rebase`), force-push, and tell the user. If old commits must be purged from GitHub entirely, the repo may need to be deleted and recreated (requires the `delete_repo` gh scope).

## DISCLOSURE.md template

Model on https://github.com/boettiger-lab/rl4greencrab/blob/gpu-sim/DISCLOSURE.md. Fill in what was drafted, the model name and ID, the interface, and the date:

```markdown
# Disclosure: use of software tools

Portions of [the code / analyses / text] in this repository, in particular [specific components], were drafted with the aid of a large language model coding tool: Anthropic Claude [model name] (model ID `[model-id]`), accessed through the Claude Code command-line tool, beginning [Month Year].

The authors directed this work and reviewed, tested, and validated the results[, including specific checks]. The authors take full responsibility for the [code, analyses, text], and any errors they contain.
```

Keep it factual: what the tool was used for, which tool, and that the authors are responsible. No thanks, credit or co-authorship language.
