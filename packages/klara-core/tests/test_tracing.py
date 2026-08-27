import json
import re
from pathlib import Path

from klara_core.api import Pose
from klara_core.results import PrimitiveResult, ReasonCode
from klara_core.stressor import ROBO9_STS3215
from klara_core.testing import ScriptedRobot
from klara_core.trace_fixture import JOINT_NAMES, TURN_0_CODE, TURN_1_CODE, write_fixture_trace
from klara_core.tracing import (
    TOPIC_AGENT_CODE,
    TOPIC_JOINT_TARGETS,
    TOPIC_PRIMITIVE_CALL,
    TOPIC_PRIMITIVE_RESULT,
    TOPIC_STRESSOR_PARAMS,
    TOPIC_TURN,
    TOPIC_VDM,
    TracedRobot,
    TraceWriter,
    episode_trace_path,
)
from mcap.reader import make_reader

REPO_ROOT = Path(__file__).parents[3]


def read_messages_by_topic(path: Path) -> dict[str, list[dict]]:
    """Read a trace back with the mcap reader, decoded JSON grouped by topic."""
    by_topic: dict[str, list[dict]] = {}
    with path.open("rb") as f:
        reader = make_reader(f)
        for _schema, channel, message in reader.iter_messages():
            by_topic.setdefault(channel.topic, []).append(json.loads(message.data))
    return by_topic


def test_episode_trace_path_convention(tmp_path):
    path = episode_trace_path(tmp_path / "data", "run-3", "ep-07")
    assert path == tmp_path / "data" / "runs" / "run-3" / "episodes" / "ep-07.mcap"


def test_fixture_trace_round_trips(tmp_path):
    path = episode_trace_path(tmp_path, "fixture", "ep-0")
    write_fixture_trace(path)
    by_topic = read_messages_by_topic(path)

    # Every topic the layout depends on is present.
    assert set(by_topic) == {
        TOPIC_PRIMITIVE_CALL,
        TOPIC_PRIMITIVE_RESULT,
        TOPIC_TURN,
        TOPIC_AGENT_CODE,
        TOPIC_VDM,
        TOPIC_STRESSOR_PARAMS,
        TOPIC_JOINT_TARGETS,
    }

    # Primitive calls and results pair up 1:1 by seq, in order.
    calls = by_topic[TOPIC_PRIMITIVE_CALL]
    results = by_topic[TOPIC_PRIMITIVE_RESULT]
    assert [c["primitive"] for c in calls] == [
        "home", "perceive", "move_to", "pick",  # turn 0
        "perceive", "move_to", "pick", "place",  # turn 1
    ]
    assert [r["seq"] for r in results] == [c["seq"] for c in calls]
    assert [r["primitive"] for r in results] == [c["primitive"] for c in calls]

    # The reason-code history shows the scripted failure and the recovery.
    reasons = [r["reason"] for r in results]
    assert reasons[3] == ReasonCode.GRASP_FAILED.value
    assert all(reason == ReasonCode.OK.value for i, reason in enumerate(reasons) if i != 3)
    assert results[3]["ok"] is False
    assert results[3]["message"] == "gripper closed on air"
    # perceive's structured data payload survives the round trip.
    assert results[1]["data"]["objects"][0]["id"] == "cube"

    # Turn boundaries and per-turn agent code.
    assert [(t["turn_index"], t["phase"]) for t in by_topic[TOPIC_TURN]] == [
        (0, "start"), (0, "end"), (1, "start"), (1, "end"),
    ]
    assert [m["code"] for m in by_topic[TOPIC_AGENT_CODE]] == [TURN_0_CODE, TURN_1_CODE]
    assert by_topic[TOPIC_VDM][0]["turn_index"] == 1

    # Stressor params match the versioned config that generated the trace.
    assert by_topic[TOPIC_STRESSOR_PARAMS] == [ROBO9_STS3215.to_dict()]

    # Commanded vs perturbed joint targets, aligned per joint.
    for m in by_topic[TOPIC_JOINT_TARGETS]:
        assert m["joint_names"] == JOINT_NAMES
        assert len(m["commanded_deg"]) == len(m["perturbed_deg"]) == len(JOINT_NAMES)


def test_traced_robot_is_observe_only(tmp_path):
    scripted_results = [
        PrimitiveResult.success(),
        PrimitiveResult.failure(ReasonCode.OBJECT_NOT_VISIBLE),
        PrimitiveResult.success(data={"note": "reached"}),
        PrimitiveResult.failure(ReasonCode.GRASP_FAILED),
        PrimitiveResult.success(),
    ]
    inner = ScriptedRobot(scripted_results)
    with TraceWriter(tmp_path / "trace.mcap") as writer:
        robot = TracedRobot(inner, writer)
        returned = [
            robot.home(),
            robot.perceive(),
            robot.move_to(Pose(x=0.1, y=0.2, z=0.3)),
            robot.pick("cube"),
            robot.place(Pose(x=0.0, y=0.0, z=0.0)),
        ]
    # The wrapper returns the inner robot's results untouched, in order.
    assert returned == scripted_results
    # And the inner robot saw exactly the calls the caller made.
    assert inner.calls == [
        "home", "perceive", "move_to(0.100,0.200,0.300)", "pick(cube)", "place(0.000,0.000,0.000)",
    ]


def test_layout_references_only_traced_topics():
    # The committed Foxglove layout must not reference topics that traces
    # never contain — that is the structural half of "the layout opens".
    layout_path = REPO_ROOT / "dashboards" / "episode-debug.json"
    layout = json.loads(layout_path.read_text())
    referenced = set(re.findall(r"/klara/[a-z_]+", json.dumps(layout)))
    assert referenced  # the layout actually points at trace topics
    assert referenced <= {
        TOPIC_PRIMITIVE_CALL,
        TOPIC_PRIMITIVE_RESULT,
        TOPIC_TURN,
        TOPIC_AGENT_CODE,
        TOPIC_VDM,
        TOPIC_STRESSOR_PARAMS,
        TOPIC_JOINT_TARGETS,
    }
    # Every panel placed in the layout tree has a config, and vice versa.
    placed = set(re.findall(r'"([A-Za-z]+![A-Za-z0-9]+)"', json.dumps(layout["layout"])))
    assert placed == set(layout["configById"])
