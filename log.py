"""
psyki.log — contract-level records. Bounded.

Holds verdicts, counts, deltas, anomaly flags, and POINTERS. Never prose,
never artifacts. (§7)

The rule that keeps the split honest: if PSY ever needs to read mnemos to
understand the present, the split is wrong. Everything PSY needs is here;
everything else evicts.

Depth is a couple of sessions. When a record falls out, it goes to mnemos and
is gone from the server — recoverable only by explicit Emissary retrieval,
never by PSY on its own initiative.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Callable, Iterator, Optional

from .types import Verdict, VerdictRecord


@dataclass(frozen=True)
class ContractRecord:
    """One closed contract. Everything scalar or enum."""
    seq: int
    session: int
    contract_id: str
    certificate_id: str
    directive_id: str
    objective_id: str
    toolset_signature: str
    model_binding: str
    verdict: Verdict
    eval_score: float
    fanout_completed: int
    fanout_total: int
    retries_used: int
    anomaly_flags: tuple[str, ...] = ()
    artifact_refs: tuple[str, ...] = ()   # mnemos pointers, never inline


MnemosSink = Callable[[ContractRecord], None]


class Log:
    def __init__(
        self,
        session_depth: int = 2,
        mnemos: Optional[MnemosSink] = None,
    ) -> None:
        self._session_depth = session_depth
        self._mnemos = mnemos
        self._records: deque[ContractRecord] = deque()
        self._seq = 0
        self._session = 0

    # -- write -----------------------------------------------------------

    def open_session(self) -> int:
        self._session += 1
        self._evict()
        return self._session

    def append(
        self,
        vr: VerdictRecord,
        *,
        certificate_id: str,
        directive_id: str,
        objective_id: str,
        toolset_signature: str,
        model_binding: str,
        retries_used: int = 0,
    ) -> ContractRecord:
        self._seq += 1
        rec = ContractRecord(
            seq=self._seq,
            session=self._session,
            contract_id=vr.contract_id,
            certificate_id=certificate_id,
            directive_id=directive_id,
            objective_id=objective_id,
            toolset_signature=toolset_signature,
            model_binding=model_binding,
            verdict=vr.verdict,
            eval_score=vr.eval_score,
            fanout_completed=vr.fanout_completed,
            fanout_total=vr.fanout_total,
            retries_used=retries_used,
            anomaly_flags=vr.anomaly_flags,
            artifact_refs=vr.artifact_refs,
        )
        self._records.append(rec)
        self._evict()
        return rec

    def _evict(self) -> None:
        floor = self._session - self._session_depth + 1
        while self._records and self._records[0].session < floor:
            dropped = self._records.popleft()
            if self._mnemos is not None:
                self._mnemos(dropped)

    # -- read ------------------------------------------------------------

    @property
    def head(self) -> int:
        return self._seq

    def __iter__(self) -> Iterator[ContractRecord]:
        return iter(self._records)

    def recent_verdicts(self, n: int = 16) -> tuple[Verdict, ...]:
        return tuple(r.verdict for r in list(self._records)[-n:])

    def retries_for_objective(self, objective_id: str) -> int:
        return sum(
            r.retries_used for r in self._records
            if r.objective_id == objective_id
        )

    def failures_for_objective(self, objective_id: str) -> int:
        return sum(
            1 for r in self._records
            if r.objective_id == objective_id
            and r.verdict not in (Verdict.FULFILLED,)
        )
