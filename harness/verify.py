#!/usr/bin/env python3
"""Execution-based ground-truth scoring for one experiment cell.

Runs AFTER the session (so the agent never sees these checks). For code tasks it
applies hidden vitest tests, typechecks, runs the suite, and runs static checks;
for the Q&A task it scores answer-key coverage of the agent's final message.
Produces a deterministic `task_score` in [0,1] -> the headline metric. Never
raises; a missing toolchain is recorded, not fatal.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

HIDDEN_SUBDIR = ("__tests__", "__verify__")  # gitignored in the workspace
TOOL_TIMEOUT = 300


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                          timeout=TOOL_TIMEOUT)


def _apply_hidden_tests(task_dir: Path, workdir: Path) -> int:
    """Copy tasks/<id>/verify/*.test.ts* into the workspace's gitignored hidden
    dir. Returns how many files were applied."""
    verify_dir = task_dir / "verify"
    if not verify_dir.is_dir():
        return 0
    dst = workdir.joinpath(*HIDDEN_SUBDIR)
    dst.mkdir(parents=True, exist_ok=True)
    n = 0
    for f in sorted(verify_dir.glob("*.test.ts*")):
        shutil.copy(f, dst / f.name)
        n += 1
    return n


def _parse_vitest(report: Path) -> dict:
    """Vitest JSON (Jest-compatible) -> hidden vs full pass counts."""
    out = {"hidden_passed": 0, "hidden_total": 0, "full_passed": 0, "full_total": 0}
    if not report.exists():
        return out
    try:
        data = json.loads(report.read_text())
    except Exception:
        return out
    out["full_passed"] = int(data.get("numPassedTests", 0))
    out["full_total"] = int(data.get("numTotalTests", 0))
    for tr in data.get("testResults", []):
        if "__verify__" not in str(tr.get("name", "")):
            continue
        for a in tr.get("assertionResults", []):
            out["hidden_total"] += 1
            out["hidden_passed"] += 1 if a.get("status") == "passed" else 0
    return out


def _run_static_check(workdir: Path, check: dict) -> bool:
    """check = {pattern, mode: must_exist|must_not_exist, glob}."""
    pattern = re.compile(check["pattern"])
    found = False
    for f in workdir.glob(check.get("glob", "**/*")):
        if not f.is_file() or "node_modules" in f.parts or ".git" in f.parts:
            continue
        try:
            if pattern.search(f.read_text(errors="ignore")):
                found = True
                break
        except Exception:
            continue
    return found if check["mode"] == "must_exist" else not found


def verify_task(task: dict, workdir: Path, final_message: str = "") -> dict:
    """Score one cell. Writes nothing itself; caller persists the returned dict."""
    result: dict[str, Any] = {
        "task": task["id"], "task_score": None, "kind": None,
        "typecheck": None, "hidden": None, "fullsuite": None,
        "checks": [], "answer_key": None, "skipped": None,
    }

    # --- Q&A: no diff, score answer-key coverage of the final message ---
    answer_key = task.get("answer_key")
    if answer_key:
        result["kind"] = "qa"
        msg = (final_message or "").lower()
        matched = [k for k in answer_key if k.lower() in msg]
        cov = len(matched) / len(answer_key) if answer_key else 0.0
        result["answer_key"] = {"matched": matched, "total": len(answer_key),
                                "coverage": round(cov, 3)}
        result["task_score"] = round(cov, 3)
        return result

    # --- Code tasks: need the JS toolchain (node_modules symlinked in) ---
    result["kind"] = "code"
    if not (workdir / "node_modules").exists():
        result["skipped"] = "no node_modules (symlink missing) — run `npm install` in the fixture"
        return result

    applied = _apply_hidden_tests(task["dir"], workdir)

    tc = _run(["npx", "tsc", "--noEmit"], workdir)
    result["typecheck"] = {"passed": tc.returncode == 0, "rc": tc.returncode,
                           "errors": (tc.stdout + tc.stderr).count("error TS")}

    report = workdir / ".verify" / "vitest.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    _run(["npx", "vitest", "run", "--reporter=json", "--outputFile", ".verify/vitest.json"],
         workdir)
    vit = _parse_vitest(report)
    result["hidden"] = {"passed": vit["hidden_passed"], "total": vit["hidden_total"],
                        "applied_files": applied}
    result["fullsuite"] = {"passed": vit["full_passed"], "total": vit["full_total"]}

    for c in task.get("checks", []):
        ok = _run_static_check(workdir, c)
        result["checks"].append({**c, "passed": ok})

    result["task_score"] = _score(result)
    return result


def _score(r: dict) -> float:
    """typecheck is a hard gate; otherwise the mean of (hidden-test pass fraction)
    and (static-check pass fraction), whichever are present."""
    if r["typecheck"] and not r["typecheck"]["passed"]:
        return 0.0
    components: list[float] = []
    h = r["hidden"]
    if h and h["total"]:
        components.append(h["passed"] / h["total"])
    if r["checks"]:
        components.append(sum(1 for c in r["checks"] if c["passed"]) / len(r["checks"]))
    if not components:  # code task with neither hidden tests nor checks
        components.append(1.0 if (r["typecheck"] and r["typecheck"]["passed"]) else 0.0)
    return round(sum(components) / len(components), 3)


def summarize_for_judge(verify: dict) -> str:
    """One-line ground-truth summary injected into the judge prompt."""
    if not verify or verify.get("skipped"):
        return "Automated checks: not run."
    if verify["kind"] == "qa":
        ak = verify["answer_key"]
        return f"Automated check: answer-key coverage {ak['matched'].__len__()}/{ak['total']}."
    tc = "PASS" if verify["typecheck"] and verify["typecheck"]["passed"] else "FAIL"
    h = verify["hidden"] or {}
    chk = verify.get("checks") or []
    chk_s = f", static checks {sum(c['passed'] for c in chk)}/{len(chk)}" if chk else ""
    return (f"Automated checks: typecheck {tc}, hidden tests "
            f"{h.get('passed', 0)}/{h.get('total', 0)}{chk_s} "
            f"(deterministic task_score={verify['task_score']}).")


if __name__ == "__main__":  # manual: python verify.py <task_dir> <workdir>
    import sys
    td = Path(sys.argv[1])
    meta = json.loads((td / "task.json").read_text())
    meta["id"] = td.name
    meta["dir"] = td
    print(json.dumps(verify_task(meta, Path(sys.argv[2])), indent=2))
