# KLARA

Kinematic Limits, Agentic Recovery Architecture. Senior thesis (Rane Gray, CU
Boulder, 2026-27) asking: does agentic test-time compute compensate for
unreliable hardware, and at what token cost? A CaP-style coding agent runs
against cheap STS3215 servos (real or injected); we measure the
reliability-per-token frontier across a ladder of test-time compute.

The research direction lives in the Obsidian vault at `~/notes/thesis/`
(authoritative; check `handoff.md` and `october defense plan.md` for current
state). This repo is the instrument, not the science.

## Hard rules

- **Import boundaries:** `klara-core` and `klara-agent` are pure Python — they
  never import sim, ROS, or provider SDKs. Only `klara-sim-isaac` imports
  `omni.*` (inside functions, so CI can import the package). Only `ros2_ws`
  imports `rclpy`.
- **The contract is frozen:** changes to `klara_core` `api.py` / `results.py` /
  `records.py` require a PR that updates every backend. Adding a ReasonCode is
  a contract change.
- **Never renumber ladder rungs** (`klara_agent/ladder.py`) — episode records
  cite them. Never rewrite existing EpisodeRecords; bump `SCHEMA_VERSION` and
  keep readers backward-compatible.
- **The stressor stays in the command path.** Unreliability injection
  (`klara_core/stressor.py`) applies to every commanded joint target in the
  backend, never as a post-hoc analysis adjustment. Parameters are versioned
  config with cited provenance (robo9 STS3215 or bench measurements).
- **Design decisions are Rane's; implementation is delegable.** The protocol
  notes in `docs/protocols/` (ladder accounting, reset contract, stressor
  provenance) are the design authority — implement against them; if a note
  doesn't cover a design question, surface it instead of deciding silently.
- **Never first-draft defense-facing prose** (proposal, lit review, slides,
  rehearsed answers). Agents critique those; Rane writes them. Adversarial
  reading is welcome and encouraged.
- **Never publish anything** (posts, releases). Draft via `/post-update`;
  Rane reviews and posts manually.

## Commands

```bash
uv sync --all-packages      # workspace setup
uv run pytest               # contract + agent tests (no Isaac/ROS needed)
uv run ruff check packages experiments
```

Isaac runs use Isaac Sim's bundled Python: `./python.sh -m pip install -e`
the three packages once, then run `experiments/run_sweep.py` with it
(docs/SETUP.md). ROS 2 Humble hardware track: `colcon build` in `ros2_ws/`.

## Layout

- `packages/klara-core` — the frozen contract + stressor + records (+ 
  `testing.ScriptedRobot`, the CI-safe RobotAPI double)
- `packages/klara-agent` — compute ladder, VLM client protocol, episode loop
- `packages/klara-sim-isaac` — Isaac Sim backend (pilot experiments)
- `ros2_ws/` — hardware track (Sep/Oct): klara_hardware, bringup,
  description (URDF source of truth), perception
- `experiments/` — sweep configs/runner/analysis; output JSONL in `data/`
  (gitignored, synced to shared storage — treat as thesis evidence)
- `dashboards/` — Foxglove layouts. `assets/usd/` — USD converted from URDF.
- `comms/` — public-update drafts (see `/post-update` skill)

## Cadence anchors

Proposal draft ~Aug 26 → proposal defense Oct 2026 → hardware campaign
Nov-Feb → final defense ~Apr 2027. Pre-defense priority: sim pilot (rungs
1-3) + the three protocol notes. Hardware work is off the critical path
until September.
