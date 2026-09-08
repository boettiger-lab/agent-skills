# agent-skills

Context and knowledge our agents need to succeed.

[Agent skills](https://agentskills.io/home)

## Install the rules globally; keep the knowledge with its repo

A skill's `description` is loaded into **every session in every repo** so the
model can decide whether to trigger it. That is a standing cost, and a standing
chance of firing when it is not wanted. So the default is not "clone
everything" — it is:

**Globally, in `~/.claude/skills/` — rule-shaped skills only.** Things that must
hold everywhere, that no single repo would own, and that go stale slowly:

| Skill | Why global |
|-------|------------|
| `no-ai-attribution` | Authorship policy. Applies to every commit in every repo. |
| `k8s-never-force-delete` | Destructive-action guard. Wanted wherever a cluster is reachable. |
| `python-env` | "Never install into system Python." True everywhere; 30 lines. |

**Per repo, in `<repo>/.claude/skills/` — everything else.** Domain knowledge
belongs beside the code it describes, where it is version-matched, reviewed in
the same PR as the change it documents, and only loaded when someone is working
in that repo:

```bash
mkdir -p .claude/skills
cp -r /path/to/agent-skills/cng-datasets .claude/skills/
git add .claude/skills && git commit -m "Add cng-datasets skill to the repo"
```

The path matters: **`.claude/skills/<name>/SKILL.md`**. A bare `skills/` at the
repo root is not a discovery location — skills there are never indexed and
never load, however good they are.

This repo stays the library those copies come from, and the place to send a fix
that is not repo-specific.

### Why not just clone it all

We ran a full week of work on `boettiger-lab/datasets` — CLI changes, k8s
workflow generators, Armada, GDAL, DuckDB, H3 — with none of the domain skills
installed, and did not miss them: `AGENTS.md`, `docs/` and the issue threads
carried it, and carried it *current*, while the `cng-datasets` skill here had
drifted five months behind the CLI. Knowledge duplicated away from the code
goes stale in exactly the way the code does not.

### Setup

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/boettiger-lab/agent-skills /tmp/agent-skills
for s in no-ai-attribution k8s-never-force-delete python-env; do
  cp -r /tmp/agent-skills/$s ~/.claude/skills/
done
```

Clone the whole thing into `~/.claude/skills` only if you genuinely want every
skill live in every session. Note `git clone` refuses a non-empty target, so on
a machine that already has skills, move them aside first rather than deleting
them — and open a PR here for any worth keeping.

### These skills are not the whole configuration

A skill loads **on demand**, when its description matches. That is right for
knowledge and wrong for standing rules, which must be in force before anything
triggers them. Two files carry those, and neither lives here:

- `~/.claude/CLAUDE.md` — injected into every session unconditionally.
- `~/.claude/settings.json` — mechanical enforcement (`includeCoAuthoredBy`),
  plus the environment description and soft-deny list.

The attribution policy is deliberately carried in all three: always-on prose, a
triggered skill, and a setting. Cloning this repo alone does not move it. Do
not copy `~/.claude/.credentials.json` between machines — re-authenticate.

### When working with devcontainers

symlink the skills dir, e.g.

```bash
{
  // ... your existing devcontainer config ...

  "mounts": [
    "source=${localEnv:HOME}${localEnv:USERPROFILE}/.claude/skills,target=/home/vscode/.claude/skills,type=bind,consistency=cached"
  ]
}
```

## The library

Rule-shaped, install globally:

| Skill | For |
|-------|-----|
| `no-ai-attribution` | Claude is a tool, never an author or co-author |
| `k8s-never-force-delete` | Never force-delete; diagnose stuck resources instead |
| `python-env` | Never install into or run the system Python |

Cross-repo, install globally only if you route between repos often:

| Skill | For |
|-------|-----|
| `boettiger-lab-stack` | Which repo owns which piece of the data → STAC → MCP → agent chain |

Domain knowledge — copy into the repo it serves:

| Skill | Belongs with |
|-------|--------------|
| `cng-datasets` | `datasets` / `data-workflows` |
| `duckdb-spatial` | any repo querying spatial parquet |
| `gdal-spatial` | `datasets`, `data-workflows` |
| `nrp-k8s` | any repo deploying to Nautilus |
| `nrp-s3` | any repo writing to Ceph S3 |
| `stac-navigation` | `data-workflows`, `mcp-data-server` |
| `oci-artifacts` | whichever repo ships large artifacts |
| `github-app-auth` | wherever the bot account pushes |
| `github-rulesets` | wherever branch protection is applied |

## Adding a skill

Every skill is a directory with a `SKILL.md` whose YAML frontmatter carries at
least `name` and `description`. **Without frontmatter a skill cannot be indexed
and will never load** — two skills here had shipped that way. Write the
description as the conditions that should trigger it, not as a summary of the
contents.
