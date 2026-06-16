#!/usr/bin/env python3
"""Roll a run's per-cell results into summary.csv + summary.md.

summary.csv : one row per session (all metrics + judge scores).
summary.md  : per-metric 3x3 tables (model x config), mean +/- stdev across the
              reps x tasks in each cell, plus each MCP config's lift vs control.

Usage: python harness/aggregate.py results/<timestamp>
"""
from __future__ import annotations

import csv
import json
import statistics
import sys
from pathlib import Path

import lib

# (column in index.json, pretty label, higher_is_better)
METRICS = [
    ("judge_overall", "Judge overall (1-5)", True),
    ("judge_correctness", "Judge correctness", True),
    ("wall_seconds", "Wall seconds", False),
    ("total_tokens", "Total tokens", False),
    ("cost_usd", "Cost USD", False),
    ("tool_calls", "Tool calls", False),
    ("mcp_tool_calls", "MCP tool calls", True),
]


def load_rows(run_root: Path) -> list[dict]:
    idx = run_root / "index.json"
    if idx.exists():
        rows = json.loads(idx.read_text())
    else:  # fall back to scanning cell dirs
        rows = []
        for cell in sorted(run_root.glob("*__*__*__rep*")):
            m = json.loads((cell / "metrics.json").read_text())
            j = {}
            jp = cell / "judge.json"
            if jp.exists():
                j = {f"judge_{k}": v for k, v in json.loads(jp.read_text()).items()}
            rows.append({**m, **j})
    for r in rows:
        r["total_tokens"] = (r.get("input_tokens", 0) or 0) + (r.get("output_tokens", 0) or 0)
    return rows


def write_csv(rows: list[dict], out: Path) -> None:
    cols: list[str] = []
    for r in rows:
        for k in r:
            if k not in cols:
                cols.append(k)
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def _nums(rows, key):
    return [float(r[key]) for r in rows if isinstance(r.get(key), (int, float))]


def _cell_stat(rows, model, config, key):
    vals = _nums([r for r in rows if r.get("model") == model and r.get("config") == config], key)
    if not vals:
        return None, None
    return statistics.mean(vals), (statistics.stdev(vals) if len(vals) > 1 else 0.0)


def write_md(rows: list[dict], out: Path, exp: dict) -> None:
    models = [m["slug"] for m in exp["models"]]
    configs = exp["configs"]
    control = "control" if "control" in configs else configs[0]
    lines = ["# Experiment summary", ""]

    n_err = sum(1 for r in rows if r.get("errored"))
    lines += [f"- Sessions: **{len(rows)}**  (errored: {n_err})",
              f"- Models: {', '.join(models)}",
              f"- Configs: {', '.join(configs)}",
              f"- Judge: `{exp['judge_model']}`", ""]

    for key, label, hib in METRICS:
        lines += [f"## {label}", "",
                  "| model \\ config | " + " | ".join(configs) + " | best |",
                  "|" + "---|" * (len(configs) + 2)]
        for model in models:
            cells, best_cfg, best_val = [], None, None
            for cfg in configs:
                mean, std = _cell_stat(rows, model, cfg, key)
                if mean is None:
                    cells.append("–")
                    continue
                lift = ""
                if cfg != control:
                    cmean, _ = _cell_stat(rows, model, control, key)
                    if cmean not in (None, 0):
                        pct = (mean - cmean) / abs(cmean) * 100
                        good = (pct >= 0) == hib
                        lift = f" ({'+' if pct >= 0 else ''}{pct:.0f}%{' ✓' if good and abs(pct) > 1 else ''})"
                cells.append(f"{mean:.2f} ± {std:.2f}{lift}")
                if best_val is None or (mean > best_val) == hib:
                    best_val, best_cfg = mean, cfg
            lines.append(f"| {model} | " + " | ".join(cells) + f" | {best_cfg or '–'} |")
        lines.append("")

    lines += ["---", "_Lift % is each MCP config vs. its own `control` row; ✓ marks a",
              "meaningful improvement in the right direction (>1%)._"]
    out.write_text("\n".join(lines))


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python harness/aggregate.py results/<timestamp>"); return 2
    run_root = Path(sys.argv[1])
    exp = lib.load_experiment()
    rows = load_rows(run_root)
    if not rows:
        print("no rows found"); return 1
    write_csv(rows, run_root / "summary.csv")
    write_md(rows, run_root / "summary.md", exp)
    print(f"wrote {run_root/'summary.csv'} and {run_root/'summary.md'}")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
