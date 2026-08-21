"""
psyki.types — the enum protocol.

Enums carry the FRAME. Typed fields carry the CONTENT.
No field in this module is ever interpolated as instruction. (I4)

Everything here is frozen. Determinism is structural, not conventional.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------- 4.1 Intent

class Verb(str, Enum):
    CREATE = "CREATE"
    MODIFY = "MODIFY"
    ANALYZE = "ANALYZE"
    TEST = "TEST"
    RESEARCH = "RESEARCH"
    DEPLOY = "DEPLOY"
    REPAIR = "REPAIR"
    DOCUMENT = "DOCUMENT"
    REMOVE = "REMOVE"
    EVALUATE = "EVALUATE"


class Scope(str, Enum):
    FILE = "FILE"
    MODULE = "MODULE"
    REPO = "REPO"
    SERVICE = "SERVICE"
    DATASET = "DATASET"
    MODEL = "MODEL"
    SYSTEM = "SYSTEM"


class Urgency(str, Enum):
    DEFER = "DEFER"
    NORMAL = "NORMAL"
    PRIORITY = "PRIORITY"
    IMMEDIATE = "IMMEDIATE"


@dataclass(frozen=True)
class Directive:
    """Emissary output. The only thing admitted to the Wall. (I6)

    `targets` and `constraints` are opaque identifiers, not prose. The Emissary
    refuses and re-asks rather than approximating anything it cannot encode.
    """
    directive_id: str
    verb: Verb
    scope: Scope
    urgency: Urgency = Urgency.NORMAL
    targets: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    origin: str = "USER"          # USER | DEBRIEF | RETRIEVAL


# ------------------------------------------------------------ plan artifacts

@dataclass(frozen=True)
class Objective:
    objective_id: str
    directive_id: str             # lineage — orphans rejected (I7)
    ordinal: int
    depends_on: tuple[str, ...] = ()


@dataclass(frozen=True)
class Task:
    """A task is bounded by its toolset. Fan-out is internal. (I8)"""
    task_id: str
    objective_id: str
    toolset_signature: str
    fanout_targets: tuple[str, ...] = ()
    planned_at_rev: int = 0       # State revision PSY planned against
    requires_model_class: str = "ANY"


# ------------------------------------------------------------- gates & verdict

class Gate(str, Enum):
    FORMAT = "FORMAT"
    LINT = "LINT"
    TYPECHECK = "TYPECHECK"
    TEST = "TEST"
    COVERAGE = "COVERAGE"
    SECURITY = "SECURITY"


GATE_CHAIN: tuple[Gate, ...] = (
    Gate.FORMAT, Gate.LINT, Gate.TYPECHECK,
    Gate.TEST, Gate.COVERAGE, Gate.SECURITY,
)


class CompletionKind(str, Enum):
    ALL = "ALL"
    THRESHOLD = "THRESHOLD"
    BEST_EFFORT = "BEST_EFFORT"
    FIRST_SUCCESS = "FIRST_SUCCESS"


@dataclass(frozen=True)
class CompletionPredicate:
    """Set at authoring time, never decided at debrief."""
    kind: CompletionKind
    threshold: int = 0            # meaningful only for THRESHOLD

    def satisfied(self, completed: int, total: int) -> bool:
        if self.kind is CompletionKind.ALL:
            return completed == total
        if self.kind is CompletionKind.THRESHOLD:
            return completed >= self.threshold
        if self.kind is CompletionKind.FIRST_SUCCESS:
            return completed >= 1
        return True               # BEST_EFFORT


class Verdict(str, Enum):
    FULFILLED = "FULFILLED"
    PARTIAL = "PARTIAL"
    FAILED_GATE = "FAILED_GATE"
    FAILED_TOOL = "FAILED_TOOL"
    FAILED_BUDGET = "FAILED_BUDGET"
    STALLED = "STALLED"
    REJECTED = "REJECTED"
    ESCALATE = "ESCALATE"


TERMINAL_VERDICTS = frozenset({
    Verdict.FULFILLED, Verdict.REJECTED, Verdict.ESCALATE,
})


@dataclass(frozen=True)
class VerdictRecord:
    """Crosses the Emissary as enum. artifact_refs point into mnemos — the
    payloads themselves never enter the server. (§7)"""
    contract_id: str
    verdict: Verdict
    gates_passed: tuple[Gate, ...] = ()
    gates_failed: tuple[Gate, ...] = ()
    eval_score: float = 0.0
    fanout_completed: int = 0
    fanout_total: int = 0
    anomaly_flags: tuple[str, ...] = ()
    artifact_refs: tuple[str, ...] = ()


# ------------------------------------------------------- certificate & contract

@dataclass(frozen=True)
class Certificate:
    """Issued and revoked by KI alone. (I9)"""
    certificate_id: str
    task_id: str
    issued_at_rev: int
    opprocs_hash: str


@dataclass(frozen=True)
class Initiation:
    """A certified task. AgentAgent's entry point."""
    task: Task
    certificate: Certificate


