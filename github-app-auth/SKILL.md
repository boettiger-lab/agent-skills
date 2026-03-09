---
name: github-app-auth
description: "Authenticate to GitHub using the boettiger-lab-llm-agent GitHub App. Covers minting installation tokens from an age-encrypted private key, git push/pull via credential helper, gh CLI usage, and the full session workflow. TRIGGER when an agent needs to: push to GitHub, create/comment on PRs or issues, use gh CLI, or perform any GitHub API operation in the boettiger-lab org."
license: Apache-2.0
compatibility: "Requires age-plugin-yubikey, age, openssl, jq, curl, and the encrypted key at the path noted below."
metadata:
  author: boettiger-lab
  version: "1.3"
---

# GitHub App Authentication: boettiger-lab-llm-agent

Agents in the `boettiger-lab` org authenticate as the `boettiger-lab-llm-agent` GitHub App,
not as a personal user. This gives scoped, auditable, time-limited access.

## App Details

| Field | Value |
|---|---|
| App name | `boettiger-lab-llm-agent` |
| App ID | `3047595` |
| Organization | `boettiger-lab` |
| Encrypted private key | `~/Documents/github/boettiger-lab/coding-agent/github-app-private-key.pem.age` |
| Decrypted key (RAM) | `/dev/shm/github-app-private-key.pem` (present only when unlocked) |
| Token script | `~/Documents/github/boettiger-lab/coding-agent/scripts/get-github-token.sh` |

## Token Lifetime

| Token | Lifetime | Purpose |
|---|---|---|
| JWT | 10 min max | Exchange only — never used for API calls |
| Installation access token | 1 hour | All GitHub API calls and git operations |

## Session Start (requires human with YubiKey)

```bash
gh-agent-unlock   # prompts for PIV PIN + physical touch; decrypts key to /dev/shm
```

Plain executable in `~/.local/bin/`. Works from any terminal. Does not affect the
calling shell's environment.

## git push / pull

A git credential helper (`git-credential-github-app` in `~/.local/bin/`) mints tokens
automatically when git needs them. It must be configured per repo:

```bash
git config --local credential.https://github.com.helper ""
git config --local --add credential.https://github.com.helper github-app
```

After this, `git push` and `git pull` just work with no further token management.

**Critical rule: never put a token in a remote URL.**
Always keep remote URLs clean:
```bash
# Correct:
git remote set-url origin https://github.com/boettiger-lab/myrepo.git

# Wrong — never do this:
# git remote set-url origin https://x-access-token:ghs_...@github.com/...
```

A token embedded in a remote URL will be cached by git and eventually expire,
causing mysterious auth failures that are hard to debug.

## gh CLI

The `gh` command is not pre-configured for app auth. Pass the token explicitly:

```bash
export GITHUB_APP_ID=3047595
export GITHUB_APP_PRIVATE_KEY_PATH=/dev/shm/github-app-private-key.pem
token=$(~/Documents/github/boettiger-lab/coding-agent/scripts/get-github-token.sh)

GITHUB_TOKEN="$token" gh pr create --title "..." --body "..."
GITHUB_TOKEN="$token" gh issue comment 42 --body "..."
GITHUB_TOKEN="$token" gh api /repos/boettiger-lab/myrepo/issues
```

Or export for a longer-lived script:

```bash
export GITHUB_TOKEN="$token"
gh pr list
gh repo view
```

## curl directly

```bash
curl -s \
  -H "Authorization: Bearer $token" \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  https://api.github.com/repos/boettiger-lab/myrepo/issues
```

## Token Refresh

Tokens expire after 1 hour. The credential helper mints a fresh token on each git
operation automatically. For `gh` calls, re-run the token script — no PIN/touch needed
as long as the key is still in `/dev/shm`:

```bash
token=$(~/Documents/github/boettiger-lab/coding-agent/scripts/get-github-token.sh)
```

## Session End

```bash
gh-agent-lock     # wipes /dev/shm/github-app-private-key.pem
```

## Troubleshooting

**"Private key not found"** — Run `gh-agent-unlock` first (requires YubiKey).

**git push fails with "Invalid username or token"** — Check for a stale token in the
remote URL: `git remote get-url origin`. If it contains `x-access-token:ghs_...`,
fix it: `git remote set-url origin https://github.com/boettiger-lab/repo.git`
Then clear the credential cache: `git credential-cache exit`

**"Could not find boettiger-lab installation"** — Check:
https://github.com/organizations/boettiger-lab/settings/installations

**gh returns 401 mid-session** — Token expired. Re-run the token script.

## Security Notes

- Never put tokens in remote URLs — use the credential helper instead
- Never commit the `.pem` or a plaintext token to git
- The `.pem.age` file is safe to commit — requires the physical YubiKey to decrypt
- `/dev/shm/github-app-private-key.pem` is mode 600 — readable only by your user
- If the YubiKey is lost, rotate immediately at:
  https://github.com/organizations/boettiger-lab/settings/apps/boettiger-lab-llm-agent
