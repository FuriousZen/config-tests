#!/usr/bin/env python3
"""Orchestrate the OpenCode MCP-config experiment matrix.

For every (model x config x task x rep) cell:
  1. copy the task's fixture into a fresh isolated workdir
  2. write a workdir-local opencode.json enabling exactly the chosen MCP
  3. (memory configs) pre-index the repo so query tools have data
  4. run `opencode run --pure --format json` (timed, headless)
  5. `opencode export` the session + capture the git diff
  6. compute metrics.json, then run the blind LLM judge -> judge.json

Artifacts land in results/<timestamp>/<model>__<config>__<task>__repN/.

Usage:
  python harness/run_experiment.py                  # full matrix
  python harness/run_experiment.py --dry-run-one    # 1 cell, smoke test
  python harness/run_experiment.py --models mistral-small-4-119b --configs control codebase-memory
  python harness/run_experiment.py --reps 1 --no-judge
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import lib
import verify
from judge import judge_run, final_agent_message

# ---------------------------------------------------------------------------
# Exact MCP tool names (from upstream docs) for accurate detection.
# ---------------------------------------------------------------------------
MCP_TOOL_NAMES: dict[str, list[str]] = {
    "codebase-memory": [
        "index_repository", "search_graph", "query_graph", "trace_path",
        "trace_call_path", "search_code", "get_code_snippet", "get_architecture",
        "get_graph_schema", "index_status", "list_projects", "detect_changes",
        "manage_adr", "ingest_traces",
    ],
    "codegraphcontext": [
        "add_code_to_graph", "check_job_status", "list_jobs", "find_code",
        "analyze_code_relationships", "watch_directory", "execute_cypher_query",
        "add_package_to_graph", "find_dead_code", "calculate_cyclomatic_complexity",
        "find_most_complex_functions", "list_indexed_repositories", "delete_repository",
        "visualize_graph_query", "list_watched_paths", "unwatch_directory",
        "load_bundle", "search_registry_bundles", "get_repository_stats",
        "discover_codegraph_contexts", "switch_context", "generate_report",
        "find_java_spring_endpoints", "find_java_spring_beans", "find_datasource_nodes",
    ],
}
ALL_MCP_TOOL_NAMES: list[str] = [n for names in MCP_TOOL_NAMES.values() for n in names]


def load_tasks() -> list[dict]:
    tasks = []
    for d in sorted(lib.TASKS_DIR.iterdir()):
        if not d.is_dir():
            continue
        meta_path = d / "task.json"
        prompt_path = d / "prompt.md"
        if not (meta_path.exists() and prompt_path.exists()):
            continue
        meta = json.loads(meta_path.read_text())
        meta["id"] = d.name
        meta["prompt"] = prompt_path.read_text().strip()
        meta["dir"] = d
        tasks.append(meta)
    return tasks


def pre_index(config_name: str, workdir: Path, mcp_runtime: dict) -> str:
    """Best-effort: populate the memory/graph for a memory config before the
    timed run, using each server's documented CLI. Returns a short status string;
    never fatal. State is isolated per-run via the same env the MCP server gets.

    - codebase-memory: `<bin> cli index_repository '{"repo_path":"<ABS>"}'`
      (repo_path must be absolute), state under CBM_CACHE_DIR.
    - codegraphcontext: `<bin> index .` run with cwd=workdir (docs index the
      current dir), state isolated by overriding HOME (no documented data-dir var).
    """
    rt = mcp_runtime.get(config_name)
    if not rt:
        return "skipped (mcp not installed)"
    bin0 = rt["command"][0]
    if config_name == "codebase-memory":
        env = {"CBM_CACHE_DIR": str(workdir / ".cbm-cache")}
        args = json.dumps({"repo_path": str(workdir)})
        return _try([bin0, "cli", "index_repository", args], env=env)
    if config_name == "codegraphcontext":
        env = {"HOME": str(workdir / ".cgc-home")}
        (workdir / ".cgc-home").mkdir(parents=True, exist_ok=True)
        return _try([bin0, "index", "."], env=env, cwd=workdir)
    return "n/a"


def _try(cmd: list[str], env: dict | None = None, cwd: Path | None = None) -> str:
    try:
        run_env = {**os.environ, **(env or {})}
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=600,
                           env=run_env, cwd=str(cwd) if cwd else None)
        return "ok" if r.returncode == 0 else f"index-cli-unavailable (rc={r.returncode}); agent indexes in-session"
    except Exception as e:
        return f"index error: {e}"


def run_cell(model: dict, config_name: str, task: dict, rep: int,
             run_root: Path, mcp_runtime: dict, exp: dict, do_judge: bool) -> dict:
    cell_id = f"{model['slug']}__{config_name}__{task['id']}__rep{rep}"
    cell_dir = run_root / cell_id
    cell_dir.mkdir(parents=True, exist_ok=True)
    workdir = cell_dir / "workspace"

    fixture = lib.FIXTURES_DIR / task.get("fixture", "react-app")
    lib.make_clean_workdir(fixture, workdir)
    lib.write_workdir_config(workdir, config_name, mcp_runtime)

    index_status = "n/a"
    if exp.get("pre_index") and config_name in ("codebase-memory", "codegraphcontext"):
        index_status = pre_index(config_name, workdir, mcp_runtime)

    print(f"  -> {cell_id}  (pre-index: {index_status})", flush=True)
    session_env = lib.build_session_env(cell_dir)
    run = lib.run_opencode_session(
        message=task["prompt"],
        model=model["id"],
        workdir=workdir,
        out_events=cell_dir / "events.json",
        timeout_seconds=exp.get("timeout_seconds", 900),
        session_env=session_env,
    )

    export_path = cell_dir / "export.json"
    if run.session_id:
        lib.export_session(run.session_id, export_path)

    (cell_dir / "diff.patch").write_text(lib.git_diff(workdir))

    metrics = lib.extract_metrics(run, export_path, ALL_MCP_TOOL_NAMES)
    metrics_d = metrics.asdict()
    metrics_d.update(model=model["slug"], model_id=model["id"], config=config_name,
                     task=task["id"], rep=rep, session_id=run.session_id,
                     pre_index=index_status)

    # Post-session isolation check
    iso_warn = None
    if not metrics.errored:
        if config_name in ("codebase-memory", "codegraphcontext") and metrics.mcp_tool_calls == 0:
            iso_warn = f"MCP config '{config_name}' produced 0 MCP tool calls — server may not have loaded"
        elif config_name == "control" and metrics.mcp_tool_calls > 0:
            iso_warn = f"control produced {metrics.mcp_tool_calls} MCP tool calls — isolation may be broken"
    if iso_warn:
        print(f"     ⚠ ISOLATION: {iso_warn}", flush=True)
        metrics_d["isolation_warning"] = iso_warn

    # --- execution-based ground truth (headline score) ---
    # Runs after the diff is captured; hidden tests land in a gitignored dir.
    final_msg = final_agent_message(export_path)
    verify_d = {}
    if exp.get("run_verify", True) and not metrics.errored:
        verify_d = verify.verify_task(task, workdir, final_msg)
        (cell_dir / "verify.json").write_text(json.dumps(verify_d, indent=2))
        metrics_d["task_score"] = verify_d.get("task_score")
        metrics_d["verify"] = {k: verify_d.get(k) for k in
                               ("kind", "typecheck", "hidden", "fullsuite", "checks",
                                "answer_key", "skipped")}
    (cell_dir / "metrics.json").write_text(json.dumps(metrics_d, indent=2))

    judge_d = {}
    if do_judge and not metrics.errored:
        judge_d = judge_run(
            task=task,
            diff_text=(cell_dir / "diff.patch").read_text(),
            export_path=export_path,
            judge_model=exp["judge_model"],
            out_path=cell_dir / "judge.json",
            verify_summary=verify.summarize_for_judge(verify_d),
        )
    elif metrics.errored:
        (cell_dir / "judge.json").write_text(json.dumps(
            {"skipped": True, "reason": "session errored", "error": metrics.error_message}, indent=2))

    status = "ERR" if metrics.errored else ("TIMEOUT" if metrics.timed_out else "ok")
    print(f"     {status}  {metrics.wall_seconds}s  task_score={metrics_d.get('task_score', '-')} "
          f"in={metrics.input_tokens} out={metrics.output_tokens} cost=${metrics.cost_usd:.4f} "
          f"tools={metrics.tool_calls} mcp={metrics.mcp_tool_calls} judge={judge_d.get('overall', '-')}",
          flush=True)

    row = {**metrics_d, **{f"judge_{k}": v for k, v in judge_d.items()}}
    row.pop("verify", None)  # keep the flat row clean; full detail lives in verify.json
    if verify_d:
        row["task_score"] = verify_d.get("task_score")
        row["verify_typecheck"] = bool((verify_d.get("typecheck") or {}).get("passed"))
    return row


def main() -> int:
    exp = lib.load_experiment()
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="*", help="model slugs to include")
    ap.add_argument("--configs", nargs="*", help="configs to include")
    ap.add_argument("--tasks", nargs="*", help="task ids to include")
    ap.add_argument("--reps", type=int, default=exp["reps"])
    ap.add_argument("--dry-run-one", action="store_true", help="run a single cell and stop")
    ap.add_argument("--no-judge", action="store_true")
    ap.add_argument("--parallel", type=int, default=1, help="max concurrent cells")
    args = ap.parse_args()

    try:
        mcp_runtime = lib.load_mcp_runtime()
    except FileNotFoundError as e:
        print(e); return 2

    models = [m for m in exp["models"] if not args.models or m["slug"] in args.models]
    configs = [c for c in exp["configs"] if not args.configs or c in args.configs]
    tasks = [t for t in load_tasks() if not args.tasks or t["id"] in args.tasks]
    reps = list(range(1, args.reps + 1))

    if not tasks:
        print("No tasks found in harness/tasks/ — add at least one task dir."); return 2

    run_root = lib.RESULTS_DIR / datetime.now().strftime("%Y%m%d-%H%M%S")
    run_root.mkdir(parents=True, exist_ok=True)

    cells = [(m, c, t, r) for m in models for c in configs for t in tasks for r in reps]
    if args.dry_run_one:
        cells = cells[:1]
    print(f"Matrix: {len(models)} models x {len(configs)} configs x {len(tasks)} tasks x "
          f"{len(reps)} reps = {len(cells)} sessions -> {run_root}")

    rows: list[dict] = []
    if args.parallel > 1:
        rows_lock = threading.Lock()
        counter = [0]

        def _run_one(m, c, t, r):
            with rows_lock:
                counter[0] += 1
                n = counter[0]
            print(f"[{n}/{len(cells)}]", flush=True)
            return run_cell(m, c, t, r, run_root, mcp_runtime, exp, do_judge=not args.no_judge)

        with ThreadPoolExecutor(max_workers=args.parallel) as pool:
            futures = {pool.submit(_run_one, m, c, t, r): i
                       for i, (m, c, t, r) in enumerate(cells)}
            for fut in as_completed(futures):
                row = fut.result()
                with rows_lock:
                    rows.append(row)
                    (run_root / "index.json").write_text(json.dumps(rows, indent=2))
    else:
        for i, (m, c, t, r) in enumerate(cells, 1):
            print(f"[{i}/{len(cells)}]", flush=True)
            rows.append(run_cell(m, c, t, r, run_root, mcp_runtime, exp, do_judge=not args.no_judge))
            (run_root / "index.json").write_text(json.dumps(rows, indent=2))

    print(f"\nDone. {len(rows)} cells. Aggregate with:\n  python harness/aggregate.py {run_root}")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
