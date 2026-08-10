# xlerobot-research

A senior-thesis research platform and web console for studying embodied coding agents on low-cost XLeRobot hardware.

**Full specification:** [`docs/xlerobot-research-spec.md`](docs/xlerobot-research-spec.md)

## Status

**Early bring-up · pre-semester planning (Spring 2026).**

What works today is a ROS 2 Humble bring-up path: robot description, fake hardware, guarded trajectories, and a harness event stream. The agent harness, primitive layer, web console, and eval logging described in the project spec are **not implemented yet**.

| Layer | Status |
| --- | --- |
| ROS 2 bring-up (`xle_description`, `xle_hardware`, `xle_fake_hardware`, …) | In progress — fake one-arm path |
| Primitive API + perception/nav skills | Planned — contract in spec §7 |
| Agent harness (CaP-X-style loop) | Planned — `xle_harness`, `xle_agent_interfaces` are shells |
| Web console (FastAPI + React, Jetson-hosted) | Planned — Phase 0 is WebRTC + record button |
| Eval / trial logging (SQLite) | Planned |

## North star

We are testing one bet:

> **Agentic test-time compute can buy back the reliability that cheap hardware gives away.**

CaP-X showed that retry, execution feedback, and visual differencing can recover manipulation reliability without training — but on well-behaved embodiments. Our platform is the opposite: sub-centimeter servo error, flexy wrists, a base that slips. This project measures whether the recovery machinery keeps up, and at what cost.

The repo is two intertwined things:

1. **A research program** (senior theses, CU Boulder) — reliability, mechanism ablation, cost-per-success, and failure taxonomy on a six-task suite.
2. **A web app** — the experimental instrument: live operation, the agent's generated code beside its execution trace and visual diffs, and per-trial logging that aggregates into the tables the thesis reports.

The app is not a side project. Every feature exists because an experiment needs it.

## Architecture

Four layers. See the spec for diagrams, ownership, and timeline.

```text
Browser (React console, LAN)
  ↔ FastAPI on Jetson (WebSocket/REST, WebRTC video, SQLite trials)
    → Agent harness (VLM loop, test-time compute, budget caps)
      → Primitive layer (pick, place, navigate_to, detect, …)
        → ROS 2 stack (motor I/O, IK, perception, SLAM/Nav2)
          ↔ XLeRobot hardware
```

