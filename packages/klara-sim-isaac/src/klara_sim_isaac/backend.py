"""Isaac Sim RobotAPI/EnvAPI backend (pilot scaffold).

Responsibilities when implemented:
- load the XLeRobot USD (assets/usd/, converted from klara_description URDF)
- implement RobotAPI primitives over the articulation + a simple IK reach
- apply klara_core.stressor.JointStressor to every commanded joint target
  BEFORE it reaches the articulation controller — the stressor is the
  experiment's premise and must sit in the command path, not in analysis
- implement EnvAPI.reset(seed): pinned cube/table start state per seed
"""

from __future__ import annotations

from klara_core.api import EnvAPI, RobotAPI  # noqa: F401  (contract types)
from klara_core.stressor import StressorParams


class IsaacBackend:
    """Implements RobotAPI + EnvAPI. Construct only inside Isaac's Python."""

    def __init__(self, stressor: StressorParams, headless: bool = True) -> None:
        raise NotImplementedError("pilot work: Isaac scene + adapters")
