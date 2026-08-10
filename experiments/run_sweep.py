"""Run a reliability-versus-token sweep from a config file.

Usage (inside Isaac Sim's Python for the isaac backend):
    python experiments/run_sweep.py experiments/configs/pilot_cube.yaml

For each rung x episode: reset env with the episode seed, run the agent loop,
append one EpisodeRecord to the output JSONL. Idempotent restart: skips
(rung, seed) pairs already present in the output file, so a crashed sweep
resumes where it left off.
"""

from __future__ import annotations

import sys


def main(config_path: str) -> None:
    raise NotImplementedError("pilot work: wire IsaacBackend + run_episode")


if __name__ == "__main__":
    main(sys.argv[1])
