#!/usr/bin/env python3
"""Idempotently install the two experiment MCP servers and record how to launch
each one. Re-running is a no-op once both are present.

Outputs harness/mcp_runtime.json:
{
  "codebase-memory":  {"command": ["/abs/codebase-memory-mcp"], "environment": {...}},
  "codegraphcontext": {"command": ["/abs/.venv-cgc/bin/codegraphcontext","mcp","start"]}
}

- codebase-memory  -> DeusData/codebase-memory-mcp: self-contained static binary
  (SQLite at ~/.cache/codebase-memory-mcp), stdio, no args, no backend daemon.
- codegraphcontext -> PyPI `codegraphcontext`: stdio via `mcp start`, embedded
  graph DB (FalkorDB Lite / KuzuDB) by default, no Neo4j required.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HARNESS_DIR = Path(__file__).resolve().parent
MCP_RUNTIME_JSON = HARNESS_DIR / "mcp_runtime.json"
CGC_VENV = HARNESS_DIR / ".venv-cgc"

CBM_INSTALL_SH = "https://raw.githubusercontent.com/DeusData/codebase-memory-mcp/main/install.sh"


def log(msg: str) -> None:
    print(f"[setup] {msg}", flush=True)


def which(name: str) -> str | None:
    return shutil.which(name)


# ---------------------------------------------------------------------------
# codebase-memory-mcp (DeusData, Go static binary)
# ---------------------------------------------------------------------------
def ensure_codebase_memory() -> dict | None:
    bin_path = which("codebase-memory-mcp")
    if binary := (bin_path or _find_cbm_in_common_paths()):
        log(f"codebase-memory-mcp present: {binary}")
        return {"command": [binary], "environment": {}}

    log("codebase-memory-mcp not found — installing via one-line script…")
    try:
        subprocess.run(
            f"curl -fsSL {CBM_INSTALL_SH} | bash",
            shell=True, check=True,
        )
    except subprocess.CalledProcessError as e:
        log(f"install script failed ({e}). Try `brew install codebase-memory-mcp` "
            "or download a release binary, then re-run setup.")
        return None

    binary = which("codebase-memory-mcp") or _find_cbm_in_common_paths()
    if not binary:
        log("installed but binary not on PATH; check ~/.local/bin and your shell PATH.")
        return None
    log(f"installed codebase-memory-mcp: {binary}")
    return {"command": [binary], "environment": {}}


def _find_cbm_in_common_paths() -> str | None:
    for p in (Path.home() / ".local/bin/codebase-memory-mcp",
              Path("/usr/local/bin/codebase-memory-mcp"),
              Path("/opt/homebrew/bin/codebase-memory-mcp")):
        if p.exists() and os.access(p, os.X_OK):
            return str(p)
    return None


# ---------------------------------------------------------------------------
# codegraphcontext (PyPI, embedded graph DB)
# ---------------------------------------------------------------------------
def ensure_codegraphcontext() -> dict | None:
    cgc_bin = CGC_VENV / "bin" / "codegraphcontext"
    if not cgc_bin.exists():
        log("creating venv + installing codegraphcontext…")
        try:
            subprocess.run([sys.executable, "-m", "venv", str(CGC_VENV)], check=True)
            subprocess.run([str(CGC_VENV / "bin" / "pip"), "install", "--upgrade",
                            "pip", "codegraphcontext"], check=True)
        except subprocess.CalledProcessError as e:
            log(f"codegraphcontext install failed: {e}")
            return None

    if not cgc_bin.exists():
        log("codegraphcontext binary missing after install.")
        return None

    # Sanity check it launches at all.
    try:
        subprocess.run([str(cgc_bin), "--help"], capture_output=True, timeout=60)
    except Exception as e:
        log(f"warning: codegraphcontext --help failed: {e}")
    log(f"codegraphcontext present: {cgc_bin}")
    # Embedded DB default => no Neo4j env required. We isolate per-run data via
    # a CGC home dir set at config-build time in run_experiment.
    return {"command": [str(cgc_bin), "mcp", "start"], "environment": {}}


def main() -> int:
    runtime: dict[str, dict] = {}
    cbm = ensure_codebase_memory()
    if cbm:
        runtime["codebase-memory"] = cbm
    cgc = ensure_codegraphcontext()
    if cgc:
        runtime["codegraphcontext"] = cgc

    MCP_RUNTIME_JSON.write_text(json.dumps(runtime, indent=2))
    log(f"wrote {MCP_RUNTIME_JSON}")
    missing = {"codebase-memory", "codegraphcontext"} - runtime.keys()
    if missing:
        log(f"NOT READY — missing: {', '.join(sorted(missing))}. "
            "Those config columns will be skipped until installed.")
        return 1
    log("both MCP servers ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
