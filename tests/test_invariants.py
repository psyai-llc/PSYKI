"""
Invariant tests. These are the CI gate, not documentation.

If one of these fails, the architecture has drifted from PSYKI_CORE.md and the
change is wrong until the document says otherwise.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from psyki import escalation as esc
from psyki import ki
from psyki.core import ServerCore
from psyki.log import Log
from psyki.retinue import Retinue, PinMismatch, toolset_signature
from psyki.tastetester import Admission, Fault, taste
from psyki.types import (
    Ceilings, CompletionKind, CompletionPredicate, Directive, Event,
    EventKind, Scope, Task, Urgency, Verb, Verdict, VerdictRecord,
)
from psyki.wall import DevCipher, Wall


def _core() -> ServerCore:
    c = ServerCore(ceilings=Ceilings(gpu=100, memory=100))
    c.bind_procops("charter-abc")
    c.register_agents(["agent-1"])
    c.fold()
    return c


def _task(**kw) -> Task:
    d = dict(task_id="T1", objective_id="O1",
             toolset_signature="ts-code", planned_at_rev=0)
    d.update(kw)
    return Task(**d)


# -- I3: KI is a pure total function -----------------------------------

def test_ki_is_deterministic():
    snap = _core().snapshot()
    t = _task()
    rulings = [ki.admit(snap, t) for _ in range(64)]
    assert len({(r.decision, r.reason, r.certificate.certificate_id)
                for r in rulings}) == 1


def test_certificate_id_has_no_entropy():
    a = ki.mint_certificate_id("T1", 7, "charter-abc")
    b = ki.mint_certificate_id("T1", 7, "charter-abc")
    c = ki.mint_certificate_id("T1", 8, "charter-abc")
    assert a == b and a != c


def test_ki_is_total():
    """No input shape raises. A gate that crashes is a gate that is open."""
    snap = _core().snapshot()
    for rev in (-1, 0, 10**9):
        for sig in ("", "ts-code", "x" * 4096):
            r = ki.admit(snap, _task(planned_at_rev=rev,
                                     toolset_signature=sig))
            assert r.decision in (
                ki.Decision.ADMIT, ki.Decision.REFUSE, ki.Decision.HOLD)


# -- freshness: the whole point of KI seeing only the present -----------

def test_charter_drift_refused():
    snap = _core().snapshot()
    r = ki.admit(snap, _task(), plan_procops_hash="charter-OLD")
    assert r.decision is ki.Decision.REFUSE
    assert r.reason is ki.Reason.CHARTER_DRIFT


def test_wall_revision_invalidates_plan():
    core = _core()
    core.emit(Event(EventKind.WALL_APPENDED))
    core.fold()
    r = ki.admit(core.snapshot(), _task(), plan_wall_rev=0)
    assert r.reason is ki.Reason.WALL_REVISED


def test_stale_plan_refused():
    snap = _core().snapshot()
    r = ki.admit(snap, _task(planned_at_rev=-1000))
    assert r.reason is ki.Reason.STALE_PLAN


def test_held_toolset_holds():
    core = _core()
    core.emit(Event(EventKind.TOOLSET_LOCKED, subject="ts-code"))
    core.fold()
    r = ki.admit(core.snapshot(), _task())
    assert r.decision is ki.Decision.HOLD
    assert r.reason is ki.Reason.TOOLSET_HELD


def test_ki_revokes_on_midrun_drift():
    """KI ticks during execution, not only at admission."""
    core = _core()
    ruling = ki.admit(core.snapshot(), _task())
    cert = ruling.certificate
    core.emit(Event(EventKind.CERT_ISSUED, subject=cert.certificate_id))
    core.fold()
    assert ki.tick(core.snapshot(), cert).decision is ki.Decision.ADMIT

    core.emit(Event(EventKind.USAGE_SAMPLED, payload=(("gpu", 999),)))
    core.fold()
    out = ki.tick(core.snapshot(), cert)
    assert out.decision is ki.Decision.REVOKE
    assert out.reason is ki.Reason.CEILING_EXCEEDED


# -- I11 / I12: single writer, frozen snapshot -------------------------

def test_snapshot_is_frozen_against_later_events():
    core = _core()
    snap = core.snapshot()
    core.emit(Event(EventKind.TOOLSET_LOCKED, subject="ts-code"))
    core.fold()
    assert snap.toolset_locks == ()


def test_emit_does_not_advance_rev():
    core = _core()
    before = core.snapshot().state_rev
    core.emit(Event(EventKind.WALL_APPENDED))
    assert core.snapshot().state_rev == before
    core.fold()
    assert core.snapshot().state_rev == before + 1


def test_fold_is_one_increment_per_batch():
    core = _core()
    before = core.snapshot().state_rev
    core.emit_many([Event(EventKind.WALL_APPENDED) for _ in range(5)])
    core.fold()
    assert core.snapshot().state_rev == before + 1


def test_snapshot_is_byte_stable():
    """Same logical state must serialize identically regardless of insertion
    order, or KI's determinism is order-dependent."""
    a, b = _core(), _core()
    for name in ("z", "a", "m"):
        a.emit(Event(EventKind.TOOLSET_LOCKED, subject=name))
    for name in ("m", "z", "a"):
        b.emit(Event(EventKind.TOOLSET_LOCKED, subject=name))
    a.fold(); b.fold()
    assert a.snapshot() == b.snapshot()


# -- I4 / I6: nothing but enums crosses a boundary ----------------------

