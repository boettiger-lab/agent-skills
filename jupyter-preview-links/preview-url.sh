#!/usr/bin/env bash
# Print the full, clickable JupyterHub proxy URL for a server on a local port,
# after checking that the server answers.
#
# Usage: preview-url.sh <port> [path]
#   preview-url.sh 8765 index.html
#   -> https://jupyterhub.cirrus.carlboettiger.info/user/cboettig/proxy/8765/index.html
set -euo pipefail

port="${1:?usage: preview-url.sh <port> [path]}"
path="${2:-}"
path="${path#/}"

# Public origin of the hub. JUPYTERHUB_PUBLIC_URL is empty on this hub, so fall
# back to the origin in VSCODE_PROXY_URI, then to the known hub host.
origin="${JUPYTERHUB_PUBLIC_URL:-}"
if [ -z "$origin" ] && [ -n "${VSCODE_PROXY_URI:-}" ]; then
    origin=$(printf '%s' "$VSCODE_PROXY_URI" | sed -E 's#^(https?://[^/]+).*#\1#')
fi
origin="${origin:-https://jupyterhub.cirrus.carlboettiger.info}"
origin="${origin%/}"

prefix="${JUPYTERHUB_SERVICE_PREFIX:-/user/${JUPYTERHUB_USER:-cboettig}/}"

url="${origin}${prefix}proxy/${port}/${path}"

code=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:${port}/${path}" || true)
if [ "$code" != "200" ]; then
    echo "WARNING: http://127.0.0.1:${port}/${path} returned ${code:-no answer}; start the server first." >&2
fi
echo "$url"
