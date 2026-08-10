"""Reliability-per-token frontier from a run-record JSONL.

Reads EpisodeRecords, groups by rung, and plots task success rate against
tokens-per-successful-episode — the core thesis figure. Also reports
tokens-per-recovered-failure (marginal spend after first detected failure)
and wall-clock per episode, the binding-cost axes.
"""

from __future__ import annotations

import sys

from klara_core.records import read_records


def main(jsonl_path: str) -> None:
    records = read_records(jsonl_path)
    by_rung: dict[int, list] = {}
    for r in records:
        by_rung.setdefault(r.rung, []).append(r)
    for rung in sorted(by_rung):
        eps = by_rung[rung]
        successes = [r for r in eps if r.success]
        rate = len(successes) / len(eps)
        tokens_per_success = (
            sum(r.total_tokens for r in eps) / len(successes) if successes else float("inf")
        )
        print(
            f"rung {rung}: n={len(eps)} success={rate:.0%} "
            f"tokens/success={tokens_per_success:,.0f}"
        )
    # TODO(pilot): matplotlib frontier plot once real records exist.


if __name__ == "__main__":
    main(sys.argv[1])
