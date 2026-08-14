"""Episode traces: MCAP evidence behind every EpisodeRecord.

Records (records.py) are the dataset; traces are the evidence. When Rane
adjudicates a FailureCategory, he does it by reading the trace in Foxglove
(dashboards/episode-debug.json), so every message here is JSON on a
JSON-schema channel — plain MCAP, no ROS types, readable by both the sim
and hardware tracks.

Two classes, two roles:

- TraceWriter owns one .mcap file and exposes explicit log_* methods for
  everything the harness knows (turn boundaries, agent code, VDM text,
  stressor params, joint targets).
- TracedRobot wraps any RobotAPI and logs each primitive call and its
  PrimitiveResult through a TraceWriter. It is observe-only: results pass
  through unchanged, and a backend used without a TracedRobot behaves
  identically.

File convention: data/runs/<run_id>/episodes/<episode_id>.mcap, next to the
run's JSONL — see episode_trace_path().
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict
from pathlib import Path
from typing import IO, Any

from mcap.writer import Writer as McapWriter

from klara_core.api import Pose, RobotAPI
from klara_core.results import PrimitiveResult
from klara_core.stressor import StressorParams

TOPIC_PRIMITIVE_CALL = "/klara/primitive_call"
TOPIC_PRIMITIVE_RESULT = "/klara/primitive_result"
TOPIC_TURN = "/klara/turn"
TOPIC_AGENT_CODE = "/klara/agent_code"
TOPIC_VDM = "/klara/vdm"
TOPIC_STRESSOR_PARAMS = "/klara/stressor_params"
TOPIC_JOINT_TARGETS = "/klara/joint_targets"

# topic -> (schema name, JSON-schema properties). One schema per channel so
# Foxglove can type the fields (e.g. plot joint arrays, list reason strings).
_SCHEMAS: dict[str, tuple[str, dict[str, Any]]] = {
    TOPIC_PRIMITIVE_CALL: (
        "klara.PrimitiveCall",
        {
            "seq": {"type": "integer"},
            "primitive": {"type": "string"},
            "args": {"type": "object"},
        },
    ),
    TOPIC_PRIMITIVE_RESULT: (
        "klara.PrimitiveResult",
        {
            "seq": {"type": "integer"},
            "primitive": {"type": "string"},
            "ok": {"type": "boolean"},
            "reason": {"type": "string"},
            "message": {"type": "string"},
            "duration_s": {"type": "number"},
            "data": {"type": "object"},
        },
    ),
    TOPIC_TURN: (
        "klara.Turn",
        {
            "turn_index": {"type": "integer"},
            "phase": {"type": "string"},
        },
    ),
    TOPIC_AGENT_CODE: (
        "klara.AgentCode",
        {
            "turn_index": {"type": "integer"},
            "code": {"type": "string"},
        },
    ),
    TOPIC_VDM: (
        "klara.VdmText",
        {
            "turn_index": {"type": "integer"},
            "text": {"type": "string"},
        },
    ),
    TOPIC_STRESSOR_PARAMS: (
        "klara.StressorParams",
        {
            "backlash_deg": {"type": "number"},
            "repeatability_deg": {"type": "number"},
            "deadband_counts": {"type": "integer"},
            "seed": {"type": "integer"},
        },
    ),
    TOPIC_JOINT_TARGETS: (
        "klara.JointTargets",
        {
            "joint_names": {"type": "array", "items": {"type": "string"}},
            "commanded_deg": {"type": "array", "items": {"type": "number"}},
            "perturbed_deg": {"type": "array", "items": {"type": "number"}},
        },
    ),
}


def episode_trace_path(data_dir: Path | str, run_id: str, episode_id: str) -> Path:
    """The file convention: data/runs/<run_id>/episodes/<episode_id>.mcap."""
    return Path(data_dir) / "runs" / run_id / "episodes" / f"{episode_id}.mcap"


class TraceWriter:
    """Writes one episode's trace to one MCAP file.

    Usage:

        with TraceWriter(episode_trace_path("data", run_id, episode_id)) as tw:
            robot = TracedRobot(backend, tw)
            tw.log_stressor_params(params)
            tw.log_turn(0, "start")
            ...

    Channels are JSON-encoded with JSON schemas, so the file opens directly
    in Foxglove and stays compatible with the hardware track's MCAP bags.
    """

    def __init__(self, path: Path | str) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._file: IO[bytes] = path.open("wb")
        self._writer = McapWriter(self._file)
        self._writer.start()
        self._channel_ids: dict[str, int] = {}
        for topic, (schema_name, properties) in _SCHEMAS.items():
            schema = {"type": "object", "properties": properties}
            schema_id = self._writer.register_schema(
                name=schema_name,
                encoding="jsonschema",
                data=json.dumps(schema).encode(),
            )
            self._channel_ids[topic] = self._writer.register_channel(
                topic=topic,
                message_encoding="json",
                schema_id=schema_id,
            )
        self._next_seq = 0
        self._closed = False

    def log_primitive_call(self, primitive: str, args: dict[str, Any]) -> int:
        """Log a primitive call starting. Returns the seq that pairs the
        call with its result message."""
        seq = self._next_seq
        self._next_seq += 1
        self._log(TOPIC_PRIMITIVE_CALL, {"seq": seq, "primitive": primitive, "args": args})
        return seq

    def log_primitive_result(self, seq: int, primitive: str, result: PrimitiveResult) -> None:
        self._log(
            TOPIC_PRIMITIVE_RESULT,
            {
                "seq": seq,
                "primitive": primitive,
                "ok": result.ok,
                "reason": result.reason.value,
                "message": result.message,
                "duration_s": result.duration_s,
                "data": result.data,
            },
        )

    def log_turn(self, turn_index: int, phase: str) -> None:
        if phase not in ("start", "end"):
            raise ValueError(f'phase must be "start" or "end", got {phase!r}')
        self._log(TOPIC_TURN, {"turn_index": turn_index, "phase": phase})

    def log_agent_code(self, turn_index: int, code: str) -> None:
        self._log(TOPIC_AGENT_CODE, {"turn_index": turn_index, "code": code})

    def log_vdm_text(self, turn_index: int, text: str) -> None:
        self._log(TOPIC_VDM, {"turn_index": turn_index, "text": text})

    def log_stressor_params(self, params: StressorParams) -> None:
        self._log(TOPIC_STRESSOR_PARAMS, params.to_dict())

    def log_joint_targets(
        self,
        joint_names: list[str],
        commanded_deg: list[float],
        perturbed_deg: list[float],
    ) -> None:
        """Log one commanded-vs-perturbed pair. Backends call this right
        where they apply JointStressor.perturb(), so the trace shows the
        stressor exactly as the command path saw it."""
        if not (len(joint_names) == len(commanded_deg) == len(perturbed_deg)):
            raise ValueError(
                f"joint_names ({len(joint_names)}), commanded_deg ({len(commanded_deg)}) "
                f"and perturbed_deg ({len(perturbed_deg)}) must have equal lengths"
            )
        self._log(
            TOPIC_JOINT_TARGETS,
            {
                "joint_names": joint_names,
                "commanded_deg": commanded_deg,
                "perturbed_deg": perturbed_deg,
            },
        )

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._writer.finish()
        self._file.close()

    def __enter__(self) -> TraceWriter:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def _log(self, topic: str, payload: dict[str, Any]) -> None:
        now = time.time_ns()
        self._writer.add_message(
            channel_id=self._channel_ids[topic],
            log_time=now,
            publish_time=now,
            data=json.dumps(payload).encode(),
        )


class TracedRobot:
    """RobotAPI decorator that logs every primitive call and result.

    Observe-only by construction: each method logs the call, invokes the
    wrapped robot, logs the result, and returns that result untouched. If
    the wrapped robot raises, the exception propagates (the trace then ends
    with an unpaired call message — itself useful evidence).
    """

    def __init__(self, robot: RobotAPI, writer: TraceWriter) -> None:
        self._robot = robot
        self._writer = writer

    def home(self) -> PrimitiveResult:
        seq = self._writer.log_primitive_call("home", {})
        result = self._robot.home()
        self._writer.log_primitive_result(seq, "home", result)
        return result

    def perceive(self) -> PrimitiveResult:
        seq = self._writer.log_primitive_call("perceive", {})
        result = self._robot.perceive()
        self._writer.log_primitive_result(seq, "perceive", result)
        return result

    def move_to(self, pose: Pose) -> PrimitiveResult:
        seq = self._writer.log_primitive_call("move_to", {"pose": asdict(pose)})
        result = self._robot.move_to(pose)
        self._writer.log_primitive_result(seq, "move_to", result)
        return result

    def pick(self, object_id: str) -> PrimitiveResult:
        seq = self._writer.log_primitive_call("pick", {"object_id": object_id})
        result = self._robot.pick(object_id)
        self._writer.log_primitive_result(seq, "pick", result)
        return result

    def place(self, pose: Pose) -> PrimitiveResult:
        seq = self._writer.log_primitive_call("place", {"pose": asdict(pose)})
        result = self._robot.place(pose)
        self._writer.log_primitive_result(seq, "place", result)
        return result
