"""
psyki.escalation — the termination condition for a loop with no human in it.

Emissary -> Wall -> PSY -> KI -> AgentAgent -> execution -> Emissary is a
closed cycle. Without this module, a plan that keeps not-quite-succeeding
spins forever.

  Tier 1  contract fails gates          AgentAgent retries within budget
  Tier 2  tier-1 budget exhausted       PSY replans the objective
  Tier 3  replan budget exceeded        Emissary returns to the USER

Tier 3 has no budget. It is the floor. Budgets live in ProcOps, not here, so
the system cannot widen its own leash.

Ambiguous debrief also lands at tier 3: there is no user to interrogate on the
return path, so the Emissary surfaces rather than guesses. Unclear outcomes
reaching a human is a feature, not a failure.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .types import Verdict


class Tier(str, Enum):
    RETRY = "RETRY"          # 1 — AgentAgent
    REPLAN = "REPLAN"        # 2 — PSY
    SURFACE = "SURFACE"      # 3 — Emissary -> user
    DONE = "DONE"


@dataclass(frozen=True)
class Budgets:
    """Mirror of ProcOps['escalation']."""
    tier1_retry: int = 2
    tier2_replan: int = 3


@dataclass(frozen=True)
class Ledger:
    """Per-objective counters. PSY carries this across replans."""
    objective_id: str
    retries_used: int = 0
    replans_used: int = 0

    def with_retry(self) -> "Ledger":
        return Ledger(self.objective_id,
                      self.retries_used + 1, self.replans_used)

    def with_replan(self) -> "Ledger":
        return Ledger(self.objective_id, 0, self.replans_used + 1)


@dataclass(frozen=True)
class Escalation:
    tier: Tier
    ledger: Ledger
    note: str = ""


def escalate(
    verdict: Verdict,
    ledger: Ledger,
    budgets: Budgets = Budgets(),
    ambiguous: bool = False,
) -> Escalation:
    """Pure. The whole halting argument lives in this function."""

    if ambiguous:
        return Escalation(Tier.SURFACE, ledger, "ambiguous debrief")

    if verdict is Verdict.FULFILLED:
        return Escalation(Tier.DONE, ledger)

    # the user's own intent was wrong, or the charter forbade it —
    # no amount of retrying fixes either
    if verdict in (Verdict.REJECTED, Verdict.ESCALATE):
        return Escalation(Tier.SURFACE, ledger, verdict.value)

    # PARTIAL under a satisfied completion predicate never reaches here;
    # the contract closes as FULFILLED. Reaching here means it genuinely fell
    # short of its own predicate.
    if verdict in (
        Verdict.FAILED_GATE, Verdict.FAILED_TOOL,
        Verdict.STALLED, Verdict.PARTIAL,
    ):
        if ledger.retries_used < budgets.tier1_retry:
            return Escalation(Tier.RETRY, ledger.with_retry())
        if ledger.replans_used < budgets.tier2_replan:
            return Escalation(Tier.REPLAN, ledger.with_replan(),
                              "retry budget exhausted")
        return Escalation(Tier.SURFACE, ledger, "replan budget exhausted")

    if verdict is Verdict.FAILED_BUDGET:
        if ledger.replans_used < budgets.tier2_replan:
            return Escalation(Tier.REPLAN, ledger.with_replan())
        return Escalation(Tier.SURFACE, ledger, "replan budget exhausted")

    return Escalation(Tier.SURFACE, ledger, "unhandled verdict")
