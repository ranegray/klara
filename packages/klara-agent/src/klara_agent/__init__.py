"""klara-agent: the compensating machinery under test.

Implements the compute ladder — each rung adds test-time machinery on top of
the last — against the klara-core contract. Backend-agnostic by construction:
nothing in this package may import Isaac, ROS, or any robot specifics.
"""

from klara_agent.ladder import Rung

__all__ = ["Rung"]
