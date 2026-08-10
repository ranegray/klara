"""VLM client abstraction.

The model is a config value, not a dependency: the loop talks to this
protocol, and swapping providers (hosted frontier model now, local model on
the Orin later) is a constructor change. Token usage is returned on every
call because token accounting is a first-class thesis result — a client that
cannot report usage is not a valid backend.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class Usage:
    prompt_tokens: int
    completion_tokens: int


@dataclass(frozen=True)
class Completion:
    text: str
    usage: Usage


class VLMClient(Protocol):
    def complete(self, messages: list[dict[str, Any]]) -> Completion:
        """One model call. messages follows the common chat format; image
        parts are allowed at rungs that use visual feedback."""
        ...
