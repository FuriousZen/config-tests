# OpenCode MCP-config experiment harness

Evaluates how two codebase-aware MCP servers affect OpenCode session performance,
across three NVIDIA NIM models. Fully automated: one command runs the matrix,
captures objective metrics + a blind LLM-judge score per session, and emits a
scorecard.

## Matrix

3 models × 3 configs × N tasks × 3 reps.

- **Models** (`experiment.json`): `nvidia/google/gemma-4-31b-it`,
  `nvidia/openai/gpt-oss-120b`, `nvidia/nvidia/nemotron-3-ultra-550b-a55b`.
- **Configs**: `control` (no experiment MCP), `codebase-memory`
  (DeusData/codebase-memory-mcp), `codegraphcontext` (PyPI).
- **Tasks** (`tasks/`): bugfix, feature, cross-file refactor, navigation Q&A —
  the last two are designed to expose MCP differences. All run against the
  `fixtures/react-app` workspace (a layered React+TS Task Board with `app/` and a
  mirroring `__tests__/`).
- Every session runs `opencode run --pure` (no plugins → no interactive
  brainstorm skill → no hangs) with `--dangerously-skip-permissions`.

## Prerequisites

1. **Nvidia auth must work.** Verify with:
   ```
   opencode run "say pong" -m nvidia/google/gemma-4-31b-it --pure --dangerously-skip-permissions
   ```
   If this 401s, re-auth: `opencode auth login` → Nvidia → paste a valid key.
2. **Install the MCP servers** (idempotent):
   ```
   python3 harness/setup_mcps.py
   ```
   Writes `harness/mcp_runtime.json`. Needs network; codegraphcontext installs
   into `harness/.venv-cgc`, codebase-memory via its one-line installer.

## Run

```
python3 harness/run_experiment.py --dry-run-one          # 1-cell smoke test
python3 harness/run_experiment.py --configs control codebase-memory codegraphcontext \
        --models gemma-4-31b --tasks task-01-bugfix --reps 1   # small matrix
python3 harness/run_experiment.py                        # full matrix
python3 harness/aggregate.py results/<timestamp>         # summary.csv + summary.md
```

Useful flags: `--models`, `--configs`, `--tasks`, `--reps`, `--no-judge`.

## Outputs

`results/<timestamp>/<model>__<config>__<task>__repN/`:
`events.json` (JSONL stream) · `export.json` (authoritative session) ·
`diff.patch` · `metrics.json` · `judge.json`. Plus `index.json` (all rows),
`summary.csv`, and `summary.md` (3×3 per-metric tables with MCP lift vs control).

## Tuning

Everything lives in `experiment.json`: models, configs, `reps`, `judge_model`
(kept off the models-under-test to avoid self-eval bias), `timeout_seconds`,
`pre_index`. Add a task by dropping a `tasks/<id>/` dir with `prompt.md` +
`task.json` (`title`, `fixture`, optional `rubric`).

## Notes / known caveats

- **Pre-indexing**: for the memory configs the harness tries a CLI index before
  the timed run; if a server has no index CLI, the agent indexes in-session
  (status recorded per cell). Verify `mcp_tool_calls > 0` for MCP configs in the
  first real runs to confirm the servers are actually being used.
- **Metric parser** (`lib.extract_metrics`) reads tokens/cost from `export.json`
  by walking for `tokens`/`cost` keys; confirm the numbers look right on the
  first real session and adjust the key names if OpenCode's schema differs.
- The fixture (`fixtures/react-app`) is a committed git repo; each session gets
  a pristine copy and a `.gitignore` that keeps harness artifacts out of the diff.
