# Protocol notes

Short, frozen protocol documents the experiments run under. Each is written
once, versioned, and cited by the proposal. Status:

- [ ] `compute-ladder.md` — the ladder rung definitions and the token/latency
      accounting protocol (what counts as a turn, what counts as a token,
      where usage is measured). Blocks the pilot sweep.
- [ ] `reset-contract.md` — the pinned start state for cube pick-and-place,
      per-seed placement, and what a valid reset means on sim vs. hardware.
      Blocks the pilot sweep.
- [ ] `stressor-model.md` — the injected unreliability model, its parameters,
      and their provenance (robo9 STS3215 numbers and/or our own bench
      measurements). The committee-facing answer to "you simulated away your
      premise."
