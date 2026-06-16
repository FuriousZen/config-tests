#!/usr/bin/env bash
# Provision opencode's Nvidia NIM credential non-interactively, so no `/connect`
# / `opencode auth login` is needed inside the container.
#
# Reads the key from $NVIDIA_API_KEY and writes the exact file opencode expects:
#   $XDG_DATA_HOME/opencode/auth.json  (default ~/.local/share/opencode/auth.json)
#   { "nvidia": { "type": "api", "key": "<KEY>" }, ... }
set -euo pipefail

KEY="${NVIDIA_API_KEY:-}"
if [ -z "$KEY" ]; then
  echo "[auth] NVIDIA_API_KEY not set — skipping opencode auth bootstrap." >&2
  echo "[auth] Provide it via host env or .devcontainer/.env, then re-run" >&2
  echo "[auth]   bash harness/setup_auth.sh   (or 'opencode auth login')." >&2
  exit 0
fi

DIR="${XDG_DATA_HOME:-$HOME/.local/share}/opencode"
mkdir -p "$DIR"

python3 - "$DIR/auth.json" "$KEY" <<'PY'
import json, os, sys
path, key = sys.argv[1], sys.argv[2]
data = {}
if os.path.exists(path):
    try:
        data = json.load(open(path))
    except Exception:
        data = {}
data["nvidia"] = {"type": "api", "key": key}
with open(path, "w") as f:
    json.dump(data, f, indent=2)
os.chmod(path, 0o600)
print(f"[auth] wrote nvidia credential to {path}")
PY

# Quick, non-fatal connectivity check.
if command -v opencode >/dev/null 2>&1; then
  echo "[auth] verifying NIM auth (a tiny probe call)…"
  if opencode run "say: ok" -m nvidia/google/gemma-4-31b-it --pure \
       --dangerously-skip-permissions >/dev/null 2>&1; then
    echo "[auth] NIM auth OK."
  else
    echo "[auth] WARNING: probe call failed — key may be invalid/expired (401)." >&2
  fi
fi
