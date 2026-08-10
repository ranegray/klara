"""The test-time compute ladder.

The sweep axis of the thesis: each rung enables strictly more machinery than
the one below. Rung numbers are recorded in every EpisodeRecord and must
never be renumbered — evidence already written refers to them.

The August sim pilot covers rungs 1–3. Rungs 4–5 belong to the post-defense
campaign.
"""

from __future__ import annotations

from enum import IntEnum


class Rung(IntEnum):
    SINGLE_TURN = 1  # one-shot code generation, no recovery (the control)
    MULTI_TURN_FEEDBACK = 2  # retry loop with structured execution feedback
    VISUAL_DIFF = 3  # + before/after visual differencing (VDM-equivalent)
    SKILL_LIBRARY = 4  # + seeded skill library
    ENSEMBLE = 5  # + ensembled reasoning

    @property
    def machinery(self) -> list[str]:
        """Mechanism tags for EpisodeRecord.machinery."""
        names = {
            Rung.SINGLE_TURN: [],
            Rung.MULTI_TURN_FEEDBACK: ["multi_turn"],
            Rung.VISUAL_DIFF: ["multi_turn", "vdm"],
            Rung.SKILL_LIBRARY: ["multi_turn", "vdm", "skill_library"],
            Rung.ENSEMBLE: ["multi_turn", "vdm", "skill_library", "ensemble"],
        }
        return names[self]
