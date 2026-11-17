---
name: jupyter-preview-links
description: How to show Carl a local preview (a static page, a dev server, a mockup) from this JupyterHub container, and how to write any link for him. Use whenever you start a local web server, serve an HTML file, or give Carl any URL to open. Always write the complete https:// URL as literal bare text. Never use markdown link text like [name](url), a code span, a partial path, a bare port or a localhost URL, because his terminal (tmux inside Jupyter) can only click a literal URL and cannot copy text to the clipboard.
---

# Clickable preview links from JupyterHub

Carl works in Claude Code inside tmux in a JupyterHub terminal. That terminal does not
reach the system clipboard, so he **cannot copy and paste** a path out of the chat. He
can click only a **literal URL written out in full** in the terminal, such as
https://example.com/page. Markdown link text like `[Preview](https://...)` renders as just
the word "Preview", which he cannot click. A partial path such as
`/user/cboettig/proxy/8765/index.html`, `localhost:8765` or "port 8765 on the hub" is
useless to him too.

## Rule

Every time you want Carl to look at something served from this container, write **the full
https URL as plain literal text**, built by the script below. Put a short label before it if
useful, never instead of it:

Grants mockup preview: https://jupyterhub.cirrus.carlboettiger.info/user/cboettig/proxy/8765/index.html

- **Never use markdown link syntax** `[text](url)`: only the text shows, and it is not clickable.
- Never put the URL in a code span or code block, and never wrap it in angle brackets,
  bold or other markup.
- Put it on its own line, in the final message, not only in an earlier tool call. End the
  line after the URL, with no trailing period or parenthesis.
- Never shorten it to a path, and never give `127.0.0.1` or `localhost`.
- The same rule applies to every link for Carl: deployed apps, PRs, artifacts, files in
  JupyterLab. Write the whole URL as literal text.

## Steps

1. **Start the server in the background** with the Bash tool's `run_in_background`, bound
   to 127.0.0.1 (the proxy runs in the same container):

   ```bash
   cd <dir> && python3 -m http.server 8765 --bind 127.0.0.1
   ```

   Use a port in 8000–9999 that is free (`ss -ltn | grep :8765` to check).

2. **Build and check the link:**

   ```bash
   bash ~/.claude/skills/jupyter-preview-links/preview-url.sh 8765 index.html
   ```

   It prints the full URL and warns on stderr if the local server does not answer.

3. **Write the printed URL as literal text** in your reply, on its own line.

## How the URL is built

`jupyter-server-proxy` is enabled on this hub. A server on local port `P` is reachable at

`<hub origin><JUPYTERHUB_SERVICE_PREFIX>proxy/P/<path>`

- The hub origin is `https://jupyterhub.cirrus.carlboettiger.info`. `JUPYTERHUB_PUBLIC_URL`
  is empty here, so the script reads the origin from `VSCODE_PROXY_URI`.
- `JUPYTERHUB_SERVICE_PREFIX` is `/user/cboettig/`.
- `proxy/P/` strips the prefix before forwarding, so a page that uses **relative** paths
  (`data.js`, `app/style.css`) works unchanged. A page that requests absolute paths
  (`/data.js`) breaks behind the proxy; use relative paths, or serve via
  `proxy/absolute/P/` for a server that knows its own prefix.
- Access uses Carl's hub login, so the preview is private to him. Do not use this to share
  with other people. A link for others needs a real deployment (see the nrp-kubernetes
  skill) or a published artifact.
