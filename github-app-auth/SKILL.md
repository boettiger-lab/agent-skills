---
name: github-app-auth
description: "Authenticate to GitHub using the boettiger-lab-llm-agent GitHub App. Covers minting installation tokens from an age-encrypted private key, git push/pull via credential helper, gh CLI usage, and the full session workflow. TRIGGER when an agent needs to: push to GitHub, create/comment on PRs or issues, use gh CLI, or perform any GitHub API operation in the boettiger-lab org."
license: Apache-2.0
compatibility: "Requires age-plugin-yubikey, age, openssl, jq, curl, and the encrypted key at the path noted below."
metadata:
  author: boettiger-lab
  version: "2.0"
---

# GitHub App Authentication: boettiger-lab-llm-agent

Agents in the `boettiger-lab` org authenticate as the `boettiger-lab-llm-agent` GitHub App.
After the human has run `gh-agent-unlock`, **use `git` and `gh` exactly as you normally would** —
credential injection and token refresh are fully automatic.

## Session commands (human runs)

```bash
gh-agent-unlock   # YubiKey PIN + touch; decrypts key to /dev/shm → all git/gh uses App identity
gh-agent-lock     # wipe key from /dev/shm → all git/gh reverts to personal gh credentials
```

**Scope:** The App only has access to `boettiger-lab` org. When unlocked, pushes to any other org
(e.g. `espm-288`, `UCB-R-Users`) will fail. Run `gh-agent-lock` to revert to personal auth.

After `gh-agent-unlock`, `git push`, `git pull`, `gh pr create`, `gh issue comment`, etc. all just work.
No token exports, no per-repo setup, no credential flags needed.

## What the App cannot do — ask the human instead

The App token does **not** have admin/org-level permissions. Operations that require them will fail with a GraphQL or 403 error. When this happens, ask the human to do it directly — do **not** ask them to run `gh-agent-unlock`, as that won't help.

| Operation | Why it fails | What to ask |
|---|---|---|
| `gh repo create` | Requires org admin or user OAuth scope | "Please create the repo `boettiger-lab/<name>` on GitHub, then I'll push." |
| Changing repo visibility | Requires admin permission | Ask human to change via GitHub UI |
| Managing org members/teams | Org admin only | Ask human directly |

In general: repo creation, deletion, and org settings always require the human.

## App identity

Actions appear as `boettiger-lab-llm-agent[bot]` in the GitHub audit log.

| Field | Value |
|---|---|
| App name | `boettiger-lab-llm-agent` |
| App ID | `3047595` |
| Organization | `boettiger-lab` |

## Troubleshooting

**Can't push to a non-boettiger-lab org (e.g. espm-288)** — the App key is unlocked and intercepting
auth. Run `gh-agent-lock` to revert to personal credentials. Check with:
```bash
ls /dev/shm/github-app-private-key.pem   # exists → locked; missing → personal auth active
```

**Auth fails for boettiger-lab** — ask the human to run `gh-agent-unlock` (requires physical YubiKey).

**Stale token in remote URL** — if a remote URL contains `x-access-token:ghs_...`, fix it:
```bash
git remote set-url origin https://github.com/boettiger-lab/repo.git
```
Never embed tokens in remote URLs; always use clean `https://github.com/...` URLs.
