# Build lane 1: Isaac Sim backend

**Goal:** `klara_sim_isaac.backend.IsaacBackend` implements `RobotAPI` +
`EnvAPI` well enough to run scripted cube pick-and-place episodes with the
stressor active.

## Scope

- USD scene: ground plane, table surface, one graspable cube, one SO-101 arm
  imported from `ros2_ws/src/klara_description/urdf/` via Isaac's URDF
  importer. Conversion is scripted (`assets/usd/convert.py` or similar),
  never a hand-edited USD — the URDF stays source of truth.
- Implement the five `RobotAPI` primitives + `EnvAPI.reset(seed)`:
  - `home`, `move_to`: IK + joint drive (Isaac's built-in IK is fine for the
    pilot; note which solver in a comment).
  - `perceive`: returns cube pose(s) in `data["objects"]` per the api.py
    docstring format.
  - `pick`/`place`: approach → grasp/release → lift, with a post-move check
    that maps honest outcomes onto `GRASP_FAILED` / `OUT_OF_WORKSPACE` /
    `TIMEOUT` reason codes.
  - `reset(seed)`: deterministic cube placement per seed. Placement
    distribution is a **reset-contract decision — surface, don't invent**;
    use a placeholder uniform patch and mark it loudly.
- **Stressor wiring (non-negotiable):** every commanded joint target passes
  through `JointStressor.perturb()` before reaching the articulation. This
  is the premise of the thesis; a backend that skips it is wrong even if the
  demo looks better.
- A `scripts/drive_manual.py` smoke script: reset → perceive → pick → place
  under Isaac's Python, printing each PrimitiveResult.

## Out of scope

Camera-based perception (pilot uses ground-truth poses — flag to Rane that
this must be stated in the proposal), the mobile base, bimanual, rungs
logic, any `klara-core` edits beyond none.

## Hard constraints

`omni.*`/`isaacsim` imports live inside functions/methods (CI imports the
package). Pin the Isaac Sim version in `docs/SETUP.md`. No `klara-core`
contract changes — if a primitive can't be implemented as specced, stop and
surface it.

## Done when

Smoke script completes a pick-place episode headless and windowed; perturbed
vs. commanded joint targets are visibly different in a debug log; package
still imports (and `uv run pytest` stays green) without Isaac installed.
