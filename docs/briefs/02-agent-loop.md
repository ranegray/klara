# Build lane 2: episode loop, rungs 1–3

**Goal:** implement `klara_agent.loop.run_episode()` for rungs 1–3 plus one
concrete `VLMClient`, fully testable against `ScriptedRobot` (no Isaac, no
robot).

## Scope

- **Rung 1 (SINGLE_TURN):** prompt → one code generation → execute against
  `RobotAPI` → one EpisodeRecord. The generated program calls only the five
  primitives; execution is a restricted namespace (`{"robot": robot, "Pose":
  Pose}` — no imports, no filesystem).
- **Rung 2 (+ multi-turn feedback):** on failure, feed structured execution
  feedback (which call failed, ReasonCode, message) back as the next turn's
  context, up to `max_turns`.
- **Rung 3 (+ VDM-equivalent):** before/after `perceive()` snapshots diffed
  into structured text ("cube_1 moved 4.2cm; expected at target ± tol").
  Text-only VDM from ground-truth poses is the pilot version — image-based
  VDM is post-defense.
- One `VLMClient` implementation (Anthropic API), returning real `Usage`
  numbers. Model name from config, never hardcoded.
- Token accounting: every model call lands in a `TurnRecord`; the episode
  totals must equal the sum of turns. Property-test this.
- Tests: drive all three rungs against `ScriptedRobot` failure scripts
  (grasp fails once then succeeds; object never visible; etc.) with a stub
  VLM returning canned programs. Assert recovery behavior differs by rung —
  that differential is the whole experiment.

## Design authority — surface, don't decide

The turn boundary, what counts in token totals (system prompt? retries?),
feedback verbosity, and retry-vs-replan routing belong to
`docs/protocols/compute-ladder.md` (Rane's). Implement mechanics behind
small functions with the open questions listed in the PR description. Do
not silently pick answers that shape the science.

## Hard constraints

Pure Python; no `omni`, no `rclpy`, no provider SDK outside the client
module. Rung numbers are frozen (`ladder.py`). One episode = exactly one
EpisodeRecord, appended, never rewritten.

## Done when

`uv run pytest` exercises rungs 1–3 end-to-end on ScriptedRobot; a real-API
smoke run (rung 1, one episode) produces a valid EpisodeRecord with nonzero
token counts.
