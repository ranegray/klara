"""Test doubles for the contract.

ScriptedRobot is a ~50-line stand-in that lets klara-agent's loop, retry
routing, and accounting run in CI, where neither Isaac Sim nor a robot can.
It is deliberately not a simulator: it replays whatever outcomes a test
scripts, nothing more.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable

from klara_core.api import Pose
from klara_core.results import PrimitiveResult, ReasonCode


class ScriptedRobot:
    """RobotAPI double that returns pre-scripted results in order.

    Each primitive call pops the next scripted result; when the script is
    exhausted, everything succeeds. Records the call log for assertions.
    """

    def __init__(self, script: Iterable[PrimitiveResult] = ()) -> None:
        self._script: deque[PrimitiveResult] = deque(script)
        self.calls: list[str] = []

    def _next(self, call: str) -> PrimitiveResult:
        self.calls.append(call)
        if self._script:
            return self._script.popleft()
        return PrimitiveResult.success()

    def home(self) -> PrimitiveResult:
        return self._next("home")

    def perceive(self) -> PrimitiveResult:
        return self._next("perceive")

    def move_to(self, pose: Pose) -> PrimitiveResult:
        return self._next(f"move_to({pose.x:.3f},{pose.y:.3f},{pose.z:.3f})")

    def pick(self, object_id: str) -> PrimitiveResult:
        return self._next(f"pick({object_id})")

    def place(self, pose: Pose) -> PrimitiveResult:
        return self._next(f"place({pose.x:.3f},{pose.y:.3f},{pose.z:.3f})")


def failure(reason: ReasonCode) -> PrimitiveResult:
    """Shorthand for scripting failures in tests."""
    return PrimitiveResult.failure(reason)
