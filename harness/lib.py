"""Shared helpers for the OpenCode MCP-config experiment harness.

Keeps the orchestrator, judge, and aggregator consistent on paths, config
loading, opencode invocation, and metric extraction from session artifacts.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
HARNESS_DIR = Path(__file__).resolve().parent
ROOT_DIR = HARNESS_DIR.parent
TASKS_DIR = HARNESS_DIR / "tasks"
FIXTURES_DIR = ROOT_DIR / "fixtures"
RESULTS_DIR = ROOT_DIR / "results"
EXPERIMENT_JSON = HARNESS_DIR / "experiment.json"
# Written by setup_mcps.py: resolved launch commands for each MCP server.
MCP_RUNTIME_JSON = HARNESS_DIR / "mcp_runtime.json"


def _strip_json_comments(text: str) -> str:
    """experiment.json uses //-prefixed keys for inline docs; those are valid
    JSON keys, so nothing to strip. This is a hook for future .jsonc support."""
    return text


def load_experiment() -> dict[str, Any]:
    return json.loads(_strip_json_comments(EXPERIMENT_JSON.read_text()))


def load_mcp_runtime() -> dict[str, Any]:
    if not MCP_RUNTIME_JSON.exists():
        raise FileNotFoundError(
            f"{MCP_RUNTIME_JSON} missing — run `python harness/setup_mcps.py` first."
        )
    return json.loads(MCP_RUNTIME_JSON.read_text())


# ---------------------------------------------------------------------------
# opencode.json generation (per-run, project-local config)
# ---------------------------------------------------------------------------
# The two experiment MCP server keys. We ALWAYS list both and flip `enabled`,
# so a globally-registered MCP can never leak into the `control` cell. `--pure`
# (passed on the CLI) handles plugins; this handles MCP servers.
MCP_KEYS = {
    "codebase-memory": "codebase-memory",
    "codegraphcontext": "codegraphcontext",
}


def build_opencode_config(
    config_name: str, mcp_runtime: dict[str, Any], workdir: Path
) -> dict[str, Any]:
    """Return the dict to write as a workdir-local opencode.json for one cell.

    config_name is one of: control | codebase-memory | codegraphcontext.
    Exactly the named MCP is enabled; every other experiment MCP is explicitly
    disabled by key. Per-run state dirs (under workdir) keep each rep's memory /
    graph isolated so runs don't contaminate one another.
    """
    # Per-run, per-MCP env isolation so accumulated state can't leak across reps.
    per_run_env = {
        # codebase-memory documents CBM_CACHE_DIR as its full storage override.
        "codebase-memory": {"CBM_CACHE_DIR": str(workdir / ".cbm-cache")},
        # codegraphcontext documents no data-dir override, so isolate everything it
        # writes under ~/ (embedded FalkorDB/Kuzu DB + ~/.codegraphcontext) via HOME.
        "codegraphcontext": {
            "HOME": str(workdir / ".cgc-home"),
            "GIT_CONFIG_GLOBAL": str(Path.home() / ".gitconfig"),
        },
    }
    mcp: dict[str, Any] = {}
    for key in MCP_KEYS:
        rt = mcp_runtime.get(key)
        if not rt:
            # Server not installed/resolved; emit a disabled stub so the key is
            # still explicitly present (defends the control cell).
            mcp[key] = {"type": "local", "command": ["true"], "enabled": False}
            continue
        env = {**rt.get("environment", {}), **per_run_env.get(key, {})}
        mcp[key] = {
            "type": "local",
            "command": rt["command"],
            "environment": env,
            "enabled": (config_name == key),
        }
    return {"$schema": "https://opencode.ai/config.json", "mcp": mcp}


def write_workdir_config(workdir: Path, config_name: str, mcp_runtime: dict[str, Any]) -> None:
    cfg = build_opencode_config(config_name, mcp_runtime, workdir)
    (workdir / "opencode.json").write_text(json.dumps(cfg, indent=2))


# ---------------------------------------------------------------------------
# Workspace isolation
# ---------------------------------------------------------------------------
def make_clean_workdir(fixture: Path, dest: Path) -> Path:
    """Copy the pristine fixture into dest so every session starts identical, then
    initialize a throwaway git repo with a baseline commit.

    The fixture is tracked in the outer repo as plain files (no nested .git), so we
    create the repo here at runtime — `git_diff` then reports only the agent's edits
    (index vs the baseline HEAD).
    """
    if dest.exists():
        shutil.rmtree(dest)
    # Skip .git (we make a fresh one) and node_modules (huge; we symlink it).
    shutil.copytree(fixture, dest, ignore=shutil.ignore_patterns(".git", "node_modules"))
    # Share the fixture's installed deps instead of copying them per run, so
    # `tsc`/`vitest` (and the agent) can resolve them cheaply. Read-mostly; our
    # tasks add no deps.
    fixture_node_modules = fixture / "node_modules"
    if fixture_node_modules.is_dir() and not (dest / "node_modules").exists():
        try:
            (dest / "node_modules").symlink_to(fixture_node_modules, target_is_directory=True)
        except OSError:
            pass  # symlink unsupported -> tsc/vitest just won't run; verify records that
    # Keep harness artifacts + hidden verification assets out of the measured diff.
    (dest / ".gitignore").write_text(
        "\n".join([".gitignore", "opencode.json", ".opencode/", ".cbm-cache/",
                   ".cgc-home/", "node_modules/", "__tests__/__verify__/", ".verify/",
                   "__pycache__/", "*.pyc"]) + "\n"
    )
    # Baseline repo so post-run `git diff --cached` shows only what the agent changed.
    subprocess.run(["git", "-C", str(dest), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(dest), "add", "-A"], check=True)
    subprocess.run(
        ["git", "-C", str(dest), "-c", "user.email=harness@local",
         "-c", "user.name=harness", "commit", "-qm", "baseline"],
        check=True,
    )
    return dest


def git_diff(workdir: Path) -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(workdir), "add", "-A"],
            capture_output=True, text=True,
        )
        res = subprocess.run(
            ["git", "-C", str(workdir), "diff", "--cached"],
            capture_output=True, text=True,
        )
        return res.stdout
    except Exception as e:  # pragma: no cover
        return f"<git diff failed: {e}>"


# ---------------------------------------------------------------------------
# Session environment isolation
# ---------------------------------------------------------------------------
_ENV_PASSTHROUGH = frozenset({
    "PATH", "HOME", "NVIDIA_API_KEY", "TERM", "LANG", "LC_ALL",
    "USER", "LOGNAME", "SHELL", "TMPDIR",
})


def _seed_auth(xdg_data: Path) -> None:
    """Copy the real NIM auth.json into an isolated XDG_DATA_HOME so opencode
    can authenticate without seeing the global config/state dirs."""
    real_data = Path(os.environ.get(
        "XDG_DATA_HOME", Path.home() / ".local" / "share"))
    real_auth = real_data / "opencode" / "auth.json"
    if not real_auth.exists():
        return
    dst = xdg_data / "opencode"
    dst.mkdir(parents=True, exist_ok=True)
    shutil.copy2(real_auth, dst / "auth.json")


def build_session_env(cell_dir: Path) -> dict[str, str]:
    """Build a minimal, isolated environment for an opencode subprocess.

    Sets per-cell XDG dirs so the global ~/.config/opencode (which may register
    extra MCP servers or AGENTS.md) and ~/.local/share/opencode (session DB)
    never leak into the experiment session.
    """
    env = {k: v for k, v in os.environ.items() if k in _ENV_PASSTHROUGH}
    xdg_config = cell_dir / ".xdg-config"
    xdg_data = cell_dir / ".xdg-data"
    xdg_cache = cell_dir / ".xdg-cache"
    xdg_state = cell_dir / ".xdg-state"
    for d in (xdg_config, xdg_data, xdg_cache, xdg_state):
        d.mkdir(parents=True, exist_ok=True)
    _seed_auth(xdg_data)
    env["XDG_CONFIG_HOME"] = str(xdg_config)
    env["XDG_DATA_HOME"] = str(xdg_data)
    env["XDG_CACHE_HOME"] = str(xdg_cache)
    env["XDG_STATE_HOME"] = str(xdg_state)
    return env


def build_judge_env(tmpdir: str) -> dict[str, str]:
    """Minimal isolated environment for the LLM-judge subprocess."""
    env = {k: v for k, v in os.environ.items() if k in _ENV_PASSTHROUGH}
    base = Path(tmpdir)
    for name in ("config", "data", "cache", "state"):
        d = base / f".xdg-{name}"
        d.mkdir(parents=True, exist_ok=True)
        env[f"XDG_{name.upper()}_HOME"] = str(d)
    _seed_auth(base / ".xdg-data")
    return env


# ---------------------------------------------------------------------------
# Running opencode
# ---------------------------------------------------------------------------
@dataclass
class RunResult:
    session_id: str | None
    returncode: int
    wall_seconds: float
    timed_out: bool
    events_path: Path
    stderr: str


def run_opencode_session(
    message: str,
    model: str,
    workdir: Path,
    out_events: Path,
    timeout_seconds: int,
    session_env: dict[str, str] | None = None,
    extra_args: list[str] | None = None,
) -> RunResult:
    """Run one headless `opencode run` session, streaming JSONL events to disk."""
    cmd = [
        "opencode", "run", message,
        "-m", model,
        "--pure",                       # no plugins -> no interactive brainstorm skill
        "--format", "json",
        "--dangerously-skip-permissions",
        "--dir", str(workdir),
    ] + (extra_args or [])

    start = time.monotonic()
    timed_out = False
    with out_events.open("wb") as ev:
        proc = subprocess.Popen(cmd, stdout=ev, stderr=subprocess.PIPE,
                                cwd=str(workdir), env=session_env)
        try:
            _, stderr = proc.communicate(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            proc.kill()
            _, stderr = proc.communicate()
    wall = time.monotonic() - start

    session_id = _first_session_id(out_events)
    return RunResult(
        session_id=session_id,
        returncode=proc.returncode,
        wall_seconds=wall,
        timed_out=timed_out,
        events_path=out_events,
        stderr=(stderr or b"").decode("utf-8", "replace"),
    )


def iter_events(events_path: Path):
    """Yield parsed JSON objects from a JSONL events file, skipping bad lines."""
    if not events_path.exists():
        return
    for line in events_path.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            continue


def _first_session_id(events_path: Path) -> str | None:
    for ev in iter_events(events_path):
        sid = ev.get("sessionID") or ev.get("sessionId") or ev.get("session_id")
        if sid:
            return sid
    return None


def export_session(session_id: str, out_path: Path,
                   session_env: dict[str, str] | None = None) -> bool:
    """`opencode export <id>` -> authoritative session JSON. Returns success."""
    try:
        res = subprocess.run(
            ["opencode", "export", session_id],
            capture_output=True, text=True, timeout=120,
            env=session_env,
        )
        if res.returncode == 0 and res.stdout.strip():
            out_path.write_text(res.stdout)
            return True
    except Exception:
        pass
    return False


# ---------------------------------------------------------------------------
# Metric extraction
# ---------------------------------------------------------------------------
@dataclass
class Metrics:
    wall_seconds: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    cost_usd: float = 0.0
    tool_calls: int = 0
    mcp_tool_calls: int = 0
    assistant_turns: int = 0
    errored: bool = False
    timed_out: bool = False
    error_message: str = ""
    mcp_tools_used: list[str] = field(default_factory=list)

    def asdict(self) -> dict[str, Any]:
        return {**self.__dict__, "mcp_tools_used": list(self.mcp_tools_used)}


# Heuristic: recursively walk any JSON structure pulling token/cost/tool signals.

def _walk_usage(obj: Any, m: Metrics, _parent_key: str = "") -> None:
    if isinstance(obj, dict):
        if _parent_key == "usage":
            if "tokens" in obj and isinstance(obj["tokens"], dict):
                t = obj["tokens"]
                m.input_tokens += _as_int(t.get("input"))
                m.output_tokens += _as_int(t.get("output"))
                m.reasoning_tokens += _as_int(t.get("reasoning"))
            if "cost" in obj and isinstance(obj.get("cost"), (int, float)):
                m.cost_usd += float(obj["cost"])
        for k, v in obj.items():
            _walk_usage(v, m, _parent_key=k)
    elif isinstance(obj, list):
        for v in obj:
            _walk_usage(v, m, _parent_key=_parent_key)


def _as_int(v: Any) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def extract_metrics(
    run: RunResult,
    export_path: Path | None,
    mcp_tool_names: list[str],
) -> Metrics:
    """Combine wall-clock (from run) + token/cost (from export, authoritative)
    + tool-call counts (from the event stream)."""
    m = Metrics(wall_seconds=round(run.wall_seconds, 2), timed_out=run.timed_out)

    # --- tool calls + turns + errors from the JSONL event stream ---
    hint_set = frozenset(mcp_tool_names) if mcp_tool_names else frozenset()
    for ev in iter_events(run.events_path):
        etype = str(ev.get("type", ""))
        if etype == "error" or ev.get("error"):
            m.errored = True
            err = ev.get("error") or {}
            if isinstance(err, dict):
                data = err.get("data") or {}
                m.error_message = str(data.get("message") or err.get("name") or m.error_message)
        if "tool" in etype.lower():
            m.tool_calls += 1
            name = str(ev.get("tool") or ev.get("name") or "")
            if name in hint_set:
                m.mcp_tool_calls += 1
                if name not in m.mcp_tools_used:
                    m.mcp_tools_used.append(name)
        if etype in ("assistant", "step-finish"):
            m.assistant_turns += 1

    # --- authoritative tokens/cost from export.json if available ---
    if export_path and export_path.exists():
        try:
            _walk_usage(json.loads(export_path.read_text()), m)
        except Exception:
            pass

    if run.returncode != 0 and not m.errored:
        m.errored = True
        if not m.error_message:
            m.error_message = (run.stderr or "").strip()[-500:] or f"exit {run.returncode}"
    return m


# ---------------------------------------------------------------------------
# Session process summary (for the LLM judge)
# ---------------------------------------------------------------------------
_READ_TOOLS = frozenset({"read_file", "readFile", "Read", "cat", "view_file"})
_WRITE_TOOLS = frozenset({
    "write_file", "writeFile", "Write", "edit_file", "editFile", "Edit",
    "patch", "replace_in_file", "insert_code",
})
_PATH_KEYS = ("path", "file", "filePath", "file_path", "filename", "target")
MAX_TRAJECTORY = 50


def _extract_file_path(ev: dict[str, Any]) -> str:
    """Best-effort extraction of a file path from a tool-call event."""
    for container in (ev.get("input"), ev.get("args"), ev.get("arguments"), ev):
        if not isinstance(container, dict):
            continue
        for k in _PATH_KEYS:
            v = container.get(k)
            if isinstance(v, str) and v:
                return v
    return ""


def summarize_session_process(events_path: Path, metrics: Metrics) -> str:
    """Build a compact text summary of the agent's tool-call trajectory."""
    trajectory: list[str] = []
    read_counts: dict[str, int] = {}
    write_counts: dict[str, int] = {}

    for ev in iter_events(events_path):
        etype = str(ev.get("type", ""))
        if "tool" not in etype.lower():
            continue
        name = str(ev.get("tool") or ev.get("name") or "")
        if not name:
            continue
        fpath = _extract_file_path(ev)
        entry = f"{name} → {fpath}" if fpath else name

        if name in _READ_TOOLS and fpath:
            read_counts[fpath] = read_counts.get(fpath, 0) + 1
            if read_counts[fpath] > 1:
                entry += "  [re-read]"
        elif name in _WRITE_TOOLS and fpath:
            write_counts[fpath] = write_counts.get(fpath, 0) + 1

        trajectory.append(entry)

    lines = [
        "Session process:",
        f"  Duration: {metrics.wall_seconds:.0f}s | "
        f"Tokens: {metrics.input_tokens:,} in / {metrics.output_tokens:,} out | "
        f"Tool calls: {metrics.tool_calls} | Turns: {metrics.assistant_turns}",
        "",
    ]

    if trajectory:
        lines.append("  Tool trajectory:")
        if len(trajectory) <= MAX_TRAJECTORY:
            for i, t in enumerate(trajectory, 1):
                lines.append(f"  {i}. {t}")
        else:
            half = MAX_TRAJECTORY // 2
            for i, t in enumerate(trajectory[:half], 1):
                lines.append(f"  {i}. {t}")
            lines.append(f"  [...{len(trajectory) - MAX_TRAJECTORY} omitted...]")
            for i, t in enumerate(trajectory[-half:], len(trajectory) - half + 1):
                lines.append(f"  {i}. {t}")
        lines.append("")

    total_reads = sum(read_counts.values())
    re_reads = total_reads - len(read_counts)
    lines.append(
        f"  Files read: {len(read_counts)} unique"
        f" ({total_reads} total reads, {re_reads} re-reads)"
    )
    lines.append(f"  Files written/edited: {len(write_counts)} unique")
    return "\n".join(lines)