**Substrate:** Built on the embedded ROS 2 autonomy stack from [*Cutting the Cord*](https://github.com/ranegray) (onboard perception, IK, SLAM, navigation, teleop). The `ros2_ws/` packages here are the research-layer bring-up and safety gates that sit under the primitive contract.

**The frozen interface** between the primitive layer and the agent harness is `PrimitiveResult` + a closed reason-code enum (spec §7). Agree and stub it in Week 1–2 so harness development never blocks on perception maturity.

## Web console (planned)

Served from the Jetson over LAN. Not a Foxglove clone — an agent-aware eval instrument.

**MVP (must exist to run any experiment):**

- Live view — WebRTC camera feed(s), robot/joint/base state, tri-bus power monitor
- Manual teleop + E-stop
- Agent panel — generated program beside live execution trace
- Trial logging — success, iterations, tokens, cost → SQLite

**v1 (thesis instrument):** visual-diff viewer, eval runner (task × condition × N trials), aggregate tables for the writeup.

**Explicitly cut:** auth, cloud sync, multi-robot fleet views, SaaS-shaped features.

Stack: FastAPI + `rclpy`/rosbridge, WebRTC (`aiortc` or GStreamer), React + Vite, SQLite.

## Quick start (ROS bring-up)

Fake-hardware-first path — the current working milestone:

```bash
git clone https://github.com/ranegray/xlerobot-research.git
cd xlerobot-research/ros2_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
ros2 launch xle_bringup fake_one_arm.launch.py
```

This should bring up `robot_state_publisher`, fake joint states, `/tf`, guarded trajectory forwarding, and `/harness/events`.

See [`docs/simulation/fake_hardware.md`](docs/simulation/fake_hardware.md) for commands, topic contract, and bag recording.

Real left-arm bring-up (read-only by default):

```bash
ros2 launch xle_bringup real_one_arm_left.launch.py
```

## ROS 2 packages

| Package | Role | Status |
| --- | --- | --- |
| `xle_description` | URDF, meshes, RViz | Implemented |
| `xle_bringup` | Launch composition | Implemented |
| `xle_hardware` | STS3215 bus, calibration, joint states, command guard | Implemented |
| `xle_fake_hardware` | Interface-compatible fake motors | Implemented |
| `xle_perception` | RealSense, color detect, reach-to-pose | Partial |
| `xle_harness` | Episode state, trial logging, harness gates | Shell only |
| `xle_benchmarks` | Task suite protocols, eval runner backend | Shell only |
| `xle_agent_interfaces` | Primitive API boundary for the agent | Shell only |

## Core ROS 2 interface (bring-up)

Global state: `/robot_description`, `/joint_states`, `/tf`, `/tf_static`

Arms (public → guarded):

- `/left_arm_controller/joint_trajectory` → `/left_arm_controller/guarded_joint_trajectory`
- `/right_arm_controller/joint_trajectory` → `/right_arm_controller/guarded_joint_trajectory`

Harness (implemented today):

- `/harness/events` — JSON events, schema `xle.harness.event.v0` (`command_accepted`, `command_rejected`, `target_rejected`)

Planned: `/episode/state`, `/episode/abort`, controller state, gripper topics. Standard ROS message types before custom messages.

## Task suite (research)

Six tasks graded by recoverability and precision demand — see spec §8. Start with fiducial-tagged objects (Tasks 1–2) so the harness is the variable, not perception debugging.

| Task | What it probes |
| --- | --- |
| Pick cube → bin | Baseline; retry value |
| Stack 2–3 cubes | Placement error under retry |
| Pour / transfer | Irreversible failure (H1) |
| Bimanual handover | Two unreliable arms |
| Mobile fetch | Base noise + loco-manipulation |
| Tidy the table | Error compounding over long horizon |

Conditions: single-shot baseline → +retry/feedback → +visual diff → +ensembling, vs. sim/literature reference.

## Safety

Generated or agent-written code must never bypass the harness or command guard.

- Commands are bounded before they reach hardware
- Primitives refuse unsafe requests with a structured reason code — never silent no-ops
- Manual interventions and E-stop events are logged
- Agent access is mediated through the primitive API, not raw motor topics

## Documentation

| Doc | Contents |
| --- | --- |
| [`docs/xlerobot-research-spec.md`](docs/xlerobot-research-spec.md) | Project spec — RQs, architecture, timeline, risks |
| [`docs/simulation/fake_hardware.md`](docs/simulation/fake_hardware.md) | Fake-hardware launch and bag targets |
| [`docs/experiments/replication_bundle_template.md`](docs/experiments/replication_bundle_template.md) | Replication bundle template |

## Timeline (summary)

| Phase | Target |
| --- | --- |
| **0 — pre-semester** | WebRTC skeleton + record button; CaP-Gym in sim; freeze primitive contract |
| **1 — weeks 1–3** | Primitive stubs on fiducials; single-shot harness; app shell; Task 1 trials |
| **2 — weeks 4–7** | Retry + visual diff; eval logging in app; Tasks 1–3 |
| **3 — weeks 8–11** | Full task suite; eval runner + aggregate tables |
| **4–5 — weeks 12–16** | Trial-scale experiments, analysis, thesis writeup |

Assume ~30–40% slip. Details in the spec.

## Relationship to XLeRobot

This is not the upstream [XLeRobot](https://github.com/Vector-Wangel/XLeRobot) repository. It is a research stack and eval console for XLeRobot hardware.

The initial robot model is vendored from XLeRobot at commit `137865981ca9e828d0923804cf77ededd22c7816`. See [`third_party/XLeRobot-URDF-PROVENANCE.md`](third_party/XLeRobot-URDF-PROVENANCE.md).

## License

License not selected yet. Prefer a permissive license for code and clear separate treatment for imported meshes, CAD, images, and external assets.
