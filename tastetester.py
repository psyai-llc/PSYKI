"""
psyki.tastetester — the Wall write gate.

CODE, not a model, and deliberately OUTSIDE the Emissary. Adversarial-intent
judgment belongs to the Emissary (that is reasoning work), but if the Emissary
also validated its own output there would be no independent check on the one
boundary the user actually owns.

So: the Emissary decides whether an intent is hostile. TasteTester decides
whether the artifact is well-formed and structurally safe. Both must pass.

This is a structural validator, not a regex screen. v0's regex list stays only
as a telemetry speed bump — a denylist on a field that should have been an
enum is theatre.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .procops import ProcOps
from .types import Directive, Scope, Urgency, Verb

MAX_TARGETS = 4096
MAX_CONSTRAINTS = 64
MAX_IDENT = 512


class Admission(str, Enum):
    ADMIT = "ADMIT"
    REJECT = "REJECT"


class Fault(str, Enum):
    OK = "OK"
    BAD_ENUM = "BAD_ENUM"
    MISSING_LINEAGE = "MISSING_LINEAGE"
    OVERSIZE = "OVERSIZE"
    NONSCALAR_FIELD = "NONSCALAR_FIELD"
    CONTROL_BYTES = "CONTROL_BYTES"
    CHARTER_VOID = "CHARTER_VOID"
    BAD_ORIGIN = "BAD_ORIGIN"


VALID_ORIGINS = frozenset({"USER", "DEBRIEF", "RETRIEVAL"})


@dataclass(frozen=True)
class Tasting:
    admission: Admission
    fault: Fault
    detail: str = ""


def taste(directive: Directive, charter: ProcOps | None = None) -> Tasting:
    """Pure. Same directive, same verdict, always."""

    def no(fault: Fault, detail: str = "") -> Tasting:
        return Tasting(Admission.REJECT, fault, detail)

    if not directive.directive_id:
        return no(Fault.MISSING_LINEAGE, "empty directive_id")

    if not isinstance(directive.verb, Verb):
        return no(Fault.BAD_ENUM, "verb")
    if not isinstance(directive.scope, Scope):
        return no(Fault.BAD_ENUM, "scope")
    if not isinstance(directive.urgency, Urgency):
        return no(Fault.BAD_ENUM, "urgency")

    if directive.origin not in VALID_ORIGINS:
        return no(Fault.BAD_ORIGIN, directive.origin)

    if len(directive.targets) > MAX_TARGETS:
        return no(Fault.OVERSIZE, "targets")
    if len(directive.constraints) > MAX_CONSTRAINTS:
        return no(Fault.OVERSIZE, "constraints")

    for group in (directive.targets, directive.constraints):
        for item in group:
            if not isinstance(item, str):
                return no(Fault.NONSCALAR_FIELD, repr(type(item)))
            if len(item) > MAX_IDENT:
                return no(Fault.OVERSIZE, item[:32])
            if _has_control_bytes(item):
                return no(Fault.CONTROL_BYTES, item[:32])

    # charter supremacy — voided, not negotiated (I5)
    if charter is not None and charter.voids(
        directive.verb.value, directive.scope.value
    ):
        return no(
            Fault.CHARTER_VOID,
            f"{directive.verb.value}/{directive.scope.value}",
        )

    return Tasting(Admission.ADMIT, Fault.OK)


def _has_control_bytes(s: str) -> bool:
    """Identifiers are identifiers. Newlines and control characters in a field
    that reaches a prompt assembler are the classic injection carrier — and
    these fields are opaque refs, so there is never a legitimate one."""
    return any(ord(c) < 0x20 or ord(c) == 0x7F for c in s)
