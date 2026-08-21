"""
psyki.ki — the certifying authority.

KI is CODE, not a model. Its entire value is being trustworthy; a model here
would put hallucination risk on the one component that must not have it.

I2  context is exactly (State, Plan, Event)
I3  pure total function — no RNG, no wall-clock, no I/O, no model call
I9  certificates are issued and revoked by KI alone
I12 determinism is over the snapshot

KI never sees the Wall, the Log, history, the future, or prose.

Why present-only: PSY plans against a snapshot, and by task 40 the world has
moved. KI is the freshness check on a stale plan. A gate that cannot say no is
a pass-through, so refusal reasons are enumerated and exhaustive.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .types import Certificate, Event, Initiation, StateSnapshot, Task


class Decision(str, Enum):
    ADMIT = "ADMIT"
    REFUSE = "REFUSE"
    REVOKE = "REVOKE"
    HOLD = "HOLD"


class Reason(str, Enum):
    OK = "OK"
    CHARTER_DRIFT = "CHARTER_DRIFT"          # opprocs hash changed under plan
    WALL_REVISED = "WALL_REVISED"            # intent moved since planning
    TOOLSET_HELD = "TOOLSET_HELD"            # another contract owns the tools
    NO_AGENT = "NO_AGENT"                    # pool exhausted
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    CEILING_EXCEEDED = "CEILING_EXCEEDED"
    QUEUE_SATURATED = "QUEUE_SATURATED"
    STALE_PLAN = "STALE_PLAN"                # planned_at_rev too far behind
    UNKNOWN_CERTIFICATE = "UNKNOWN_CERTIFICATE"
    PRECONDITION_LOST = "PRECONDITION_LOST"  # revoke: state drifted mid-run


@dataclass(frozen=True)
class KiRuling:
    decision: Decision
    reason: Reason
    subject: str                       # task_id or certificate_id
    at_rev: int
    certificate: Optional[Certificate] = None


# ----------------------------------------------------------------- policy

@dataclass(frozen=True)
class KiPolicy:
    """Lives in OpProcs, not in KI's discretion. (I5)"""
    max_plan_age_revs: int = 32
    max_queue_depth: int = 8
    wall_revision_invalidates: bool = True


# -------------------------------------------------------------- certificate

def mint_certificate_id(
    task_id: str, state_rev: int, opprocs_hash: str
) -> str:
    """Deterministic. No RNG anywhere in KI. (I3)"""
    h = hashlib.blake2b(digest_size=16)
    h.update(task_id.encode("utf-8"))
    h.update(b"\x00")
    h.update(str(state_rev).encode("ascii"))
    h.update(b"\x00")
    h.update(opprocs_hash.encode("utf-8"))
    return h.hexdigest()


# ------------------------------------------------------------------ admit

def admit(
    snapshot: StateSnapshot,
    task: Task,
    policy: KiPolicy = KiPolicy(),
    plan_opprocs_hash: str = "",
    plan_wall_rev: int = -1,
) -> KiRuling:
    """Should this task be admitted right now?

    Pure over (snapshot, task, policy). Same inputs, same ruling, always.
    """
    rev = snapshot.state_rev

    def no(reason: Reason) -> KiRuling:
        return KiRuling(Decision.REFUSE, reason, task.task_id, rev)

    # charter first — a plan authored under a different charter is void (I5)
    if plan_opprocs_hash and plan_opprocs_hash != snapshot.opprocs_hash:
        return no(Reason.CHARTER_DRIFT)

    # intent freshness: the user changed their mind while PSY was planning
    if (
        policy.wall_revision_invalidates
        and plan_wall_rev >= 0
        and plan_wall_rev != snapshot.wall_rev
    ):
        return no(Reason.WALL_REVISED)

    if rev - task.planned_at_rev > policy.max_plan_age_revs:
        return no(Reason.STALE_PLAN)

    if task.toolset_signature in snapshot.toolset_locks:
        return KiRuling(Decision.HOLD, Reason.TOOLSET_HELD, task.task_id, rev)

    if not snapshot.agent_pool_available:
        return KiRuling(Decision.HOLD, Reason.NO_AGENT, task.task_id, rev)

    if (
        task.requires_model_class != "ANY"
        and snapshot.model_residency != task.requires_model_class
    ):
        return KiRuling(
            Decision.HOLD, Reason.MODEL_UNAVAILABLE, task.task_id, rev)

    if snapshot.contract_queue_depth >= policy.max_queue_depth:
        return KiRuling(
            Decision.HOLD, Reason.QUEUE_SATURATED, task.task_id, rev)

    if _over_ceiling(snapshot):
        return KiRuling(
            Decision.HOLD, Reason.CEILING_EXCEEDED, task.task_id, rev)

    cert = Certificate(
        certificate_id=mint_certificate_id(
            task.task_id, rev, snapshot.opprocs_hash),
        task_id=task.task_id,
        issued_at_rev=rev,
        opprocs_hash=snapshot.opprocs_hash,
    )
    return KiRuling(Decision.ADMIT, Reason.OK, task.task_id, rev, cert)


def certify(ruling: KiRuling, task: Task) -> Initiation:
    """ADMIT ruling + task -> Initiation. AgentAgent's entry point."""
    if ruling.decision is not Decision.ADMIT or ruling.certificate is None:
        raise ValueError(f"cannot certify a {ruling.decision} ruling")
    return Initiation(task=task, certificate=ruling.certificate)


# ----------------------------------------------------------------- revoke

def tick(
    snapshot: StateSnapshot,
    certificate: Certificate,
    event: Optional[Event] = None,
    policy: KiPolicy = KiPolicy(),
) -> KiRuling:
    """Event-clocked re-check of a LIVE certificate.

    KI does not only gate admission. Tasks can run long, so KI ticks during
    execution and revokes when present state drifts out from under a running
    contract. This is where 'operational rhythm' stops being a metaphor.
    """
    rev = snapshot.state_rev
    cid = certificate.certificate_id

    if cid not in snapshot.certificates_outstanding:
        return KiRuling(Decision.REVOKE, Reason.UNKNOWN_CERTIFICATE, cid, rev)

    if certificate.opprocs_hash != snapshot.opprocs_hash:
        return KiRuling(Decision.REVOKE, Reason.CHARTER_DRIFT, cid, rev)

    if _over_ceiling(snapshot):
        return KiRuling(Decision.REVOKE, Reason.CEILING_EXCEEDED, cid, rev)

    return KiRuling(Decision.ADMIT, Reason.OK, cid, rev, certificate)


def revoke(certificate: Certificate, snapshot: StateSnapshot,
           reason: Reason = Reason.OK) -> KiRuling:
    """Contract fulfilled or aborted. The certifying authority retires the
    credential it issued. (I9) Caller then returns model to pool and agent
    code to the retinue."""
    return KiRuling(
        Decision.REVOKE, reason,
        certificate.certificate_id, snapshot.state_rev,
    )


# ---------------------------------------------------------------- helpers

def _over_ceiling(s: StateSnapshot) -> bool:
    c, u = s.ceilings, s.usage
    return any((
        c.gpu and u.gpu > c.gpu,
        c.memory and u.memory > c.memory,
        c.disk and u.disk > c.disk,
        c.context and u.context > c.context,
    ))
