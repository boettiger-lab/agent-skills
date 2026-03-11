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

## Session start (human runs once)

```bash
gh-agent-unlock   # YubiKey PIN + touch; decrypts key to /dev/shm
```

After this, `git push`, `git pull`, `gh pr create`, `gh issue comment`, etc. all just work.
No token exports, no per-repo setup, no credential flags needed.

## App identity

Actions appear as `boettiger-lab-llm-agent[bot]` in the GitHub audit log.

| Field | Value |
|---|---|
| App name | `boettiger-lab-llm-agent` |
| App ID | `3047595` |
| Organization | `boettiger-lab` |

## Troubleshooting

**Auth fails** — ask the human to run `gh-agent-unlock` (requires physical YubiKey).

**Stale token in remote URL** — if a remote URL contains `x-access-token:ghs_...`, fix it:
```bash
git remote set-url origin https://github.com/boettiger-lab/repo.git
```
Never embed tokens in remote URLs; always use clean `https://github.com/...` URLs.
