# KLARA

**Kinematic Limits, Agentic Recovery Architecture**

A senior-thesis research platform asking one question: **does agentic
test-time compute compensate for unreliable hardware, and at what token
cost?**

Cheap servos (Feetech STS3215: ~0.85° backlash, ±1° repeatability, 10-count
dead zone) take task reliability away. A CaP-style coding agent (retry,
structured execution feedback, visual differencing) may buy it back, one
token at a time. KLARA measures the reliability-per-token frontier on a
low-cost XLeRobot platform: how much each mechanism recovers, where recovery
hits its ceiling, and where paying tokens to paper over bad hardware becomes
false economy.

## Architecture

The agent programs against one frozen primitive contract; sim and hardware
are interchangeable backends behind it. The actuator unreliability is
*injected* at the joint-command boundary from measured servo
characterization: the stressor is real even when the robot is simulated.

```
klara-agent          the compensating machinery under test (compute ladder,
   │                 VLM client, episode loop)
klara-core           the frozen contract: RobotAPI, PrimitiveResult + reason
   │                 codes, stressor model, episode run records
   ├── klara-sim-isaac    Isaac Sim backend (pilot experiments)
   └── ros2_ws/           hardware backend: STS3215 bus, bringup, perception
```

| Directory | What it is |
| --- | --- |
| `packages/klara-core` | The contract. Pure stdlib, CI-tested. Changes require a PR. |
| `packages/klara-agent` | Compute ladder rungs 1–5, token accounting, agent loop. |
| `packages/klara-sim-isaac` | Isaac Sim adapter (runs in Isaac's bundled Python). |
| `ros2_ws/` | ROS 2 Humble hardware track: `klara_hardware`, `klara_bringup`, `klara_description`, `klara_perception`. |
| `experiments/` | Sweep configs, runner, reliability-per-token analysis. |
| `dashboards/` | Foxglove layouts (live episodes + MCAP post-mortems). |
| `assets/usd/` | USD converted from the `klara_description` URDF. |
| `docs/` | [Setup](docs/SETUP.md), [protocol notes](docs/protocols/), [archived v0.1 spec](docs/archive/xlerobot-research-spec-v0.1.md). |

## Getting started

See [docs/SETUP.md](docs/SETUP.md). The sim path (`uv sync --all-packages &&
uv run pytest`) needs no robot, no ROS, and no GPU until you run Isaac
itself.

## Evidence conventions

Every episode writes one `EpisodeRecord` (JSONL): success, per-turn token
counts, wall clock, failure attribution, seed, stressor parameters, git SHA.
Records are append-only thesis evidence; see `klara_core/records.py` for the
schema and [docs/protocols/](docs/protocols/) for the accounting rules.

## Lineage

Built on the open-source [XLeRobot](https://github.com/Vector-Wangel/XLeRobot)
hardware platform (Wang, 2025). See [third_party/](third_party/) for the
URDF license and provenance. KLARA is an independent research stack; the
robot stays XLeRobot, the name applies to what runs on it.
