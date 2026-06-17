# OpenCode MCP-config experiment harness

Evaluates how two codebase-aware MCP servers affect OpenCode session performance,
across three NVIDIA NIM models. Fully automated: one command runs the matrix,
captures objective metrics + a blind LLM-judge score per session, and emits a
scorecard.

## Matrix

3 models × 3 configs × N tasks × 3 reps.

- **Models** (`experiment.json`): `nvidia/mistralai/mistral-small-4-119b-2603`,
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
   opencode run "say pong" -m nvidia/mistralai/mistral-small-4-119b-2603 --pure --dangerously-skip-permissions
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
        --models mistral-small-4-119b --tasks task-01-bugfix --reps 1   # small matrix
python3 harness/run_experiment.py                        # full matrix
python3 harness/aggregate.py results/<timestamp>         # summary.csv + summary.md
```

Useful flags: `--models`, `--configs`, `--tasks`, `--reps`, `--no-judge`.

## Outputs

`results/<timestamp>/<model>__<config>__<task>__repN/`:
`events.json` (JSONL stream) · `export.json` (authoritative session) ·
`diff.patch` · `metrics.json` · `verify.json` · `judge.json`. Plus `index.json`
(all rows), `summary.csv`, and `summary.md` (3×3 per-metric tables with MCP lift
vs control).

## Scoring (two layers)

1. **Execution-based ground truth (headline `task_score`, 0–1)** — `verify.py`
   runs *after* the session, so the agent never sees it:
   - copies hidden vitest tests from `tasks/<id>/verify/` into the workspace's
     gitignored `__tests__/__verify__/`,
   - runs `tsc --noEmit` (hard gate) + `vitest` (scores **hidden** tests only, so
     trivial agent-written tests can't inflate it) + static `checks` from
     `task.json` (e.g. the refactor's "old name gone, new name present"),
   - the Q&A task (no diff) scores answer-key coverage of the final message.
   `task_score = 0` if typecheck fails, else mean of hidden-test and static-check
   pass-fractions. Toggle with `run_verify` in `experiment.json`.
2. **LLM judge (secondary, grounded)** — the judge is shown the verify summary
   ("typecheck PASS, hidden tests 7/8…") so it can't praise broken code; it rates
   qualitative axes and stays primary only for the Q&A task.

Requires Node + the fixture's `node_modules` (the devcontainer installs it; each
workspace **symlinks** it rather than copying 108×).

## Adding a task with execution checks

Drop `tasks/<id>/verify/*.test.ts` (hidden tests) and/or add to `task.json`:
`checks` (`[{pattern, mode: must_exist|must_not_exist, glob}]`) for static
assertions, or `answer_key` (`[string,…]`) for a no-diff Q&A task.

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
