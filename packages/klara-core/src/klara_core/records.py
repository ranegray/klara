"""Episode run records — the thesis dataset.

Every trial, on every backend, at every ladder rung, writes exactly one
EpisodeRecord to a JSONL file. The reliability-per-token curves in the
proposal and thesis are a groupby over these records, so the schema carries
every field the evaluation protocol demands: success, per-turn token counts,
wall clock, failure attribution, and full reproducibility metadata (rung,
model, machinery, seed, stressor params, git SHA).

Schema changes are contract changes: bump SCHEMA_VERSION and keep readers
backward-compatible — old records are evidence and are never rewritten.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1


class FailureCategory(str, Enum):
    """Failure attribution buckets (one per failed episode)."""

    AGENT_REASONING = "AGENT_REASONING"
    PERCEPTION = "PERCEPTION"
    POLICY_CONTROL = "POLICY_CONTROL"
    HARNESS_PROTOCOL = "HARNESS_PROTOCOL"
    HARDWARE_ENVIRONMENT = "HARDWARE_ENVIRONMENT"


@dataclass
class TurnRecord:
    index: int
    prompt_tokens: int
    completion_tokens: int
    wall_clock_s: float
    primitive_calls: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class EpisodeRecord:
    episode_id: str
    task: str
    backend: str  # "isaac" | "hardware"
    rung: int  # compute-ladder rung (see klara_agent.ladder)
    model: str
    machinery: list[str]  # enabled mechanisms, e.g. ["multi_turn", "vdm"]
    seed: int
    stressor: dict[str, Any]  # StressorParams.to_dict()
    success: bool
    failure_category: str | None = None  # FailureCategory value when success is False
    turns: list[TurnRecord] = field(default_factory=list)
    wall_clock_s: float = 0.0
    resets: int = 0
    interventions: int = 0
    started_at: str = ""  # ISO 8601
    git_sha: str = ""
    notes: str = ""
    schema_version: int = SCHEMA_VERSION

    @property
    def total_prompt_tokens(self) -> int:
        return sum(t.prompt_tokens for t in self.turns)

    @property
    def total_completion_tokens(self) -> int:
        return sum(t.completion_tokens for t in self.turns)

    @property
    def total_tokens(self) -> int:
        return self.total_prompt_tokens + self.total_completion_tokens

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # Persist the derived totals so analysis tools that stream JSONL
        # don't have to re-implement the aggregation.
        d["total_tokens"] = self.total_tokens
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> EpisodeRecord:
        d = dict(d)
        d.pop("total_tokens", None)
        d["turns"] = [TurnRecord(**t) for t in d.get("turns", [])]
        return cls(**d)


def append_record(path: Path | str, record: EpisodeRecord) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record.to_dict()) + "\n")


def read_records(path: Path | str) -> list[EpisodeRecord]:
    with Path(path).open(encoding="utf-8") as f:
        return [EpisodeRecord.from_dict(json.loads(line)) for line in f if line.strip()]
