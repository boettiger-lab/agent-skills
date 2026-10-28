---
name: stacked-pr-squash-merge
description: >
  Safely merging stacked or dependent pull requests. Read BEFORE squash-merging
  any PR when another open PR is based on its branch, or when merging several
  related PRs in sequence. Squash-merging a base PR and deleting its branch can
  auto-close the dependent PR, balloon its diff, or silently drop commits. Use
  whenever you run `gh pr merge`/`--delete-branch` on more than one related PR,
  or after pushing a late commit to an already-open PR.
metadata:
  author: boettiger-lab
  version: "1.0"
---

# Merging stacked / dependent PRs (the squash-drop gotcha)

**The bite:** when PR-B's base branch is PR-A's head branch (a *stacked* PR), or
when you push a late commit to an open PR right before merging, a
`squash` + `--delete-branch` on the base **bites**:

- **Deleting the base branch auto-closes the dependent PR.** GitHub closes PR-B
  when the branch it targets disappears (or retargets it to `main` with a now-wrong,
  ballooned diff that includes PR-A's changes).
- **Squash silently drops commits.** A squash collapses the *branch tip* into one
  commit. If the merged PR's head wasn't what you thought — a commit you pushed
  seconds before merging, or commits that really live in the base PR — those
  changes never reach `main`, even though the working tree/cluster you deployed
  from had them. `main` and reality then disagree.

## Safe procedure

1. **Prefer not to stack.** Rebase each branch directly onto `main` and open
   independent PRs. Independent PRs squash-merge in any order without interaction.

2. **If PRs are stacked, merge bottom-up, one at a time.** Before merging or
   deleting the base (PR-A), **retarget the dependent PR to `main` first**:
   ```bash
   gh pr edit <B> --base main      # retarget BEFORE deleting PR-A's branch
   ```
   Confirm the retarget, *then* merge PR-A. Do **not** pass `--delete-branch` on a
   base PR while any open PR still targets its branch.

3. **Fold late edits into one commit.** If you push a new commit to an
   already-open PR just before merging, either squash locally first or re-verify
   the PR head includes it (`gh pr view <n> --json commits`) before merging.

4. **Verify `main` after every squash-merge.** Don't trust the green "Merged".
   Confirm the merged branch actually landed *all* intended changes:
   ```bash
   git fetch origin -q
   git show origin/main:path/to/file | grep <the-change>
   ```
   Do this even when a deploy/cluster already shows the change — you may have
   applied from a local tree that had commits the squash dropped.

## Recovery

- **Dependent PR auto-closed:** reopen it, `gh pr edit <B> --base main`, rebase
  onto `main`, push.
- **Commits dropped from a squash:** land them via a small follow-up PR (a
  "reconcile main" PR) rather than re-opening the merged one.

## Real incident (2026-07-06, geo-agent-ops)

A fleet model-config roll: each app's PR carried a picker-entry commit, then a
`llm_model` default commit pushed later. Two of twelve squash-merges captured
**only the first commit** — `main` kept the old default while the deployed pods
already served the new one (applied from the local tree). The cross-check tool
caught one; the other slipped it (its value lived in a file the tool doesn't read)
and was only found by a manual `git show origin/main` sweep. Fixed with
follow-up default-only PRs. **Lesson: after squash-merging, always confirm `main`
contains everything — a squash is not a guarantee.**
