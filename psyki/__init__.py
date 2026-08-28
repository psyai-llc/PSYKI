"""PSYKI — a self-governing, meta-agentic MCP server.

Three reasoning components (Emissary, PSY, AgentAgent); everything else here is
deterministic code. See docs/PSYKI_CORE.md for the architecture and the
invariants this package is required to hold.

Nothing in this module does work. Business logic lives in the submodules so that
importing the package cannot have side effects.
"""

from __future__ import annotations

__all__ = [
    "core",
    "escalation",
    "ki",
    "log",
    "procops",
    "retinue",
    "tastetester",
    "types",
    "wall",
]
