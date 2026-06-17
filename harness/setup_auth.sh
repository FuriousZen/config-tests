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

# Quick, non-fatal connectivity check. MUST NOT be able to block the build:
# - `--format json` forces machine output (the default renderer expects a TTY,
#   which postCreate doesn't have, and would otherwise block).
# - `timeout` caps it so a slow/hung call can never stall the container build.
if command -v opencode >/dev/null 2>&1; then
  echo "[auth] verifying NIM auth (tiny probe, 45s cap)…"
  if timeout 45 opencode run "say ok" -m nvidia/mistralai/mistral-small-4-119b-2603 \
       --pure --format json --dangerously-skip-permissions \
       >/tmp/nim-probe.json 2>/dev/null \
     && [ -s /tmp/nim-probe.json ] \
     && ! grep -q '"type":"error"' /tmp/nim-probe.json; then
    echo "[auth] NIM auth OK."
  else
    echo "[auth] NOTE: probe inconclusive (timeout/empty/401). auth.json is" >&2
    echo "[auth] already written — verify directly with: opencode auth list" >&2
  fi
fi
