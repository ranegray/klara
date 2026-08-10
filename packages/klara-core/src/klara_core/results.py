"""Primitive result types.

This is the frozen half of the contract: every primitive on every backend
returns a PrimitiveResult carrying one ReasonCode. The agent's recovery
routing keys off the reason code, so adding a code is a contract change —
do it deliberately, in one PR that updates all backends, never ad hoc.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ReasonCode(str, Enum):
    OK = "OK"
    OBJECT_NOT_VISIBLE = "OBJECT_NOT_VISIBLE"
    OUT_OF_WORKSPACE = "OUT_OF_WORKSPACE"
    GRASP_FAILED = "GRASP_FAILED"
    COLLISION_AVOIDED = "COLLISION_AVOIDED"
    TIMEOUT = "TIMEOUT"
    NAV_FAILED = "NAV_FAILED"


@dataclass(frozen=True)
class PrimitiveResult:
    """Outcome of a single primitive call, on any backend."""

    ok: bool
    reason: ReasonCode
    message: str = ""
    duration_s: float = 0.0
    # Structured observation payload (e.g. perceive() puts detected objects
    # here). JSON-serializable values only — this crosses process boundaries.
    data: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.ok != (self.reason is ReasonCode.OK):
            raise ValueError("ok must be True iff reason is OK")

    @classmethod
    def success(cls, **kwargs: Any) -> PrimitiveResult:
        return cls(ok=True, reason=ReasonCode.OK, **kwargs)

    @classmethod
    def failure(cls, reason: ReasonCode, **kwargs: Any) -> PrimitiveResult:
        if reason is ReasonCode.OK:
            raise ValueError("failure() requires a non-OK reason")
        return cls(ok=False, reason=reason, **kwargs)
