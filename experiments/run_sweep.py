"""Run a reliability-versus-token sweep from a config file.

Usage (inside Isaac Sim's Python for the isaac backend):
    python experiments/run_sweep.py experiments/configs/pilot_cube.yaml

For each rung x episode: reset env with the episode seed, run the agent loop,
append one EpisodeRecord to the output JSONL. Idempotent restart: skips
(rung, seed) pairs already present in the output file, so a crashed sweep
resumes where it left off. The output file is only ever appended to — run
files are thesis evidence and are never rewritten.

The episode itself is delegated to klara_agent.loop.run_episode via an
"episode runner" callable, so tests can inject a stub runner and exercise
the sweep loop (resume, accounting, logging) without Isaac or a VLM.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import yaml
from klara_agent.ladder import Rung
from klara_agent.vlm import VLMClient
from klara_core.records import EpisodeRecord, append_record, read_records
from klara_core.stressor import StressorParams

REPO_ROOT = Path(__file__).resolve().parents[1]

# An episode runner takes (rung, seed) and returns the finished record.
# The production runner (make_episode_runner) wraps backend + VLM +
# klara_agent.loop.run_episode; tests inject a stub instead.
EpisodeRunner = Callable[[Rung, int], EpisodeRecord]


@dataclass(frozen=True)
class SweepConfig:
    task: str
    backend: str  # "isaac" (hardware backend lands with the ROS 2 track)
    rungs: list[int]
    episodes_per_rung: int
    base_seed: int  # episode i uses seed base_seed + i, identical across rungs
    model: str
    max_turns: int
    stressor: StressorParams
    output: Path


def load_config(path: Path) -> SweepConfig:
    """Parse a sweep config YAML into a SweepConfig.

    A relative `output` path is resolved against the repo root, so the sweep
    lands in data/ no matter which directory it is launched from.
    """
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    output = Path(raw["output"])
    if not output.is_absolute():
        output = REPO_ROOT / output
    return SweepConfig(
        task=str(raw["task"]),
        backend=str(raw["backend"]),
        rungs=[int(r) for r in raw["rungs"]],
        episodes_per_rung=int(raw["episodes_per_rung"]),
        base_seed=int(raw["base_seed"]),
        model=str(raw["model"]),
        max_turns=int(raw["max_turns"]),
        stressor=StressorParams(**raw["stressor"]),
        output=output,
    )


def config_hash(path: Path) -> str:
    """Short digest of the config file bytes, logged in the run header so a
    run file can be matched to the exact config that produced it."""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def git_sha() -> str:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            cwd=REPO_ROOT,
        )
        return proc.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def planned_pairs(config: SweepConfig) -> list[tuple[int, int]]:
    """Every (rung, seed) pair the sweep should produce, in run order.

    Seeds repeat across rungs on purpose: identical start states per seed is
    what lets the analysis say "rung 2 recovered this exact rung-1 failure".
    """
    pairs: list[tuple[int, int]] = []
    for rung in config.rungs:
        for i in range(config.episodes_per_rung):
            pairs.append((rung, config.base_seed + i))
    return pairs


def completed_pairs(output: Path) -> set[tuple[int, int]]:
    """(rung, seed) pairs already recorded in the output JSONL — the resume set."""
    if not output.exists():
        return set()
    return {(record.rung, record.seed) for record in read_records(output)}


def make_vlm(model: str) -> VLMClient:
    raise NotImplementedError(
        "the concrete VLMClient is lane 2 work (docs/briefs/02-agent-loop.md); "
        "wire it here once it lands"
    )


def make_episode_runner(config: SweepConfig) -> EpisodeRunner:
    """Build the production episode runner: backend + VLM + agent loop.

    The isaac import is deliberately inside the branch: it only resolves
    inside Isaac Sim's Python, and CI never takes this path (tests inject a
    stub runner instead of calling this function).
    """
    if config.backend == "isaac":
        from klara_sim_isaac.backend import IsaacBackend

        backend = IsaacBackend(stressor=config.stressor)
        robot, env = backend, backend
    else:
        raise ValueError(f"unknown backend {config.backend!r} (expected 'isaac')")

    vlm = make_vlm(config.model)

    from klara_agent.loop import run_episode

    def runner(rung: Rung, seed: int) -> EpisodeRecord:
        env.reset(seed)
        return run_episode(
            robot=robot,
            env=env,
            vlm=vlm,
            task=config.task,
            rung=rung,
            seed=seed,
            max_turns=config.max_turns,
        )

    return runner


def print_run_header(config: SweepConfig, config_digest: str) -> None:
    print("KLARA sweep")
    print(f"  git_sha:      {git_sha()}")
    print(f"  config_hash:  {config_digest}")
    print(f"  task:         {config.task}")
    print(f"  backend:      {config.backend}")
    print(f"  model:        {config.model}")
    print(f"  rungs:        {config.rungs} x {config.episodes_per_rung} episodes")
    print(f"  base_seed:    {config.base_seed}")
    print(f"  stressor:     {config.stressor.to_dict()}")
    print(f"  output:       {config.output}")


def run_sweep(config: SweepConfig, config_digest: str, episode_runner: EpisodeRunner) -> int:
    """Run every missing (rung, seed) pair and append records to config.output.

    Returns the number of episodes run in this invocation. Restart-safe:
    pairs already present in the output JSONL are skipped, never re-run.
    """
    print_run_header(config, config_digest)

    plan = planned_pairs(config)
    done = completed_pairs(config.output)
    already = sum(1 for pair in plan if pair in done)
    if already:
        print(f"resuming: {already} of {len(plan)} pairs already recorded, skipping those")

    ran = 0
    for position, (rung_number, seed) in enumerate(plan, start=1):
        if (rung_number, seed) in done:
            continue
        rung = Rung(rung_number)
        record = episode_runner(rung, seed)
        append_record(config.output, record)
        ran += 1
        print(
            f"[{position}/{len(plan)}] rung {rung_number} seed {seed}: "
            f"success={record.success} tokens={record.total_tokens} "
            f"wall_clock={record.wall_clock_s:.1f}s"
        )

    print(f"done: ran {ran} episodes this invocation ({already} skipped as already recorded)")
    return ran


def main(config_path: str) -> None:
    path = Path(config_path)
    config = load_config(path)
    digest = config_hash(path)
    runner = make_episode_runner(config)
    run_sweep(config, digest, runner)


if __name__ == "__main__":
    main(sys.argv[1])