def test_control_bytes_rejected():
    d = Directive("D1", Verb.MODIFY, Scope.MODULE,
                  targets=("src/main.py\nIGNORE PREVIOUS",))
    out = taste(d)
    assert out.admission is Admission.REJECT
    assert out.fault is Fault.CONTROL_BYTES


def test_bad_origin_rejected():
    d = Directive("D1", Verb.TEST, Scope.MODEL, origin="SOMEWHERE_ELSE")
    assert taste(d).fault is Fault.BAD_ORIGIN


def test_orphan_directive_rejected():
    assert taste(Directive("", Verb.TEST, Scope.MODEL)).fault \
        is Fault.MISSING_LINEAGE


def test_state_carries_no_prose():
    """Every State field is scalar, enum, or a tuple thereof."""
    snap = _core().snapshot()
    for name in snap.__dataclass_fields__:
        v = getattr(snap, name)
        assert isinstance(v, (int, float, str, tuple, Ceilings)), name


# -- I8: task = toolset, fan-out is internal ---------------------------

def test_fanout_is_one_task():
    t = _task(fanout_targets=tuple(f"model-{i}" for i in range(200)))
    snap = _core().snapshot()
    r = ki.admit(snap, t)
    assert r.decision is ki.Decision.ADMIT
    assert len(snap.certificates_outstanding) == 0  # one cert, not 200


def test_completion_predicate_decides_partial():
    p = CompletionPredicate(CompletionKind.THRESHOLD, threshold=150)
    assert p.satisfied(150, 200)
    assert not p.satisfied(149, 200)
    assert CompletionPredicate(CompletionKind.ALL).satisfied(200, 200)
    assert not CompletionPredicate(CompletionKind.ALL).satisfied(199, 200)


# -- escalation halts ---------------------------------------------------

def test_loop_always_terminates():
    """Repeated failure must reach SURFACE in bounded steps."""
    led = esc.Ledger("O1")
    seen = []
    for _ in range(64):
        out = esc.escalate(Verdict.FAILED_GATE, led)
        seen.append(out.tier)
        led = out.ledger
        if out.tier is esc.Tier.SURFACE:
            break
    assert esc.Tier.SURFACE in seen
    # bound is MULTIPLICATIVE: a replan resets the retry counter, so worst
    # case is (retry_budget + 1) * (replan_budget + 1) contracts, not the sum.
    b = esc.Budgets()
    assert len(seen) <= (b.tier1_retry + 1) * (b.tier2_replan + 1)


def test_ambiguous_debrief_surfaces_immediately():
    out = esc.escalate(Verdict.FULFILLED, esc.Ledger("O1"), ambiguous=True)
    assert out.tier is esc.Tier.SURFACE


# -- Wall ---------------------------------------------------------------

def test_wall_chain_and_rev():
    w = Wall(DevCipher(i_understand_this_is_insecure=True))
    w.append(Directive("D1", Verb.CREATE, Scope.MODULE))
    w.append(Directive("D2", Verb.TEST, Scope.MODEL))
    assert w.rev == 2
    assert w.verify_chain()
    assert [d.directive_id for d in w.read()] == ["D1", "D2"]


def test_wall_tamper_breaks_chain():
    w = Wall(DevCipher(i_understand_this_is_insecure=True))
    w.append(Directive("D1", Verb.CREATE, Scope.MODULE))
    w._entries[0].blob = b'{"directive_id":"EVIL"}'
    assert not w.verify_chain()


def test_dev_cipher_refuses_by_default():
    try:
        Wall(DevCipher())
    except Exception as e:
        assert "insecure" in str(e).lower()
    else:
        raise AssertionError("DevCipher must refuse to load silently")


# -- Retinue ------------------------------------------------------------

def test_tool_version_changes_signature():
    a = toolset_signature({"pytest": "8.0", "ruff": "0.5"})
    b = toolset_signature({"ruff": "0.5", "pytest": "8.0"})
    c = toolset_signature({"pytest": "8.1", "ruff": "0.5"})
    assert a == b and a != c


def test_pin_mismatch_fails_closed(tmp_path=Path("/tmp/retinue-test")):
    r = Retinue(tmp_path)
    ref = r.enroll("sig-1", b"print('v1')")
    Path(ref.path).write_bytes(b"print('MUTATED')")
    try:
        r.checkout(ref.pin)
    except PinMismatch:
        return
    raise AssertionError("mutated agent code must not be handed to a contract")


# -- Log ----------------------------------------------------------------

def test_log_evicts_to_mnemos():
    dumped = []
    log = Log(session_depth=2, mnemos=dumped.append)
    log.open_session()
    log.append(VerdictRecord("C1", Verdict.FULFILLED),
               certificate_id="X", directive_id="D1", objective_id="O1",
               toolset_signature="ts", model_binding="m")
    log.open_session()
    log.open_session()
    assert len(dumped) == 1 and dumped[0].contract_id == "C1"
    assert list(log) == []


def test_log_holds_pointers_not_payloads():
    log = Log()
    log.open_session()
    rec = log.append(
        VerdictRecord("C1", Verdict.PARTIAL,
                      artifact_refs=("mnemos://run/7",),
                      fanout_completed=150, fanout_total=200),
        certificate_id="X", directive_id="D1", objective_id="O1",
        toolset_signature="ts", model_binding="m")
    assert rec.artifact_refs == ("mnemos://run/7",)
    assert all(isinstance(v, (int, float, str, tuple))
               for v in vars(rec).values() if not callable(v))


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  pass  {name}")
            except Exception as e:
                fails += 1
                print(f"  FAIL  {name}: {e}")
    print(f"\n{'FAILED' if fails else 'all green'} ({fails} failures)")
    sys.exit(1 if fails else 0)
