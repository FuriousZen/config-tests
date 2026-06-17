# config-tests — OpenCode MCP-config experiment harness

Measures how much two codebase-aware MCP servers help an [OpenCode](https://opencode.ai)
coding session, and whether that help depends on the model. It runs a **3×3
matrix** — three NVIDIA NIM models × three MCP configs — over a small task suite,
capturing objective metrics plus a blind LLM-judge score per session, and emits a
scorecard.

## The matrix

|                | control | codebase-memory | codegraphcontext |
|----------------|---------|-----------------|------------------|
| mistral-small-4-119b | …   | …               | …                |
| gpt-oss-120b   | …       | …               | …                |
| nemotron-3-ultra | …     | …               | …                |

- **Configs** toggle exactly one experiment MCP (or none for `control`); every
  session runs `opencode run --pure` so plugins can't confound or hang the run.
- **Tasks** (`harness/tasks/`) run against `fixtures/react-app`, a layered
  React + TypeScript app with `app/` and a mirroring `__tests__/`, built to give
  the MCPs real cross-file relationships to navigate.
- 3 reps × ~4 tasks × 9 cells ≈ **108 sessions** + 108 judge calls.

## Quickstart (devcontainer)

1. `cp .devcontainer/.env.example .devcontainer/.env` and paste a valid
   **NVIDIA NIM** key (`NVIDIA_API_KEY`). This file is gitignored — never commit it.
2. Reopen in the container. On build it installs opencode, connects NIM (no
   `/connect`), installs the fixture deps, and installs both MCP servers.
3. Run:
   ```bash
   python3 harness/run_experiment.py --dry-run-one     # smoke test one cell
   python3 harness/run_experiment.py                   # full matrix
   python3 harness/aggregate.py results/<timestamp>    # summary.csv + summary.md
   ```

NVIDIA NIM credentials are required to run anything, and are **never committed**.

## Layout

- `harness/` — orchestrator, judge, aggregator, MCP/auth setup. See
  [harness/README.md](harness/README.md) for full detail and flags.
- `fixtures/react-app/` — the workspace each session edits (pristine; copied + a
  fresh git baseline per run).
- `.devcontainer/` — Node 22 + Python 3.12 toolchain and build-time bootstrap.
- `results/` — timestamped run artifacts (gitignored).
