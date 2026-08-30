# Note 08 — Userspace initialization

**Not canon.** Design input, per `docs/notes/readme.md`.

**Sequencing.** This is post-R1.3. The loop has not run end to end even with
nulls, and userspace construction is the thing every later component stands on.
Written now so the reasoning survives; not scheduled.

---

## 1. The problem in "KI creates the userspaces"

KI is a pure total function over `(State, Plan, Event)` with no wall clock, no
RNG, and no model call (I2, I3). The CI job greps `ki.py` for nondeterminism
imports. **A pure function cannot mount a filesystem, spawn a process, or write
a file.** So KI cannot construct anything, and making it able to would cost the
invariant that makes every verdict replayable.

What KI can do is **recognize**. The split:

| | Who | When |
|---|---|---|
| **Construct** the three userspaces | boot | once, before the loop starts |
| **Bind** each to an unforgeable origin | boot, via the AK | once, at construction |
| **Recognize** an origin and admit its work | KI | every tick, purely |
| **Refuse** an unrecognized origin | KI | every tick, purely |

Same shape as the successor slot: boot does the work, KI decides the question.
This is not a workaround — a constructor that also adjudicates is a component
that can arrange its own admission.

---

## 2. The three userspaces

| Role | Component | Mandate |
|---|---|---|
| **Director** | PSY | Decides what is to be done. Never touches capability. |
| **Producer** | AgentAgent | Assembles what is needed to do it. Never decides what. |
| **Conductor** | Emissary | The sole interface between the system and everything outside it. |

Singular by construction, not by rule. They are part of the server rather than
things the server creates, so there is no mechanism that would produce a second
one. Nothing needs to forbid it.

Each can fan out to subagents without multiplying authority, because a subagent
writes only to ephemeral scope and nothing crosses back without a verdict.

### 2.1 Scope table

The divide is **write permission to durable state**. Agents produce;
meta-agents commit.

| Userspace | Reads | Writes durable | Writes ephemeral |
|---|---|---|---|
| Director | Wall, State, History — sealed, exactly (I1) | nothing | nothing |
| Producer | State, retinue, manifest, skills, procedures, styles | retinue entries, artifacts | its own scope |
| Conductor | Log, verdicts, mnemos refs | Wall (via TasteTester), Log | its own scope |
| any provisioned agent | its contract inputs | **nothing** | `tmp/<contract_id>/` |

**PSY writes nothing.** It emits a plan; the core folds it. That is I11 and it
falls out of the table rather than needing a rule.

**Per-contract tmp, never shared.** A shared scratch directory is a covert
channel between contracts that no invariant covers. Per-contract scope closes it
as a side effect.

---

## 3. Boot sequence

Fail closed at every step. Boot is now the highest-value target in the system,
because everything downstream trusts that these checks ran.

```
1.  Verify LLAW digest against the pin           → mismatch: REFUSE START
2.  Verify ProcOps pin                           → mismatch: REFUSE START
3.  Verify roles/ pin                            → mismatch: REFUSE START   (new)
4.  Successor slot POST (note 04)                → invalid: continue, bar rotation
5.  Time anchor (note 05)                        → fail: continue, UNANCHORED
6.  Construct three userspaces from a pinned spec
7.  Derive an origin identity per userspace, AK-signed
8.  Seal: no further userspace may be constructed
9.  Register the three origins in the admission table
10. Start the loop
```

Steps 1–3 refuse; 4–5 degrade. The difference is whether running is itself the
harm. A wrong charter means every subsequent verdict is issued under rules
nobody reviewed. An unanchored clock means one subsystem holds.

**Step 8 matters more than it looks.** Without an explicit seal, "only three
userspaces" is an accident of the boot script rather than a property. Sealing
makes a fourth construction attempt a detectable event.

---

## 4. Code

### New modules

**`psyki/userspace.py`**
```
Role            enum: DIRECTOR | PRODUCER | CONDUCTOR
Scope           frozen: read paths, durable write paths, ephemeral root
Userspace       frozen: role, scope, origin_id, origin_pubkey
construct()     boot only — builds the three from a pinned spec
seal()          after which construct() raises
```
No model call, no network. Filesystem and keys only.

**`psyki/origin.py`**
```
OriginId        opaque, derived from role + AK-signed attestation
verify()        pure — signature check against the registered pubkey
```
Split from `userspace.py` because KI needs `verify()` and must not import
anything that touches a filesystem. Keeping them apart is what keeps the I3
grep clean.

**`psyki/boot.py`** — the sequence above. Already proposed in note 04 for the
successor POST; this is the rest of it.

### Changes to existing modules

| Module | Change | Why |
|---|---|---|
| `types.py` | `Event` gains `origin: OriginId` | **KI currently cannot tell who asked.** It evaluates the plan's shape; a clone submitting a well-formed plan is indistinguishable from the original. This is the gap that makes the whole divide checkable. |
| `types.py` | `StateSnapshot` gains `roles_hash` | Same drift check `procops_hash` already does, for a tier that currently has none. |
| `ki.py` | `admit()` checks origin **before** plan shape | Cheapest check first, and an unrecognized origin should never reach plan evaluation. |
| `ki.py` | new `Reason.UNKNOWN_ORIGIN`, `Reason.ROLE_DRIFT` | Refusals need to be distinguishable in the record. |
| `ki.py` | `admit()` checks `llaw_hash`, then `roles_hash`, then `procops_hash` | Trust order, top down. |
| `core.py` | fold rejects a durable write whose origin lacks the scope | The divide, enforced at the one place that writes State (I11). |

