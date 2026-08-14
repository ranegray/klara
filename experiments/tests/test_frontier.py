"""Analysis tests on synthetic records with hand-checkable answers.

The central fixture mirrors the pilot design: rung 1 and rung 2 share the
same 20 seeds, and rung 2 recovers exactly half of rung 1's failures, so
every summary number below can be computed by hand.
"""

import math

import frontier
import plot_frontier
import pytest
from klara_core.records import EpisodeRecord, FailureCategory, TurnRecord
from klara_core.stressor import StressorParams

TOKENS_FIRST_TURN = 100
TOKENS_RETRY_TURN = 50


def make_episode(
    rung: int,
    seed: int,
    success: bool,
    n_turns: int = 1,
    failure_category: str | None = None,
) -> EpisodeRecord:
    turns = [
        TurnRecord(
            index=i,
            prompt_tokens=TOKENS_FIRST_TURN if i == 0 else TOKENS_RETRY_TURN,
            completion_tokens=0,
            wall_clock_s=2.0,
        )
        for i in range(n_turns)
    ]
    return EpisodeRecord(
        episode_id=f"fixture-r{rung}-s{seed}",
        task="cube_pick_place",
        backend="scripted",
        rung=rung,
        model="stub",
        machinery=[],
        seed=seed,
        stressor=StressorParams().to_dict(),
        success=success,
        failure_category=failure_category,
        turns=turns,
        wall_clock_s=10.0,
    )


def rung1_and_rung2_records() -> list[EpisodeRecord]:
    """20 seeds. Rung 1: seeds 0-9 succeed, 10-19 fail (single turn each).
    Rung 2: the same 10 successes, plus seeds 10-14 recovered on a second
    turn — exactly half of rung 1's failures — and seeds 15-19 still failing
    after a retry."""
    records: list[EpisodeRecord] = []
    for seed in range(10):
        records.append(make_episode(1, seed, success=True))
    for seed in range(10, 20):
        records.append(
            make_episode(
                1, seed, success=False, failure_category=FailureCategory.PERCEPTION.value
            )
        )
    for seed in range(10):
        records.append(make_episode(2, seed, success=True))
    for seed in range(10, 15):
        records.append(make_episode(2, seed, success=True, n_turns=2))
    for seed in range(15, 20):
        records.append(
            make_episode(
                2,
                seed,
                success=False,
                n_turns=2,
                failure_category=FailureCategory.AGENT_REASONING.value,
            )
        )
    return records


def test_wilson_interval_matches_published_value():
    # Wilson 95% CI for 8/10 is (0.4901, 0.9433) — a standard worked example.
    low, high = frontier.wilson_interval(8, 10)
    assert low == pytest.approx(0.4901, abs=1e-3)
    assert high == pytest.approx(0.9433, abs=1e-3)


def test_wilson_interval_stays_inside_unit_interval():
    low, high = frontier.wilson_interval(0, 20)
    assert low == 0.0
    assert 0.0 < high < 0.2
    low, high = frontier.wilson_interval(20, 20)
    assert 0.8 < low < 1.0
    assert high == 1.0


def test_wilson_interval_rejects_bad_input():
    with pytest.raises(ValueError):
        frontier.wilson_interval(1, 0)
    with pytest.raises(ValueError):
        frontier.wilson_interval(5, 4)


def test_rung_summaries_on_the_half_recovery_fixture():
    summaries = frontier.summarize_rungs(rung1_and_rung2_records())
    assert [s.rung for s in summaries] == [1, 2]
    rung1, rung2 = summaries

    assert rung1.n_episodes == 20
    assert rung1.n_successes == 10
    assert rung1.success_rate == pytest.approx(0.5)
    # 20 single-turn episodes at 100 tokens: 2000 total, 10 successes.
    assert rung1.mean_tokens == pytest.approx(100.0)
    assert rung1.tokens_per_success == pytest.approx(200.0)
    assert rung1.mean_turns == pytest.approx(1.0)
    assert rung1.failure_categories == {"PERCEPTION": 10}

    # Rung 2 recovered exactly half of rung 1's failures: 10 + 5 successes.
    assert rung2.n_successes == 15
    assert rung2.success_rate == pytest.approx(0.75)
    # 10x100 + 10x150 = 2500 tokens over 15 successes.
    assert rung2.mean_tokens == pytest.approx(125.0)
    assert rung2.tokens_per_success == pytest.approx(2500.0 / 15.0)
    assert rung2.failure_categories == {"AGENT_REASONING": 5}

    # The CIs must overlap the true rates and be genuinely wide at n=20.
    assert rung1.ci_low < 0.5 < rung1.ci_high
    assert rung2.ci_low < 0.75 < rung2.ci_high
    assert rung1.ci_high - rung1.ci_low > 0.3


def test_provisional_tokens_per_recovered_failure():
    by_rung = frontier.group_by_rung(rung1_and_rung2_records())
    # Rung 1 is single-turn: nothing recovered, so the metric is undefined.
    assert math.isnan(frontier.provisional_tokens_per_recovered_failure(by_rung[1]))
    # Rung 2: five recovered failures, each spending one 50-token retry turn.
    cost = frontier.provisional_tokens_per_recovered_failure(by_rung[2])
    assert cost == pytest.approx(TOKENS_RETRY_TURN)


def test_summary_table_markdown_contents():
    summaries = frontier.summarize_rungs(rung1_and_rung2_records())
    table = frontier.summary_table_markdown(summaries)
    lines = table.splitlines()
    assert lines[0].startswith("| Rung |")
    assert len(lines) == 2 + len(summaries)  # header + divider + one row per rung
    assert "| 1 | 20 | 10 | 50% (30%-70%) " in table
    assert "PERCEPTION: 10" in table
    assert "AGENT_REASONING: 5" in table


def test_summary_table_handles_a_rung_with_zero_successes():
    episodes = [make_episode(1, seed, success=False) for seed in range(5)]
    summary = frontier.summarize_rung(1, episodes)
    assert math.isinf(summary.tokens_per_success)
    table = frontier.summary_table_markdown([summary])
    assert "n/a (0 successes)" in table


def test_frontier_plot_writes_a_png(tmp_path):
    summaries = frontier.summarize_rungs(rung1_and_rung2_records())
    out_path = tmp_path / "frontier.png"
    plot_frontier.plot_frontier(summaries, out_path)
    assert out_path.exists()
    assert out_path.stat().st_size > 0


def test_frontier_plot_skips_zero_success_rungs(tmp_path):
    episodes = [make_episode(1, seed, success=False) for seed in range(5)]
    summaries = [frontier.summarize_rung(1, episodes)]
    out_path = tmp_path / "frontier.png"
    plot_frontier.plot_frontier(summaries, out_path)  # must not raise on inf
    assert out_path.exists()


def test_plot_frontier_main_end_to_end(tmp_path):
    from klara_core.records import append_record

    jsonl_path = tmp_path / "pilot.jsonl"
    for record in rung1_and_rung2_records():
        append_record(jsonl_path, record)

    plot_frontier.main([str(jsonl_path), "--out-dir", str(tmp_path / "out")])

    assert (tmp_path / "out" / "pilot_summary.md").exists()
    assert (tmp_path / "out" / "pilot_frontier.png").exists()
    # Analysis never mutates the run file.
    assert len(jsonl_path.read_text(encoding="utf-8").splitlines()) == 40
