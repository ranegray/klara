# Setup

Two entry paths. The sim path needs no robot and no ROS — it is the low-barrier
onramp for new team members.

## Path A — sim pilot (agent + Isaac Sim)

Prerequisites: [uv](https://docs.astral.sh/uv/), Python ≥3.10, and for actual
sim runs an RTX GPU + Isaac Sim 6.0.1.

```bash
git clone https://github.com/ranegray/klara.git && cd klara
uv sync --all-packages
uv run pytest            # contract + agent tests, no Isaac needed
```

To run against Isaac Sim, install the workspace packages into Isaac's bundled
Python (one-time, from the Isaac Sim install dir):

```bash
./python.sh -m pip install -e <repo>/packages/klara-core -e <repo>/packages/klara-agent -e <repo>/packages/klara-sim-isaac
./python.sh <repo>/experiments/run_sweep.py <repo>/experiments/configs/pilot_cube.yaml
```

Sweep outputs land in `data/runs/*.jsonl` (gitignored). Analyze with
`uv run python experiments/analysis/plot_frontier.py data/runs/pilot_cube.jsonl`.

## Path B — hardware track (ROS 2)

Prerequisites: ROS 2 Humble, an assembled XLeRobot on the STS3215 bus.

```bash
cd ros2_ws
colcon build --symlink-install
source install/setup.bash
ros2 launch klara_bringup real_one_arm_left.launch.py
```

Visualize with Foxglove (`foxglove_bridge`) using the layouts in
[`dashboards/`](../dashboards/).

## Conventions

- **The contract is frozen:** changes to `klara_core.api`, `results`, or
  `records` go through a PR that updates every backend. Everything else can be
  pushed directly.
- **Run artifacts:** JSONL run records + MCAP traces under `data/` (gitignored).
  Sync `data/` to the shared drive after each session — episode records are
  thesis evidence; treat loss as data loss.
- **Import rule:** only `klara-sim-isaac` imports `omni.*`; only `ros2_ws`
  imports `rclpy`. `klara-core` and `klara-agent` stay pure.
