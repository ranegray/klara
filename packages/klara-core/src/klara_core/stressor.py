"""Actuator-unreliability injection.

The thesis stressor is real, measured servo misbehavior injected at the
joint-command boundary — the sim must not be allowed to simulate it away.
Backends call JointStressor.perturb() on every commanded joint target before
handing it to the simulator (or, for calibration experiments, compare its
predictions against the real bus).

Model provenance: defaults come from the peer-reviewed STS3215
characterization (Kotov, HardwareX, Mar 2026, PMC13087586 — the journal
version of the robo9 measurements): 0.62° backlash unloaded rising to 1.30°
loaded, ±1° repeatability, 10-count dead zone at 4096 counts/rev. The 0.85°
default sits mid-range of the unloaded/loaded bracket; revisit when the
stressor protocol note (docs/protocols/stressor-model.md) or our own bench
measurements pin it. Cite whichever source is in force in every EpisodeRecord
(records.py stores the params). Modeling choices (uniform repeatability
noise, symmetric backlash hysteresis) are documented inline and are
themselves defensible-question material — keep them honest.
"""

from __future__ import annotations

import random
from dataclasses import asdict, dataclass
from typing import Any

COUNTS_PER_REV = 4096
DEG_PER_COUNT = 360.0 / COUNTS_PER_REV


@dataclass(frozen=True)
class StressorParams:
    backlash_deg: float = 0.85
    repeatability_deg: float = 1.0
    deadband_counts: int = 10
    seed: int = 0

    @property
    def deadband_deg(self) -> float:
        return self.deadband_counts * DEG_PER_COUNT

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


ROBO9_STS3215 = StressorParams()


class JointStressor:
    """Stateful per-joint unreliability model.

    - Deadband: commands within deadband_deg of the current (perturbed)
      position produce no motion — the servo's 10-count dead zone.
    - Backlash: on direction reversal, the first backlash_deg of commanded
      travel is absorbed by gear lash before the joint moves.
    - Repeatability: uniform noise in ±repeatability_deg on every move that
      does actuate.

    Deterministic for a given (params.seed, call sequence).
    """

    def __init__(self, params: StressorParams, n_joints: int) -> None:
        self.params = params
        self.n_joints = n_joints
        self._rng = random.Random(params.seed)
        self._position: list[float | None] = [None] * n_joints  # unknown until first command
        self._direction: list[int] = [0] * n_joints  # -1, 0, +1

    def perturb(self, commanded_deg: list[float]) -> list[float]:
        """Map commanded joint targets to the positions actually reached."""
        if len(commanded_deg) != self.n_joints:
            raise ValueError(f"expected {self.n_joints} joint targets, got {len(commanded_deg)}")
        reached: list[float] = []
        for j, target in enumerate(commanded_deg):
            current = self._position[j]
            if current is None:
                # First command: seed position at target + repeatability noise.
                actual = target + self._noise()
                self._position[j] = actual
                reached.append(actual)
                continue

            delta = target - current
            if abs(delta) <= self.params.deadband_deg:
                reached.append(current)
                continue

            direction = 1 if delta > 0 else -1
            travel = abs(delta)
            if direction != self._direction[j] and self._direction[j] != 0:
                travel = max(0.0, travel - self.params.backlash_deg)
            self._direction[j] = direction

            actual = current + direction * travel + self._noise()
            self._position[j] = actual
            reached.append(actual)
        return reached

    def _noise(self) -> float:
        r = self.params.repeatability_deg
        return self._rng.uniform(-r, r)