**The origin check is the single highest-value change in this note.** Everything
else is scaffolding around it.

---

## 5. Dependencies

**Cryptographic.** AK signing, per note 02's three-tier hierarchy. Origin
identity must be a *signature*, not a struct KI constructs — a struct any
component can construct is not an identity. Pulls in `psyki/keys.py`, which does
not exist.

**Sandbox — and this one is not Python.** The ephemeral scope must be enforced
by the environment, not by instruction. A skill file saying "write only to your
scope" is advice; a filesystem with nothing else mounted is a boundary. If an
agent can address a durable path at all, the divide is a convention again — and
conventions get crossed by a model that was confused rather than hostile, which
is the more common case.

Concretely: Linux namespaces, or bubblewrap/nsjail locally, or per-instance
isolation on Cloud Run. **The tool manifest does not change.** `fs_write` writes
files; which paths exist is the environment's answer. Splitting the tool would
bake an environment property into a capability definition.

**Pinning `roles/`.** Currently unpinned and unchecked. Under the monolithic
role-prompt model these files are governance surface, and the server must not be
able to author its own reasoning components' instructions — the property I5 buys
for the charter, applied one tier over.

**Ordering.** `keys.py` → `origin.py` → `userspace.py` → `boot.py` → the KI
changes. The KI changes are last because they are the ones that can break a
green suite.

---

## 6. Urgent lane semantics

An audit conducted under mandate passes with urgent status. Two things this must
and must not mean:

**Urgent buys priority and non-refusal.** The audit result cannot be held,
deferred, or dropped, and it does not queue behind ordinary work. That is the
reserved lane from the L2 design, now with a concrete meaning.

**Urgent does not mean unvalidated.** TasteTester still runs. It is cheap and
schema-only, and an auditor's report enforced on arrival without a shape check
is a write path with no check on it.

**"Enforced immediately" means recorded, surfaced, and unignorable — not
self-applied.** An audit finding is a diff against ProcOps, and application
remains an out-of-band authority act with a pin update. Otherwise the server
authors its own charter and I5 is gone. Two readings of one word, and the
permissive one will be chosen by whoever implements this at speed unless the law
says which.

---

## 7. Outstanding security issues

Consolidated across notes 02, 04, 05, and this one. **Bold is unresolved and
load-bearing.**

### Trust architecture (note 05)

| # | Item | State |
|---|---|---|
| **T1** | **Bootstrap / TOFU.** Nothing verifies that whoever runs the installer is entitled to become the authority. Every downstream guarantee rests on this one unverified moment. | **open** |
| **T2** | Escrow for the pre-signed successor delegation: who holds it, threshold-split or not. | open |
| T3 | EK provenance — whether to require the TPM manufacturer CA chain, and behaviour when unavailable. | open |
| T4 | Parameters unset: liveness interval, time anchor source, notification channels, transient-loss threshold, max lease term. | open |
| T5 | Succession law text. L2 drafted for the governance audit and never finished; whether the next law is the audit law, a succession law, or both is undecided. | open |
| T6 | Auditor parameter capture — check interval and miss ceiling are levers on succession timing and must be authority-only. | open |
| S2 | Rotation record — shape given, not specified to implementation grade. | open |
| S5 | `slot_epoch` needs a hardware monotonic counter. Config-stored epochs are rollback-able. | open, real dependency |
| S6 | Ed25519 verification strictness varies by library; pin library and mode. | open |

### Userspace and divide (this note)

| # | Item | State |
|---|---|---|
| **U1** | **`Event` carries no origin.** KI cannot currently tell who asked. Until it can, the agent/meta-agent divide is unenforceable in code. | **open, blocking** |
| **U2** | **Ephemeral scope has no enforcement mechanism.** Needs namespace isolation. Instruction is not a boundary. | **open, blocking** |
| **U3** | **`roles/` is unpinned.** Governance surface with no drift check. | **open** |
| U4 | Certificates are structs, not signatures. Note 02 specifies the hierarchy; nothing is wired. A struct any component can construct is not an identity. | open |
| U5 | Per-contract tmp lifetime and size bound unset. Unbounded ephemeral storage is a disk-fill denial channel; no expiry means things quietly persist. | open |
| U6 | Boot has no watchdog. Everything trusts that steps 1–3 ran, and nothing outside boot verifies boot. | open |
| U7 | Subagent return audit: the auditor must see the **composed** result, not each fragment. Four clean fragments can compose into something neither was. | open |
| U8 | Delegation as authority substitute — if a meta-agent will commit work it did not author, a subagent gets capability by proxy and the gate never fires. | open |

### Carried from the tree

| # | Item | State |
|---|---|---|
| W1 | Wall cipher is a refusing stub. Blocking the moment a second Wall writer exists. | open |
| W2 | Per-origin Wall admission budgets, with a reserved floor for the human channel. | open |
| I1/I10 | Both invariants have zero implementation; both depend on PSY. | open |

---

## 8. What to do first

Not in build order — in *decision* order, since several of these are cheap now
and expensive later.

1. **U1.** Adding `origin` to `Event` after KI has a test suite around the
   current tuple is a retrofit across every test. Decide now even if it is built
   later.
2. **T1.** Everything in note 05 rests on it and it has no proposed answer yet.
3. **U2.** Choosing the isolation mechanism affects deployment target, and the
   Cloud Run decision is already in flight.
4. **U3.** One pin, one check, closes a whole unguarded tier.

Everything else can wait for its own session.
