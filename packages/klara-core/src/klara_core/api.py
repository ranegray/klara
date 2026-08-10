"""The primitive API the agent programs against.

Two backends implement RobotAPI: klara-sim-isaac (Isaac Sim, the pilot) and,
after hardware bring-up, a ROS 2 adapter in ros2_ws. The agent must work
against either without modification — that is the whole point of the seam.

Keep this surface small. Every method added here must be implemented by all
backends and considered in the agent's recovery routing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from klara_core.results import PrimitiveResult


@dataclass(frozen=True)
class Pose:
    """Position (meters) + orientation quaternion (wxyz), in the robot base frame."""

    x: float
    y: float
    z: float
    qw: float = 1.0
    qx: float = 0.0
    qy: float = 0.0
    qz: float = 0.0


@runtime_checkable
class RobotAPI(Protocol):
    """Manipulation-first primitive surface (pilot task: cube pick-and-place)."""

    def home(self) -> PrimitiveResult:
        """Move the arm to its named home configuration."""
        ...

    def perceive(self) -> PrimitiveResult:
        """Observe the scene. On success, data["objects"] is a list of
        {"id": str, "pose": {x, y, z, qw, qx, qy, qz}} entries."""
        ...

    def move_to(self, pose: Pose) -> PrimitiveResult:
        """Move the end effector to the given pose."""
        ...

    def pick(self, object_id: str) -> PrimitiveResult:
        """Grasp the object last seen under this id."""
        ...

    def place(self, pose: Pose) -> PrimitiveResult:
        """Place the currently held object at the given pose."""
        ...


@runtime_checkable
class EnvAPI(Protocol):
    """Episode-level environment control. Owned by the harness, never
    exposed to the agent — the agent cannot reset its way out of trouble."""

    def reset(self, seed: int) -> PrimitiveResult:
        """Restore the pinned start state (the reset contract). Deterministic
        per seed on sim backends; a prompted manual procedure on hardware."""
        ...
