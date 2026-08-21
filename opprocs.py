"""
psyki.opprocs — the charter.

Read-only, hash-verified on every read. (I5) The server cannot author its own
charter; a Wall directive contradicting OpProcs is VOIDED, not negotiated.

Trust hierarchy: OpProcs > Wall > Log.

This is also what makes the closed loop safe. Emissary -> Wall -> PSY -> KI ->
AgentAgent -> execution -> Emissary has no human in it. Cadence, budgets, and
escalation limits live here rather than in PSY's discretion, so PSY cannot
widen its own leash.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class CharterViolation(Exception):
    """Raised when the charter file no longer matches its pin."""


@dataclass(frozen=True)
class OpProcs:
    path: Path
    pinned_hash: str
    _body: dict[str, Any]

    # -- load ------------------------------------------------------------

    @staticmethod
    def hash_file(path: Path) -> str:
        return hashlib.blake2b(
            path.read_bytes(), digest_size=32).hexdigest()

    @classmethod
    def load(cls, path: str | Path, pinned_hash: str) -> "OpProcs":
        p = Path(path)
        actual = cls.hash_file(p)
        if actual != pinned_hash:
            raise CharterViolation(
                f"charter hash mismatch: pinned={pinned_hash} actual={actual}")
        return cls(p, pinned_hash, json.loads(p.read_text()))

    # -- read ------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        """Re-verify on every read. Cheap, and the failure mode it prevents
        is a charter swapped underneath a running server."""
        if self.hash_file(self.path) != self.pinned_hash:
            raise CharterViolation("charter mutated at runtime")
        return self._body.get(key, default)

    # -- adjudicate ------------------------------------------------------

    def voids(self, directive_verb: str, directive_scope: str) -> bool:
        """True if the charter forbids this directive outright.

        Voided, not negotiated: the caller drops the directive and reports
        REJECTED. There is no downgrade path.
        """
        forbidden = self.get("forbidden", {})
        scopes = forbidden.get(directive_verb, [])
        return directive_scope in scopes or "*" in scopes


DEFAULT_CHARTER: dict[str, Any] = {
    "version": 1,
    "ki_policy": {
        "max_plan_age_revs": 32,
        "max_queue_depth": 8,
        "wall_revision_invalidates": True,
    },
    "escalation": {
        "tier1_retry_budget": 2,      # AgentAgent retries the contract
        "tier2_replan_budget": 3,     # PSY replans the objective
        # tier 3 = Emissary returns to the user. No budget; it is the floor.
    },
    "gates": {
        "eval_threshold": 0.90,
        "safety_threshold": 1.0,      # never relaxed
    },
    "log": {"session_depth": 2},
    "forbidden": {
        "DEPLOY": ["SYSTEM"],
        "REMOVE": ["SYSTEM", "REPO"],
    },
    "auto_evolution": False,          # §10.4 — deferred, deliberately
}
