"""Generate a fixture episode trace without Isaac or hardware.

ScriptedRobot plays the backend and a hard-coded two-turn "agent" script
plays the agent: turn 0 ends in a GRASP_FAILED pick, turn 1 recovers and
succeeds. The trace exercises every topic TraceWriter knows, so it doubles
as the round-trip test input (tests/test_tracing.py) and as the sample file
for checking dashboards/episode-debug.json in Foxglove:

    uv run python -m klara_core.trace_fixture
    # -> data/runs/fixture/episodes/fixture-episode-0.mcap
"""

from __future__ import annotations

import argparse
from pathlib import Path

from klara_core.api import Pose
from klara_core.results import PrimitiveResult, ReasonCode
from klara_core.stressor import ROBO9_STS3215, JointStressor
from klara_core.testing import ScriptedRobot
from klara_core.tracing import TracedRobot, TraceWriter, episode_trace_path

JOINT_NAMES = ["shoulder_pan", "elbow_flex"]

TURN_0_CODE = """\
robot.home()
scene = robot.perceive()
cube = scene.data["objects"][0]
robot.move_to(Pose(x=cube["pose"]["x"], y=cube["pose"]["y"], z=0.05))
robot.pick("cube")
"""

TURN_1_CODE = """\
# Retry after GRASP_FAILED: re-perceive and approach lower before picking.
scene = robot.perceive()
cube = scene.data["objects"][0]
robot.move_to(Pose(x=cube["pose"]["x"], y=cube["pose"]["y"], z=0.02))
robot.pick("cube")
robot.place(Pose(x=-0.15, y=0.20, z=0.05))
"""

VDM_TEXT_TURN_1 = (
    "Before/after diff: cube unmoved at (0.25, 0.00); gripper closed above "
    "the cube. Approach height looks too high."
)


def write_fixture_trace(path: Path | str) -> None:
    """Write the two-turn fixture episode to the given .mcap path."""
    # Scripted outcomes, in call order. Once the script is exhausted,
    # ScriptedRobot returns success for everything (all of turn 1).
    scripted = ScriptedRobot(
        [
            PrimitiveResult.success(),  # turn 0: home
            PrimitiveResult.success(  # turn 0: perceive
                data={
                    "objects": [
                        {
                            "id": "cube",
                            "pose": {
                                "x": 0.25, "y": 0.0, "z": 0.02,
                                "qw": 1.0, "qx": 0.0, "qy": 0.0, "qz": 0.0,
                            },
                        }
                    ]
                }
            ),
            PrimitiveResult.success(),  # turn 0: move_to
            PrimitiveResult.failure(  # turn 0: pick
                ReasonCode.GRASP_FAILED, message="gripper closed on air"
            ),
        ]
    )
    # The fixture stands in for the backend too: it runs a JointStressor and
    # logs commanded-vs-perturbed pairs the way a real backend would at its
    # command boundary.
    stressor = JointStressor(ROBO9_STS3215, n_joints=len(JOINT_NAMES))

    with TraceWriter(path) as writer:
        robot = TracedRobot(scripted, writer)
        writer.log_stressor_params(ROBO9_STS3215)

        writer.log_turn(0, "start")
        writer.log_agent_code(0, TURN_0_CODE)
        robot.home()
        robot.perceive()
        for commanded in ([0.0, 0.0], [25.0, -10.0], [25.4, -30.0]):
            writer.log_joint_targets(JOINT_NAMES, commanded, stressor.perturb(commanded))
        robot.move_to(Pose(x=0.25, y=0.0, z=0.05))
        robot.pick("cube")  # scripted GRASP_FAILED
        writer.log_turn(0, "end")

        writer.log_turn(1, "start")
        writer.log_vdm_text(1, VDM_TEXT_TURN_1)
        writer.log_agent_code(1, TURN_1_CODE)
        robot.perceive()
        for commanded in ([25.4, -35.0], [10.0, -35.0], [-20.0, 15.0]):
            writer.log_joint_targets(JOINT_NAMES, commanded, stressor.perturb(commanded))
        robot.move_to(Pose(x=0.25, y=0.0, z=0.02))
        robot.pick("cube")
        robot.place(Pose(x=-0.15, y=0.20, z=0.05))
        writer.log_turn(1, "end")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default="data", help="run-artifact root (default: data)")
    parser.add_argument("--run-id", default="fixture")
    parser.add_argument("--episode-id", default="fixture-episode-0")
    args = parser.parse_args(argv)
    path = episode_trace_path(args.data_dir, args.run_id, args.episode_id)
    write_fixture_trace(path)
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
