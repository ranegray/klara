# klara-announcement — 2026-08-10

Suggested visual: screenshot of the repo README, or the RViz view of the
XLeRobot URDF (labeled as visualization, not sim).

## X

Naming things is hard, so I stole from Ishiguro. Meet KLARA (Kinematic
Limits, Agentic Recovery Architecture): my senior thesis platform asking
whether an LLM coding agent can buy back the reliability that $30 servos
give away — and what each recovered failure costs in tokens.
github.com/ranegray/klara

## LinkedIn

My senior thesis now has a name: KLARA — Kinematic Limits, Agentic Recovery
Architecture (yes, after Ishiguro's Klara, an older-generation robot who
compensates for cheaper hardware with careful observation — which is
basically the research question).

The question: cheap servos (~0.85° of backlash, ±1° repeatability) take task
reliability away from low-cost robots. Can a coding agent — retry, execution
feedback, visual differencing — buy that reliability back at test time? And
at what token cost? Somewhere there's a crossover where paying tokens to
paper over bad hardware becomes false economy. Finding that frontier is the
thesis.

This week the repo grew its skeleton: a frozen primitive contract so Isaac
Sim and the real XLeRobot are swappable backends behind one API, a servo
unreliability model injected at the joint-command boundary (so the sim can't
simulate away the premise), and an episode-record schema where every trial
logs its token spend. First sim experiments start with the semester.

Built on the open-source XLeRobot platform. More as it happens — this will
be a build-in-public project.

## Notes for Rane

- Verify you're comfortable naming the token-cost framing publicly before
  the proposal defense — it's the thesis question, and this post states it.
  Held back: anything about rungs, pilot design, or expected results.
- Alternative angle if you'd rather not announce the thesis question yet:
  pure engineering post about the contract/backend-swap architecture, saving
  the science framing for a later post.
- The robo9 numbers are cited as characteristic of the servo class, not as
  your measurements — that's honest, but say "measured by robo9" if asked.
