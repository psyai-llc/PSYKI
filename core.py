"""
psyki.core — the server core.

Sole writer of State. (I11) Components emit events; the core folds them and
increments state_rev; KI takes a frozen snapshot at tick. (I12)

Concurrent mutation of State would be fatal to KI's determinism, so the fold
is single-threaded and strictly ordered. Events arriving mid-tick queue for
the next fold — they never land inside a snapshot already handed out.
"""

from __future__ import annotations

import threading
from collections import deque
from typing import Iterable

from .types import Ceilings, Event, EventKind, StateSnapshot, Verdict

RECENT_VERDICT_DEPTH = 16


class ServerCore:
    def __init__(
        self,
        ceilings: Ceilings = Ceilings(),
        recent_depth: int = RECENT_VERDICT_DEPTH,
    ) -> None:
        self._lock = threading.Lock()
        self._pending: deque[Event] = deque()
        self._recent_depth = recent_depth

        self._rev = 0
        self._procops_hash = ""
        self._wall_rev = 0
        self._log_head = 0
        self._recent: deque[Verdict] = deque(maxlen=recent_depth)
        self._certs: set[str] = set()
        self._agents: set[str] = set()
        self._model_residency = "NONE"
        self._locks: set[str] = set()
        self._queue_depth = 0
        self._ceilings = ceilings
        self._usage = Ceilings()

    # -- ingress ---------------------------------------------------------

    def emit(self, event: Event) -> None:
        """Queue an event. Does not advance state_rev."""
        with self._lock:
            self._pending.append(event)

    def emit_many(self, events: Iterable[Event]) -> None:
        with self._lock:
            self._pending.extend(events)

    # -- fold ------------------------------------------------------------

    def fold(self) -> int:
        """Apply all pending events atomically, bump state_rev, return it.

        One increment per fold, not per event: a snapshot is a coherent
        moment, and KI's freshness check compares moments.
        """
        with self._lock:
            if not self._pending:
                return self._rev
            batch = list(self._pending)
            self._pending.clear()
            for ev in batch:
                self._apply(ev)
            self._rev += 1
            return self._rev

    def _apply(self, ev: Event) -> None:
        k = ev.kind
        p = dict(ev.payload)

        if k is EventKind.WALL_APPENDED:
            self._wall_rev = p.get("wall_rev", self._wall_rev + 1)
        elif k is EventKind.LOG_APPENDED:
            self._log_head = p.get("log_head", self._log_head + 1)
            v = p.get("verdict_ord")
            if v is not None:
                self._recent.append(list(Verdict)[v])
        elif k is EventKind.CERT_ISSUED:
            self._certs.add(ev.subject)
        elif k is EventKind.CERT_REVOKED:
            self._certs.discard(ev.subject)
        elif k is EventKind.TOOLSET_LOCKED:
            self._locks.add(ev.subject)
        elif k is EventKind.TOOLSET_RELEASED:
            self._locks.discard(ev.subject)
        elif k is EventKind.MODEL_LOADED:
            self._model_residency = ev.subject
        elif k is EventKind.AGENT_CHECKED_OUT:
            self._agents.discard(ev.subject)
        elif k is EventKind.AGENT_RETURNED:
            self._agents.add(ev.subject)
        elif k is EventKind.CONTRACT_ENQUEUED:
            self._queue_depth += 1
        elif k is EventKind.CONTRACT_CLOSED:
            self._queue_depth = max(0, self._queue_depth - 1)
        elif k is EventKind.USAGE_SAMPLED:
            self._usage = Ceilings(
                gpu=p.get("gpu", self._usage.gpu),
                memory=p.get("memory", self._usage.memory),
                disk=p.get("disk", self._usage.disk),
                context=p.get("context", self._usage.context),
            )

    # -- egress ----------------------------------------------------------

    def snapshot(self) -> StateSnapshot:
        """Hand out a frozen moment. Sorted collections so that two folds
        producing the same logical state produce byte-identical snapshots."""
        with self._lock:
            return StateSnapshot(
                state_rev=self._rev,
                procops_hash=self._procops_hash,
                wall_rev=self._wall_rev,
                log_head=self._log_head,
                recent_verdicts=tuple(self._recent),
                certificates_outstanding=tuple(sorted(self._certs)),
                agent_pool_available=tuple(sorted(self._agents)),
                model_residency=self._model_residency,
                toolset_locks=tuple(sorted(self._locks)),
                contract_queue_depth=self._queue_depth,
                ceilings=self._ceilings,
                usage=self._usage,
            )

    def bind_procops(self, procops_hash: str) -> None:
        """Set once at boot from the verified charter. (I5)"""
        with self._lock:
            self._procops_hash = procops_hash

    def register_agents(self, refs: Iterable[str]) -> None:
        with self._lock:
            self._agents.update(refs)
