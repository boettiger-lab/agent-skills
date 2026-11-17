---
name: jupyterhub-user-config
description: >
  Per-user settings on Carl's JupyterHubs (boettiger-lab/k8s, boettiger-lab/nautilus,
  and the Berkeley datahub via PRs from his fork), starting with git commit identity.
  Use before changing what a hub puts in users' pod environment, when commits show up
  as "jovyan <jovyan@noreply.invalid>", "Ubuntu" or "Default User", or when deciding
  whether a setting belongs in the rocker/ml image or in hub config. Git identity
  needs no hub config: the image derives it from JUPYTERHUB_USER.
---

# Per-user settings on Carl's JupyterHubs

## The split: image defaults, hub specifics

The rocker/ml images (`rocker-org/ml`) ship generic defaults that must work on **any**
hub and in a plain `docker run`. Prefer build-time settings in standard system
locations (`/etc`, `ENV`) over runtime code; Carl is wary of startup hooks. Runtime
code is justified only when the value can only be known at runtime and no hub can be
relied on to supply it, as with the per-user git email; it then lives in the image's
existing Jupyter startup hook, changes only the server's environment, and writes
nothing to `$HOME`. Deployment-specific settings go in that hub's config, but the
campus datahub may not adopt per-image config, so don't make the image depend on it.
`rocker-org/ml`'s `AGENTS.md` has the image side in detail.

A user's own config (`~/.gitconfig`, `~/.config/gh/…`, on the persistent HOME
volume) must always win over anything the image or the hub sets.

## Git commit identity

Needs **no hub configuration**. The rocker/ml image handles it (since Nov 2026,
rocker-org/ml#65 and the follow-up PR):

- No `user.name` / `user.email` in `/etc/gitconfig`.
- `ENV EMAIL=jovyan@noreply.invalid`. `EMAIL` is git's lowest-precedence source, below
  `~/.gitconfig`, so it never overrides a user. The `jovyan` account's full name is
  `jovyan`, which git uses for the name. (An empty full name makes git refuse to commit.)
- The image's Jupyter startup hook replaces that default with
  `<JUPYTERHUB_USER>@noreply.invalid`, keeping only the part before an `@` for
  email-style usernames. Every hub sets `JUPYTERHUB_USER`, so this works on the campus
  datahub, k8s and nautilus alike. RStudio gets the same value via `Renviron.site`.

Resulting emails: k8s `cboettig@noreply.invalid` (GitHub login), datahub
`jsmith@noreply.invalid` (CalNet ID; `strip_email_domain: berkeley.edu`), nautilus
`cboettig@noreply.invalid` (CILogon username `cboettig@berkeley.edu`, cut at the `@`).

If a hub ever does need a different value, set `EMAIL` in its pod environment
(`hub.config.KubeSpawner.environment` or `singleuser.extraEnv`); the hook leaves a
hub-set `EMAIL` alone. Rules if you do:

- **Set only `EMAIL`.** Never `GIT_AUTHOR_NAME`, `GIT_COMMITTER_NAME` or the
  `GIT_*_EMAIL` variables: they outrank `~/.gitconfig` and would override users.
- **Use the `.invalid` domain**, not `noreply.com` (a real, owned domain).
- **Don't look up real emails or GitHub IDs** from auth state; Carl does not want
  commits to disclose addresses the user did not choose. Users who want GitHub credit
  set their own `user.email`.

Other images on these hubs (BinderHub/repo2docker builds, datahub images not based on
rocker/ml) get none of this, and may set their own identity in `/etc/gitconfig`.

## The hubs

- **boettiger-lab/k8s:** config `services/jupyterhub/public-config.yaml`, deployed by
  hand with `./up.sh`. `GitHubOAuthenticator`. Its images (`images/Dockerfile`,
  `images/Dockerfile.gpu`) are built `FROM` rocker-org images; a watch workflow
  rebuilds the CPU one within 6 hours of `ml-spatial` publishing.
- **boettiger-lab/nautilus (NRP):** config `values.yaml`. Active login is
  `authenticator_class: cilogon` with `username_claim: email`, despite a leftover
  `GitHubOAuthenticator` section.
- **Berkeley datahub (berkeley-dsep-infra/datahub):** never push upstream. Branch on
  Carl's fork `cboettig/datahub` and PR against upstream, as in
  https://github.com/berkeley-dsep-infra/datahub/pull/8422. Read the
  `human-communication-consent` skill first. Shared `hub/values.yaml` uses
  `CanvasOAuthenticator` (bCourses); per-deployment config is
  `deployments/<hub>/config/common.yaml`. Campus staff may not adopt per-image config,
  so prefer fixes that live in the image.

## gh expiring tokens

gh (>= 2.103.0) supports `gh auth login --expiring` and
`gh config set expiring_credentials enabled`. gh has no system-wide config and no
environment variable for this, so neither the image nor a hub can make it the default
without writing into each user's HOME. Don't try; it is opt-in for users until gh
makes it the default upstream. The key is `expiring_credentials`, not
`prefer_expiring_credentials` as the release notes partly say.
