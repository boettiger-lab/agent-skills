#!/usr/bin/env bash
# Apply a branch-protection ruleset to a GitHub repo.
# Also enforces squash-merge-only at the repo level.
#
# Usage:
#   apply-ruleset.sh OWNER/REPO [standard|strict]
#
# standard (default): require PR, no approval required, stale reviews kept
# strict:             require PR, 1 approval, dismiss stale reviews
set -euo pipefail

REPO="${1:?Usage: apply-ruleset.sh OWNER/REPO [standard|strict]}"
PROFILE="${2:-standard}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

case "$PROFILE" in
  standard) RULESET_FILE="$SCRIPT_DIR/ruleset-standard.json" ;;
  strict)   RULESET_FILE="$SCRIPT_DIR/ruleset-strict.json" ;;
  *) echo "Unknown profile: $PROFILE (use 'standard' or 'strict')" >&2; exit 1 ;;
esac

echo "==> Enforcing squash-merge-only on $REPO"
gh api -X PATCH "repos/$REPO" \
  -f allow_squash_merge=true \
  -f allow_merge_commit=false \
  -f allow_rebase_merge=false \
  -f delete_branch_on_merge=true \
  --silent

# Check for an existing ruleset with the same name and update it, or create new
RULESET_NAME=$(jq -r '.name' "$RULESET_FILE")
EXISTING_ID=$(gh api "repos/$REPO/rulesets" --jq ".[] | select(.name == \"$RULESET_NAME\") | .id" 2>/dev/null || true)

if [ -n "$EXISTING_ID" ]; then
  echo "==> Updating existing ruleset '$RULESET_NAME' (id: $EXISTING_ID) on $REPO"
  gh api -X PUT "repos/$REPO/rulesets/$EXISTING_ID" \
    --input "$RULESET_FILE" \
    --silent
else
  echo "==> Creating ruleset '$RULESET_NAME' on $REPO"
  gh api -X POST "repos/$REPO/rulesets" \
    --input "$RULESET_FILE" \
    --silent
fi

echo "==> Done. Ruleset '$RULESET_NAME' ($PROFILE) active on $REPO"
