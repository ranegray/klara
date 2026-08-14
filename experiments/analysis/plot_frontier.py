"""Reliability-per-token frontier from a run-record JSONL.

Usage:
    python experiments/analysis/plot_frontier.py data/runs/pilot_cube.jsonl
    python experiments/analysis/plot_frontier.py data/runs/pilot_cube.jsonl --out-dir figures/

Reads EpisodeRecords, groups by rung, and produces the pilot's outputs:
  <stem>_frontier.png  — success rate (Wilson 95% CI) vs tokens-per-successful-
                         episode, one point per rung: the core thesis figure
  <stem>_summary.md    — the per-rung summary table, ready to paste into the
                         proposal
plus the same table and the provisional tokens-per-recovered-failure numbers
on stdout. Read-only: the run file is never modified.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # file output only; never needs a display

import frontier  # noqa: E402  (sibling module; script dir is on sys.path)
import matplotlib.pyplot as plt  # noqa: E402  (backend must be set before pyplot)
from klara_core.records import read_records  # noqa: E402

# Single-series figure: one accent hue for the marks, neutral ink for text,
# recessive gray for the grid. No legend needed — the axes name the series.
ACCENT = "#2a6f97"
INK = "#333333"
GRID = "#d9d9d9"


def plot_frontier(summaries: list[frontier.RungSummary], out_path: Path) -> None:
    """Write the frontier figure: reliability vs tokens-per-successful-episode.

    Rungs with zero successes have no defined tokens-per-success and are
    left off the figure (they still appear in the summary table).
    """
    plottable = [s for s in summaries if not math.isinf(s.tokens_per_success)]
    skipped = [s.rung for s in summaries if math.isinf(s.tokens_per_success)]
    if skipped:
        print(f"frontier plot: skipping rungs with zero successes: {skipped}")

    fig, ax = plt.subplots(figsize=(6.0, 4.0))
    if plottable:
        x = [s.tokens_per_success for s in plottable]
        y = [s.success_rate for s in plottable]
        err_low = [s.success_rate - s.ci_low for s in plottable]
        err_high = [s.ci_high - s.success_rate for s in plottable]
        ax.errorbar(
            x,
            y,
            yerr=[err_low, err_high],
            fmt="o-",
            color=ACCENT,
            linewidth=2,
            markersize=8,
            capsize=4,
            markeredgecolor="white",
            markeredgewidth=1,
        )
        for s in plottable:
            ax.annotate(
                f"rung {s.rung}",
                (s.tokens_per_success, s.success_rate),
                textcoords="offset points",
                xytext=(8, 8),
                fontsize=9,
                color=INK,
            )

    ax.set_xlabel("tokens per successful episode", color=INK)
    ax.set_ylabel("task success rate (Wilson 95% CI)", color=INK)
    ax.set_title("Reliability-per-token frontier", color=INK)
    ax.set_ylim(0.0, 1.05)
    ax.yaxis.set_major_formatter(lambda value, _pos: f"{value:.0%}")
    ax.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(colors=INK)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("jsonl_path", help="run-record JSONL written by run_sweep.py")
    parser.add_argument(
        "--out-dir",
        default=None,
        help="directory for the figure and table (default: alongside the JSONL)",
    )
    args = parser.parse_args(argv)

    jsonl_path = Path(args.jsonl_path)
    out_dir = Path(args.out_dir) if args.out_dir else jsonl_path.parent

    records = read_records(jsonl_path)
    summaries = frontier.summarize_rungs(records)
    by_rung = frontier.group_by_rung(records)

    table = frontier.summary_table_markdown(summaries)
    print(table)
    for rung in sorted(by_rung):
        cost = frontier.provisional_tokens_per_recovered_failure(by_rung[rung])
        print(f"rung {rung}: provisional tokens/recovered-failure = {cost:,.0f} (see KLA-1)")

    out_dir.mkdir(parents=True, exist_ok=True)
    table_path = out_dir / f"{jsonl_path.stem}_summary.md"
    table_path.write_text(table, encoding="utf-8")
    figure_path = out_dir / f"{jsonl_path.stem}_frontier.png"
    plot_frontier(summaries, figure_path)
    print(f"wrote {table_path}")
    print(f"wrote {figure_path}")


if __name__ == "__main__":
    main()
