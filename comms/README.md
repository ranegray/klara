# Comms: building KLARA in public

Post drafts live in `posts/` as `YYYY-MM-DD-slug.md`, one file per update,
each containing an X variant and a LinkedIn variant. Draft with the
`/post-update` skill; **Rane reviews, edits, and posts manually — nothing is
ever auto-published.**

## Voice

- First person, builder's log, plain language. Confident about the
  engineering, humble about the science ("we'll see what the data says").
- Concrete beats abstract: a number, a screenshot, a failure story, a design
  decision and why. "Frozen the primitive contract so sim and hardware are
  swappable backends" beats "made great progress this week."
- No hype words (revolutionary, game-changing), no thread-bro formatting, no
  engagement bait. It's a research log people happen to enjoy reading.
- X: one tight post by default (a short thread only when there's a real
  sequence to tell). LinkedIn: 120–220 words, first line carries the hook,
  written for engineers and robotics folks, not recruiters.

## What we share vs. hold

**Share freely (build-in-public lane):** architecture and tooling decisions,
the repo, sim scenes, Foxglove dashboards, hardware bring-up, bugs and
war stories, the *question* the thesis asks, papers we're reading.

**Hold until defended/published (science lane):** pilot curves and success
rates, quantitative reliability-per-token results, claims of findings, and
anything that would scoop the proposal's novelty positioning (the FAR /
Playful Agentic overlap makes this real). When in doubt, the update is about
*how we're building the instrument*, not *what it measured*.

**Always:** credit upstream (XLeRobot by Vector Wang; CaP-X; robo9's servo
characterization) when their work is in frame. Disclose sim vs. hardware
honestly — never let a sim clip read as a real robot.
