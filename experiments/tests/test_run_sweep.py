"""Sweep-runner tests: config loading, the full run, and resumability.

The episode itself is lane 2 work (klara_agent.loop.run_episode is still a
stub), so these tests inject a stub episode runner that returns synthetic
EpisodeRecords — exactly the seam run_sweep.main uses for the real thing.
"""

import dataclasses
from pathlib import Path

import pytest
import run_sweep
from klara_agent.ladder import Rung
from klara_core.records import EpisodeRecord, TurnRecord, append_record, read_records
from klara_core.stressor import StressorParams
from run_sweep import (
    SweepConfig,
    completed_pairs,
    load_config,
    make_episode_runner,
    planned_pairs,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
PILOT_CONFIG = REPO_ROOT / "experiments" / "configs" / "pilot_cube.yaml"


def make_record(rung: int, seed: int, success: bool = True, tokens: int = 100) -> EpisodeRecord:
    return EpisodeRecord(
        episode_id=f"test-r{rung}-s{seed}",
        task="cube_pick_place",
        backend="scripted",
        rung=rung,
        model="stub",
        machinery=Rung(rung).machinery,
        seed=seed,
        stressor=StressorParams().to_dict(),
        success=success,
        turns=[TurnRecord(index=0, prompt_tokens=tokens, completion_tokens=0, wall_clock_s=1.0)],
        wall_clock_s=1.0,
    )


def make_config(tmp_path: Path, rungs: list[int], episodes_per_rung: int) -> SweepConfig:
    return SweepConfig(
        task="cube_pick_place",
        backend="isaac",
        rungs=rungs,
        episodes_per_rung=episodes_per_rung,
        base_seed=0,
        model="stub",
        max_turns=10,
        stressor=StressorParams(),
        output=tmp_path / "run.jsonl",
    )


def stub_runner(calls: list[tuple[int, int]]):
    """An episode runner double that logs its (rung, seed) calls."""

    def runner(rung: Rung, seed: int) -> EpisodeRecord:
        calls.append((int(rung), seed))
        return make_record(int(rung), seed)

    return runner


def test_load_config_parses_the_pilot_config():
    config = load_config(PILOT_CONFIG)
    assert config.task == "cube_pick_place"
    assert config.backend == "isaac"
    assert config.rungs == [1, 2, 3]
    assert config.episodes_per_rung == 20
    assert config.base_seed == 0
    assert config.max_turns == 10
    assert config.stressor == StressorParams(
        backlash_deg=0.85, repeatability_deg=1.0, deadband_counts=10, seed=0
    )
    # Relative output paths resolve against the repo root, not the cwd.
    assert config.output == REPO_ROOT / "data" / "runs" / "pilot_cube.jsonl"


def test_planned_pairs_repeats_seeds_across_rungs(tmp_path):
    config = make_config(tmp_path, rungs=[1, 2], episodes_per_rung=3)
    assert planned_pairs(config) == [(1, 0), (1, 1), (1, 2), (2, 0), (2, 1), (2, 2)]


def test_full_sweep_writes_every_pair(tmp_path, capsys):
    config = make_config(tmp_path, rungs=[1, 2], episodes_per_rung=3)
    calls: list[tuple[int, int]] = []

    ran = run_sweep.run_sweep(config, "abc123def456", stub_runner(calls))

    assert ran == 6
    assert calls == planned_pairs(config)
    records = read_records(config.output)
    assert {(r.rung, r.seed) for r in records} == set(planned_pairs(config))

    out = capsys.readouterr().out
    assert "config_hash:  abc123def456" in out
    assert "git_sha:" in out
    assert "backlash_deg" in out  # stressor params belong in the run header
    assert "rung 1 seed 0: success=True tokens=100" in out


def test_restart_skips_already_recorded_pairs(tmp_path):
    config = make_config(tmp_path, rungs=[1, 2], episodes_per_rung=3)
    # A previous invocation got through rung 1 and one rung-2 episode.
    for rung, seed in [(1, 0), (1, 1), (1, 2), (2, 0)]:
        append_record(config.output, make_record(rung, seed))

    calls: list[tuple[int, int]] = []
    ran = run_sweep.run_sweep(config, "abc123def456", stub_runner(calls))

    assert ran == 2
    assert calls == [(2, 1), (2, 2)]
    records = read_records(config.output)
    assert len(records) == 6  # appended, no duplicates, nothing rewritten
    assert {(r.rung, r.seed) for r in records} == set(planned_pairs(config))


def test_restart_on_a_complete_run_does_nothing(tmp_path):
    config = make_config(tmp_path, rungs=[1], episodes_per_rung=2)
    for _, seed in planned_pairs(config):
        append_record(config.output, make_record(1, seed))
    before = read_records(config.output)

    calls: list[tuple[int, int]] = []
    ran = run_sweep.run_sweep(config, "abc123def456", stub_runner(calls))

    assert ran == 0
    assert calls == []
    assert read_records(config.output) == before


def test_completed_pairs_on_missing_file_is_empty(tmp_path):
    assert completed_pairs(tmp_path / "nope.jsonl") == set()


def test_unknown_backend_is_rejected(tmp_path):
    config = make_config(tmp_path, rungs=[1], episodes_per_rung=1)
    config = dataclasses.replace(config, backend="mujoco")
    with pytest.raises(ValueError, match="unknown backend"):
        make_episode_runner(config)


def test_invalid_rung_number_is_rejected(tmp_path):
    config = make_config(tmp_path, rungs=[99], episodes_per_rung=1)
    with pytest.raises(ValueError):
        run_sweep.run_sweep(config, "abc123def456", stub_runner([]))
