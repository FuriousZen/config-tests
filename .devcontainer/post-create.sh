#!/usr/bin/env bash
# Devcontainer bootstrap: install tooling, provision credentials, prepare
# fixture deps, and install both MCP servers. Runs once on container creation.
set -euo pipefail

corepack enable
npm install -g opencode-ai

bash harness/setup_auth.sh

(cd fixtures/react-app && npm install)

python3 harness/setup_mcps.py || echo "[post-create] WARNING: MCP setup incomplete — some configs will be skipped."
