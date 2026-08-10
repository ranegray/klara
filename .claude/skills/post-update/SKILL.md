---
name: post-update
description: Draft X + LinkedIn progress posts about KLARA development. Use when the user asks to draft an update, announce a milestone, or "make a post" about recent work.
---

# Draft a KLARA progress update

Produce one draft file containing an X post and a LinkedIn post about recent
project progress. You draft; Rane posts. **Never publish, schedule, or post
anything yourself — that includes via browser tools.** The deliverable is
always a reviewed file.

## Gather material

1. Find the last draft in `comms/posts/` (dated filenames). New material is
   what happened since then.
2. `git log` since that date — commits, merged PRs, what actually landed.
3. If relevant, skim `~/notes/thesis/handoff.md` for context on why the work
   mattered (but see the guardrails: research direction context is fine,
   results are not).
4. Ask Rane for a screenshot/clip only if the update obviously needs one
   (sim scene, Foxglove dashboard, hardware photo); otherwise note a
   suggested visual in the draft.

## Write

Read `comms/README.md` first — it defines voice and the share/hold line.
Non-negotiables from it: no unpublished results or curves, no hype, credit
upstream work, label sim as sim.

Structure the file as:

```markdown
# <slug> — <date>

Suggested visual: <what to attach, or "none">

## X

<the post; ≤280 chars. Thread only if there's a real sequence — mark
tweets 1/, 2/, ...>

## LinkedIn

<120–220 words, hook in the first line>

## Notes for Rane

<1-3 bullets: anything to verify before posting, why this angle, what was
deliberately left out>
```

Save as `comms/posts/YYYY-MM-DD-<slug>.md`. Offer one alternative angle in
the Notes section if the material supports two genuinely different posts.

## Tone calibration (examples)

Good X post shape: "Froze KLARA's primitive contract today: the agent talks
to one typed API, and Isaac Sim vs. the real robot are swappable backends
behind it. Same trick that decouples me from my teammate decouples sim from
hardware. Repo: <link>"

Bad: "🚀 HUGE progress on my thesis project this week! So excited to share
what we've been building 🧵👇"
