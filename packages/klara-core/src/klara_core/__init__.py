"""klara-core: the frozen contract between the agent and any robot backend.

Everything in this package is pure Python — stdlib plus the `mcap` trace
format library (tracing.py). The agent (klara-agent) and the backends
(klara-sim-isaac now, klara_robot_api over ROS 2 later) both depend on this
package; nothing here may ever import a simulator or ROS.
"""

from klara_core.api import EnvAPI, Pose, RobotAPI
from klara_core.records import EpisodeRecord, FailureCategory, TurnRecord
from klara_core.results import PrimitiveResult, ReasonCode
from klara_core.stressor import ROBO9_STS3215, JointStressor, StressorParams
from klara_core.tracing import TracedRobot, TraceWriter, episode_trace_path

__all__ = [
    "EnvAPI",
    "Pose",
    "RobotAPI",
    "PrimitiveResult",
    "ReasonCode",
    "EpisodeRecord",
    "TurnRecord",
    "FailureCategory",
    "StressorParams",
    "JointStressor",
    "ROBO9_STS3215",
    "TraceWriter",
    "TracedRobot",
    "episode_trace_path",
]
