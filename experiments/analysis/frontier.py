"""Per-rung reliability and token-cost summaries from EpisodeRecords.

Pure computation, no plotting — plot_frontier.py turns these numbers into
the figure and the markdown table. All record access goes through
klara_core.records readers; run files are read-only evidence and are never
touched by analysis.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from klara_core.records import EpisodeRecord


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score confidence interval for a binomial proportion.

    z=1.96 gives the 95% interval. At n=20 per rung the normal approximation
    is untrustworthy near 0% and 100%; Wilson stays inside [0, 1] and keeps
    sane coverage at small n, which is why the proposal figures use it.
    """
    if n <= 0:
        raise ValueError("wilson_interval needs n > 0")
    if not 0 <= successes <= n:
        raise ValueError(f"successes must be in [0, {n}], got {successes}")
    p = successes / n
    z2 = z * z
    denominator = 1.0 + z2 / n
    center = (p + z2 / (2.0 * n)) / denominator
    half_width = (z / denominator) * math.sqrt(p * (1.0 - p) / n + z2 / (4.0 * n * n))
    return max(0.0, center - half_width), min(1.0, center + half_width)


@dataclass(frozen=True)
class RungSummary:
    """One row of the per-rung summary table."""

    rung: int
    n_episodes: int
    n_successes: int
    success_rate: float
    ci_low: float  # Wilson 95% CI on the success rate
    ci_high: float
    mean_turns: float
    mean_tokens: float  # mean total tokens per episode (successes and failures)
    tokens_per_success: float  # total rung tokens / successes; inf when none succeed
    mean_wall_clock_s: float
    failure_categories: dict[str, int]  # FailureCategory value -> count


def group_by_rung(records: list[EpisodeRecord]) -> dict[int, list[EpisodeRecord]]:
    by_rung: dict[int, list[EpisodeRecord]] = {}
    for record in records:
        by_rung.setdefault(record.rung, []).append(record)
    return by_rung


def summarize_rung(rung: int, episodes: list[EpisodeRecord]) -> RungSummary:
    if not episodes:
        raise ValueError(f"no episodes for rung {rung}")
    n = len(episodes)
    n_successes = sum(1 for e in episodes if e.success)
    ci_low, ci_high = wilson_interval(n_successes, n)
    total_tokens = sum(e.total_tokens for e in episodes)
    failure_categories: dict[str, int] = {}
    for e in episodes:
        if not e.success and e.failure_category:
            count = failure_categories.get(e.failure_category, 0)
            failure_categories[e.failure_category] = count + 1
    return RungSummary(
        rung=rung,
        n_episodes=n,
        n_successes=n_successes,
        success_rate=n_successes / n,
        ci_low=ci_low,
        ci_high=ci_high,
        mean_turns=sum(len(e.turns) for e in episodes) / n,
        mean_tokens=total_tokens / n,
        tokens_per_success=total_tokens / n_successes if n_successes else math.inf,
        mean_wall_clock_s=sum(e.wall_clock_s for e in episodes) / n,
        failure_categories=failure_categories,
    )


def summarize_rungs(records: list[EpisodeRecord]) -> list[RungSummary]:
    """One RungSummary per rung present in the records, in rung order."""
    by_rung = group_by_rung(records)
    return [summarize_rung(rung, by_rung[rung]) for rung in sorted(by_rung)]


def provisional_tokens_per_recovered_failure(episodes: list[EpisodeRecord]) -> float:
    """PROVISIONAL marginal token cost of recovering from a failure, one rung.

    The real definition — what counts as a detected failure, which turns are
    recovery spend, how multiple failures inside one episode are attributed —
    belongs to docs/protocols/compute-ladder.md (KLA-1), which is not written
    yet. Until that note lands, this function uses the simplest stand-in:
    a successful episode with more than one turn counts as exactly one
    recovered failure, and every token after the first turn is charged to
    the recovery. Returns NaN when no episode qualifies.

    Do not cite this number in defense-facing prose before KLA-1 pins the
    definition; rename/replace this function when it does.
    """
    recovered = [e for e in episodes if e.success and len(e.turns) > 1]
    if not recovered:
        return math.nan
    marginal_tokens = 0
    for e in recovered:
        for turn in e.turns[1:]:
            marginal_tokens += turn.prompt_tokens + turn.completion_tokens
    return marginal_tokens / len(recovered)


def summary_table_markdown(summaries: list[RungSummary]) -> str:
    """The per-rung summary table, as markdown — pastes into the proposal."""
    lines = [
        "| Rung | n | Successes | Success rate (Wilson 95% CI) | Mean turns "
        "| Mean tokens | Tokens/success | Mean wall-clock (s) | Failure categories |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for s in summaries:
        if math.isinf(s.tokens_per_success):
            tokens_per_success = "n/a (0 successes)"
        else:
            tokens_per_success = f"{s.tokens_per_success:,.0f}"
        if s.failure_categories:
            categories = ", ".join(
                f"{name}: {count}" for name, count in sorted(s.failure_categories.items())
            )
        else:
            categories = "-"
        lines.append(
            f"| {s.rung} | {s.n_episodes} | {s.n_successes} "
            f"| {s.success_rate:.0%} ({s.ci_low:.0%}-{s.ci_high:.0%}) "
            f"| {s.mean_turns:.1f} | {s.mean_tokens:,.0f} | {tokens_per_success} "
            f"| {s.mean_wall_clock_s:.1f} | {categories} |"
        )
    return "\n".join(lines) + "\n"
