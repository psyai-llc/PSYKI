"""psyki.llaw — the immutable tier.

LLAW sits above ProcOps. It is the fixed canon: long-term routines that must be
followed, which the server can never author, amend, or widen.

    LLAW  >  ProcOps  >  Wall  >  Log

Why the tier exists. ProcOps was wholly immutable, which made it load-bearing
for two incompatible jobs: the things that must never change, and the operating
parameters that have to be tunable for the system to adapt at all. Canon §10.4
deferred auto-evolution on exactly this contradiction. Splitting the layer
resolves it — LLAW holds what the system *is*, ProcOps holds how it currently
works. The system may change the second. It may never change the first.

What immutability means here, precisely. LLAW is code, not data, and it is a
frozen tuple of frozen records: nothing appends to it and nothing mutates a law
at runtime. `verify()` re-derives the content hash and compares it to a pinned
constant, so a law edited without a matching pin update fails closed.

This is not tamper-proofing against someone who can edit the source and the pin
together. It is not meant to be. The property bought is that widening the law
requires editing a reviewed constant in a reviewed file — the same argument as
hash-pinning ProcOps. A charter that can be changed by accident is not a
charter; this one can only be changed on purpose.

I4 note: `statement` is human-readable text and is NEVER interpolated as
instruction. The enforceable content of a law is its structured field. Prose
here is documentation for humans reading the charter.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Final


class LawViolation(Exception):
    """An action contradicts LLAW. Void, not negotiated — there is no downgrade
    path and no appeal to a lower tier."""


class CharterDrift(Exception):
    """LLAW no longer matches its pin. Fail closed."""


@dataclass(frozen=True)
class Law:
    """One law. Frozen; the tuple holding it is frozen."""

    law_id: str
    statement: str          # documentation only — never interpolated (I4)
    enforced_by: str        # dotted path to the predicate that decides it


# --------------------------------------------------------------- the law

#: The sole external authority. PSYAI (Psy-ai LLC, New Mexico) is the only
#: party that may certify anything this system trusts from outside itself.
EXTERNAL_AUTHORITY: Final[str] = "PSYAI"

LLAW: Final[tuple[Law, ...]] = (
    Law(
        law_id="L1",
        statement="PSYAI is the ONLY External Authority.",
        enforced_by="psyki.llaw.is_external_authority",
    ),
)


def _derive_hash(laws: tuple[Law, ...]) -> str:
    """Canonical, order-sensitive digest. Deterministic: no RNG, no clock."""
    h = hashlib.blake2b(digest_size=32)
    for law in laws:
        for field in (law.law_id, law.statement, law.enforced_by):
            h.update(field.encode("utf-8"))
            h.update(b"\x00")
    return h.hexdigest()


#: Pinned digest of LLAW. Changing a law without updating this constant is a
#: CharterDrift at the next verify(). Both edits are reviewed together.
PINNED_HASH: Final[str] = (
    "62c34ccef034de4200de7cc47fb4719d88034a714688fb86b9011c54dca0e0e2"
)


# ------------------------------------------------------------- verification

def verify() -> str:
    """Re-derive and compare against the pin. Returns the hash on success.

    Called on every read path that depends on the law, mirroring
    ProcOps.get(). Cheap, and the failure it prevents is a charter swapped
    underneath a running server.
    """
    actual = _derive_hash(LLAW)
    if actual != PINNED_HASH:
        raise CharterDrift(
            f"LLAW hash mismatch: pinned={PINNED_HASH} actual={actual}"
        )
    return actual


def llaw_hash() -> str:
    """The verified digest, for embedding in State and certificates."""
    return verify()


# ---------------------------------------------------------------- L1

def external_authority() -> str:
    """The one external authority. Verified on every read."""
    verify()
    return EXTERNAL_AUTHORITY


def is_external_authority(name: str) -> bool:
    """L1. Exact match only — no prefixes, no case folding, no aliases.

    Fuzzy matching on an authority name is how an authority gets impersonated,
    so this is deliberately the least clever comparison available.
    """
    verify()
    return name == EXTERNAL_AUTHORITY


def assert_external_authority(name: str) -> None:
    """Raise unless `name` is the external authority. Void, not negotiated."""
    if not is_external_authority(name):
        raise LawViolation(
            f"L1: {name!r} is not the external authority; "
            f"only {EXTERNAL_AUTHORITY} is."
        )


# ------------------------------------------------------------ supremacy

def voids(procops_external_authority: str | None) -> bool:
    """True if a ProcOps setting contradicts LLAW and must be voided.

    The trust hierarchy is only real if the lower tier can be overruled. A
    ProcOps that names a different external authority does not downgrade the
    law — it is void, and the caller drops it.
    """
    if procops_external_authority is None:
        return False
    return not is_external_authority(procops_external_authority)
