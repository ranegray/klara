"""The episode loop: run one task attempt at one ladder rung.

This is the centerpiece of the pilot and is deliberately still a stub — the
loop design (turn boundary, feedback routing, retry-vs-replan policy) is
thesis work, not scaffolding. What is already fixed by the contract:

- the loop drives a RobotAPI and never sees a backend type
- every turn's token usage lands in a TurnRecord
- the return value is exactly one EpisodeRecord, appended to the run's JSONL
"""

from __future__ import annotations

from klara_core.api import EnvAPI, RobotAPI
from klara_core.records import EpisodeRecord

from klara_agent.ladder import Rung
from klara_agent.vlm import VLMClient


def run_episode(
    robot: RobotAPI,
    env: EnvAPI,
    vlm: VLMClient,
    task: str,
    rung: Rung,
    seed: int,
    max_turns: int = 10,
) -> EpisodeRecord:
    raise NotImplementedError("pilot work: implement rungs 1-3 (see docs/protocols/)")
