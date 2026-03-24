---
name: github-rulesets
description: "Apply preferred branch-protection rulesets and squash-merge-only settings to GitHub repos. Two profiles: 'standard' (no approval required) for smaller projects and 'strict' (1 approval, dismiss stale reviews) for larger ones. TRIGGER when: setting up a new repo, applying branch protection, configuring merge settings, or the user mentions rulesets."
license: Apache-2.0
compatibility: "Requires gh CLI authenticated with admin access to the target repo."
metadata:
  author: boettiger-lab
  version: "1.0"
---

# GitHub Repository Rulesets

Apply branch-protection rulesets and merge settings to repos. Two profiles available:

| Profile | Approvals | Dismiss stale reviews | Use for |
|---|---|---|---|
| `standard` | 0 | no | smaller / solo projects |
| `strict` | 1 | yes | larger / team projects |

Both profiles enforce: require PR, block deletion, block force push, squash-merge-only, delete branch on merge.

## How to apply

Run the shell script directly:

```bash
/home/cboettig/.claude/skills/github-rulesets/apply-ruleset.sh OWNER/REPO [standard|strict]
```

Or use `gh` one-liners directly:

### Squash-merge-only + delete branch on merge

```bash
gh api -X PATCH repos/OWNER/REPO -f allow_squash_merge=true -f allow_merge_commit=false -f allow_rebase_merge=false -f delete_branch_on_merge=true --silent
```

### Create/apply the ruleset

```bash
# standard (no approval required):
gh api -X POST repos/OWNER/REPO/rulesets --input /home/cboettig/.claude/skills/github-rulesets/ruleset-standard.json --silent

# strict (1 approval, dismiss stale):
gh api -X POST repos/OWNER/REPO/rulesets --input /home/cboettig/.claude/skills/github-rulesets/ruleset-strict.json --silent
```

### Update an existing ruleset

```bash
# Find the ruleset ID:
gh api repos/OWNER/REPO/rulesets --jq '.[].id'

# Update it:
gh api -X PUT repos/OWNER/REPO/rulesets/RULESET_ID --input /home/cboettig/.claude/skills/github-rulesets/ruleset-standard.json --silent
```

## What each ruleset does

The JSON payloads at `ruleset-standard.json` and `ruleset-strict.json` create a ruleset named `default-branch-protection` targeting `~DEFAULT_BRANCH` with these rules:

- **`deletion`** — prevents branch deletion
- **`non_fast_forward`** — blocks force pushes
- **`pull_request`** — requires a PR to merge (approval count and stale-review settings vary by profile)

The `apply-ruleset.sh` script is idempotent: it updates an existing ruleset with the same name rather than creating duplicates.

## Notes

- Rulesets require the caller to have admin access to the repo.
- The `~DEFAULT_BRANCH` ref pattern automatically targets whatever the repo's default branch is (main, master, etc.).
- Repo-level merge settings (squash-only) are separate from rulesets and set via `PATCH repos/OWNER/REPO`.