@dataclass(frozen=True)
class Contract:
    """Simultaneously the agent's lifecycle, sole purpose, and prompt. (§4.2)"""
    contract_id: str
    certificate_id: str
    directive_id: str
    objective_id: str

    toolset_signature: str
    fanout_targets: tuple[str, ...]

    agent_ref: str                # retinue hash-pin, or "NEW"
    model_binding: str            # TaskMaster-assigned
    capability_floor: "CapabilityFloor" = None  # type: ignore[assignment]

    completion_predicate: CompletionPredicate = CompletionPredicate(
        CompletionKind.ALL)
    gate_chain: tuple[Gate, ...] = GATE_CHAIN
    eval_threshold: float = 0.90
    safety_threshold: float = 1.0   # never relaxed

    retry_budget: int = 2
    return_address: str = "EMISSARY"


@dataclass(frozen=True)
class CapabilityFloor:
    context_tokens: int = 8192
    tool_calling: bool = True
    modalities: tuple[str, ...] = ("TEXT",)


# ------------------------------------------------------------------ 6a. State

@dataclass(frozen=True)
class Ceilings:
    gpu: int = 0
    memory: int = 0
    disk: int = 0
    context: int = 0


@dataclass(frozen=True)
class StateSnapshot:
    """Frozen projection. KI's determinism is over this, not the live struct.
    (I12) Every field is scalar or enum — no prose ever enters State."""
    state_rev: int
    opprocs_hash: str
    wall_rev: int                 # revision ONLY, never Wall contents
    log_head: int
    recent_verdicts: tuple[Verdict, ...] = ()
    certificates_outstanding: tuple[str, ...] = ()
    agent_pool_available: tuple[str, ...] = ()
    model_residency: str = "NONE"
    toolset_locks: tuple[str, ...] = ()
    contract_queue_depth: int = 0
    ceilings: Ceilings = Ceilings()
    usage: Ceilings = Ceilings()


# ------------------------------------------------------------------- events

class EventKind(str, Enum):
    WALL_APPENDED = "WALL_APPENDED"
    LOG_APPENDED = "LOG_APPENDED"
    CERT_ISSUED = "CERT_ISSUED"
    CERT_REVOKED = "CERT_REVOKED"
    TOOLSET_LOCKED = "TOOLSET_LOCKED"
    TOOLSET_RELEASED = "TOOLSET_RELEASED"
    MODEL_LOADED = "MODEL_LOADED"
    AGENT_CHECKED_OUT = "AGENT_CHECKED_OUT"
    AGENT_RETURNED = "AGENT_RETURNED"
    CONTRACT_ENQUEUED = "CONTRACT_ENQUEUED"
    CONTRACT_CLOSED = "CONTRACT_CLOSED"
    USAGE_SAMPLED = "USAGE_SAMPLED"


@dataclass(frozen=True)
class Event:
    """Components emit these. They never mutate State directly. (I11)"""
    kind: EventKind
    subject: str = ""
    payload: tuple[tuple[str, int], ...] = ()   # scalar pairs only
