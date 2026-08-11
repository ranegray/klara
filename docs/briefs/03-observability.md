# Build lane 3: episode traces + Foxglove

**Goal:** every episode can be replayed and inspected — an MCAP trace per
episode plus a committed Foxglove layout that makes failures legible.

## Scope

- `klara_core.tracing.TraceWriter`: wraps any `RobotAPI` (decorator pattern,
  same trick as `JointStressor`'s wrapper) and logs to MCAP: primitive call
  start/end with args + PrimitiveResult, turn boundaries, agent-generated
  code per turn, VDM text, stressor params. Use the `mcap` Python package
  with JSON-schema channels; keep it dependency-light and backend-agnostic.
- File convention: `data/runs/<run_id>/episodes/<episode_id>.mcap` next to
  the run's JSONL (records = the dataset, traces = the evidence behind it).
- `dashboards/episode-debug.json`: Foxglove layout — timeline of primitive
  calls, current turn's generated code (raw message panel), reason-code
  history, joint targets commanded-vs-perturbed plot. Verify it opens
  against a generated trace and commit a screenshot to the PR.
- A tiny fixture generator (`ScriptedRobot` + stub agent) so traces exist
  without Isaac, and a test that a written trace round-trips through the
  `mcap` reader.

## Why this lane matters

Failure attribution (`FailureCategory`) is a thesis result, and Rane
adjudicates it by *reading traces*. The layout is the instrument for that
judgment — optimize for "why did this episode fail" being answerable in
under a minute.

## Out of scope

Live streaming from Isaac (nice-to-have later via foxglove-websocket),
ROS/rosbag2 integration (hardware track picks this up — but don't preclude
it: stick to standard MCAP so both tracks converge).

## Hard constraints

Pure Python in `klara-core`; JSON-serializable payloads only; tracing must
be optional (a backend without a TraceWriter still works) and must never
change behavior — observe, don't intercept.

## Done when

A ScriptedRobot episode produces an MCAP that opens in Foxglove with the
committed layout showing calls, code, and reason codes; round-trip test
green in CI.
