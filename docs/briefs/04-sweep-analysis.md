# Build lane 4: sweep runner + frontier analysis

**Goal:** `experiments/run_sweep.py` executes a pilot config end-to-end and
`experiments/analysis/` turns the resulting JSONL into the
reliability-per-token figures the proposal will print.

## Scope

- **Runner:** load `configs/pilot_cube.yaml` → for each rung × episode:
  `env.reset(seed)`, `run_episode(...)`, append the record. Requirements:
  - **Resumable:** on restart, skip (rung, seed) pairs already present in
    the output JSONL. Sweeps die mid-run; evidence must survive.
  - Backend selection by config string ("isaac" imports lazily so the
    runner itself works with ScriptedRobot in tests).
  - Per-episode progress line (rung, seed, success, tokens, wall-clock) and
    a run header logging git SHA, config hash, stressor params.
- **Analysis (`analysis/plot_frontier.py` + friends):** from a JSONL path
  produce:
  - success rate per rung with Wilson 95% CIs (n=20/rung is small — CIs are
    not optional),
  - the frontier plot: reliability vs. mean tokens-per-successful-episode
    per rung,
  - tokens-per-recovered-failure (marginal cost of turns after first
    detected failure — definition cited from `docs/protocols/compute-ladder.md`;
    if that note isn't written yet, implement behind a clearly-named
    function and flag it),
  - a per-rung summary table (success, turns, tokens, wall-clock, failure
    categories) as markdown — this pastes into the proposal.
- Tests: run the sweep runner against ScriptedRobot + stub VLM in CI;
  analysis functions tested on synthetic record fixtures with known answers
  (e.g. constructed data where rung 2 recovers exactly half of rung 1's
  failures).

## Out of scope

The loop internals (lane 2), Isaac (lane 1) — this lane must be fully
buildable against `ScriptedRobot` and synthetic records. Statistical tests
beyond CIs (post-defense).

## Hard constraints

Analysis reads records only through `klara_core.records` readers — no ad-hoc
JSON parsing that silently forks the schema. Never mutate or rewrite a run
file. Plots follow the repo's one style (matplotlib, no seaborn dep).

## Done when

`uv run pytest` runs a miniature sweep + analysis in CI; running the real
config against lane 1+2 outputs (once they land) produces the frontier
figure and summary table from a single command.
