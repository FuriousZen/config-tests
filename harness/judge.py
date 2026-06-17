#!/usr/bin/env python3
"""Blind LLM-judge scoring for one experiment cell.

Runs a fixed neutral judge model (NOT one of the models under test) via a
headless `opencode run --pure` session in a throwaway dir. The judge sees only
the task spec + the produced diff + the agent's final message — never which
model or MCP config produced them — and returns a strict-JSON rubric score.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

import lib

RUBRIC = """You are a strict, impartial code-review judge. You are given a coding TASK,
the RESULT a coding agent produced (a unified diff, plus the agent's final
message), and a SESSION PROCESS log showing every tool call the agent made.
Score the RESULT on each axis from 1 (poor) to 5 (excellent):

- correctness:  Does the change actually do what the task asked, without bugs?
- completeness: Are all parts of the task addressed (edge cases, tests if asked)?
- efficiency:   Is the solution focused and clean (no needless churn or detours)?
- process_efficiency: Did the agent navigate the codebase efficiently? Penalize
  excessive file reads, re-reading the same files, reading irrelevant files,
  hallucinating file paths, high token burn relative to task complexity, and
  unfocused exploration. Reward targeted reads, minimal backtracking, and
  efficient context use.

Then give an overall score 1-5 and a one-sentence rationale.

Respond with ONLY a single JSON object, no prose before or after:
{"correctness": <1-5>, "completeness": <1-5>, "efficiency": <1-5>, "process_efficiency": <1-5>, "overall": <1-5>, "rationale": "<one sentence>"}
"""

MAX_DIFF_CHARS = 24000


def final_agent_message(export_path: Path | None) -> str:
    """Best-effort pull of the agent's last assistant text from export.json."""
    if not export_path or not export_path.exists():
        return ""
    try:
        data = json.loads(export_path.read_text())
    except Exception:
        return ""
    texts: list[str] = []

    def walk(o):
        if isinstance(o, dict):
            if o.get("type") == "text" and isinstance(o.get("text"), str):
                texts.append(o["text"])
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(data)
    return texts[-1][:4000] if texts else ""


def _extract_json(text: str) -> dict:
    """Extract the last valid JSON object containing 'overall' from text.

    Uses brace-depth counting so nested objects like
    {"a": {"b": 1}, "overall": 5} are matched correctly.
    """
    candidates: list[str] = []
    i = 0
    while i < len(text):
        if text[i] == "{":
            depth = 0
            in_string = False
            escape_next = False
            for j in range(i, len(text)):
                c = text[j]
                if escape_next:
                    escape_next = False
                    continue
                if c == "\\" and in_string:
                    escape_next = True
                    continue
                if c == '"' and not escape_next:
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        candidates.append(text[i : j + 1])
                        i = j
                        break
        i += 1
    for blob in reversed(candidates):
        try:
            d = json.loads(blob)
            if isinstance(d, dict) and "overall" in d:
                return d
        except json.JSONDecodeError:
            continue
    return {}


def judge_run(task: dict, diff_text: str, export_path: Path | None,
              judge_model: str, out_path: Path, verify_summary: str = "",
              process_summary: str = "") -> dict:
    diff = diff_text if len(diff_text) <= MAX_DIFF_CHARS else diff_text[:MAX_DIFF_CHARS] + "\n…[diff truncated]…"
    final_msg = final_agent_message(export_path)
    rubric_extra = task.get("rubric", "")

    # Ground the judge in deterministic results so it can't praise broken code.
    ground = (f"==== GROUND TRUTH (trust this over your own reading) ====\n{verify_summary}\n\n"
              if verify_summary else "")
    process = (f"==== SESSION PROCESS ====\n{process_summary}\n\n"
               if process_summary else "")
    message = (
        f"{RUBRIC}\n"
        f"{('Extra rubric guidance for this task: ' + rubric_extra) if rubric_extra else ''}\n\n"
        f"==== TASK ====\n{task['title']}\n\n{task['prompt']}\n\n"
        f"{ground}"
        f"{process}"
        f"==== RESULT: AGENT FINAL MESSAGE ====\n{final_msg or '(none)'}\n\n"
        f"==== RESULT: DIFF ====\n{diff or '(no changes were made)'}\n"
    )

    with tempfile.TemporaryDirectory() as td:
        try:
            judge_env = lib.build_judge_env(td)
            res = subprocess.run(
                ["opencode", "run", message, "-m", judge_model,
                 "--pure", "--dangerously-skip-permissions", "--dir", td],
                capture_output=True, text=True, timeout=300, env=judge_env,
            )
            verdict = _extract_json(res.stdout)
        except Exception as e:
            verdict = {"error": str(e)}

    if not verdict or "overall" not in verdict:
        verdict = {**verdict, "overall": None, "parse_failed": True}
    out_path.write_text(json.dumps(verdict, indent=2))
    return verdict


if __name__ == "__main__":  # manual: python judge.py <cell_dir> <judge_model>
    import sys
    cell = Path(sys.argv[1])
    meta = json.loads((cell / "metrics.json").read_text())
    task = {"id": meta["task"], "title": meta["task"], "prompt": "(see task spec)", "rubric": ""}
    print(judge_run(task, (cell / "diff.patch").read_text(),
                     cell / "export.json", sys.argv[2], cell / "judge.json"))
