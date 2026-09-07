# agent-skills

Providing appropriate context and knowledge our agents need to succeed.

[Agent skills](https://agentskills.io/home)

## What is here

| Skill | For |
|-------|-----|
| `boettiger-lab-stack` | Map of the boettiger-lab data-and-agent stack — which GitHub repo owns which piece of the data → STAC → MCP → LLM-agent chain |
| `cng-datasets` | Process geospatial datasets into cloud-native formats (GeoParquet, PMTiles, H3 hex Parquet) using the cng-datasets CLI and NRP Kubernetes |
| `duckdb-spatial` | Critical gotchas for DuckDB spatial extension: the ST_Read() vs read_parquet() distinction, vendored GDAL limitations, S3 secret configuration for… |
| `gdal-spatial` | Read and convert remote geospatial files with GDAL/OGR |
| `github-app-auth` | Authenticate to GitHub using the boettiger-lab-llm-agent GitHub App |
| `github-rulesets` | Apply preferred branch-protection rulesets and squash-merge-only settings to GitHub repos |
| `k8s-never-force-delete` | Kubernetes deletion safety — never force-delete |
| `no-ai-attribution` | Authorship and attribution policy — Claude is a tool, never an author or co-author |
| `nrp-k8s` | Deploy and manage workloads on the NRP Nautilus Kubernetes cluster |
| `nrp-s3` | Manage S3 object storage on the NRP (National Research Platform) Nautilus cluster, which uses Ceph S3 (not AWS) |
| `oci-artifacts` | Use when storing, versioning, or sharing large files alongside a GitHub repo — model checkpoints, datasets, build artifacts, binaries, fixtures —… |
| `python-env` | Never install into or run the system Python |
| `stac-navigation` | Use when browsing, querying, or reasoning about what datasets exist in a STAC catalog — especially before concluding a dataset is missing or absent |

## Working with Claude Code (via CLI or VSCode)

Clone to `~/.claude/skills`:

```bash
git clone https://github.com/boettiger-lab/agent-skills ~/.claude/skills
```

`git clone` refuses a directory that already exists and is non-empty, so if you
already have skills there, move them aside first (and open a PR here for any
worth keeping) rather than deleting them:

```bash
mv ~/.claude/skills ~/.claude/skills.bak
git clone https://github.com/boettiger-lab/agent-skills ~/.claude/skills
```

Other clients can be instructed to load these skills on demand by having the
model copy their metadata into AGENTS.md or similar.

### These skills are not the whole configuration

A skill loads **on demand**, when its description matches what is happening.
That is right for knowledge ("how does rclone work against Ceph") and wrong for
standing rules, which have to be in force before anything triggers them. Two
other files carry those, and neither lives here:

- `~/.claude/CLAUDE.md` — injected into every session unconditionally.
- `~/.claude/settings.json` — mechanical enforcement (`includeCoAuthoredBy`),
  plus the environment description and soft-deny list.

The attribution policy is deliberately carried in all three places: always-on
prose, a triggered skill, and a setting. Cloning this repo alone does not move
it. Do not copy `~/.claude/.credentials.json` between machines — re-authenticate.

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

## Adding a skill

Every skill is a directory with a `SKILL.md` whose YAML frontmatter carries at
least `name` and `description`. **Without frontmatter a skill cannot be indexed
and will never load** — write the description as the conditions that should
trigger it, not as a summary of the contents.
