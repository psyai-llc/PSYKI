# PSYKEY — Core Architecture

**Truth-Structure:** neo-canonical (the truth for this repo is still developing, it can be asked that the most recent file supersedes previous files in the event of conflicting information.

**Provenance:** truth is the root of trust, and truth is never assumed it must be proven and evaluated. Truth os not Boolean it is a floating point derived from consistent evaluation. Nothing here is inherited unexamined from prior authorship.

**Standards:** A common agentic protocol is formed through the Procedures of
Operation, the Contract, and the LLAW. LLAW is the immutable read-only core —
long-term routines that must be followed, which the server can never author.
ProcOps is the operational layer above it, tunable under gates. The Contract
binds both to a single task. Together they are the self-governing structure:
the system can change how it works, never what it is.
---

## 0. Shape

Three reasoning components. Everything else is deterministic code.

| Component | Kind | Role |
|---|---|---|
| **Emissary** | model | sole membrane. NL↔enum, both directions. |
| **PSY** | model | temporal planner. Wall + present + history → target → objectives → tasks. |
| **AgentAgent** | model | agent design, code authoring, test authoring. TaskMaster is its subagent. |
| KI | **code** | certifying authority. Admits, certifies, revokes. Never reads text. |
| TasteTester | **code** | schema + security validation at the Wall write path. |
| **State** | **code** | bounded projection of all server data. Server core is sole writer. |
| Wall | **code** | encrypted, user-authored, append-only. |
| Log | **code** | server events + contract records. Bounded depth. |
| Retinue | **code** | agent code indexed by toolset signature. Hash-pinned. |
| LLAW | **code** | immutable charter. The one thing the system cannot change. Hash-pinned. |
| ProcOps | **code** | read-only charter. Hash-verified on every read. |

**Trust hierarchy:** `LLAW ≻ ProcOps ≻ Wall ≻ Log`. A ProcOps setting
contradicting LLAW is voided, not negotiated. A directive contradicting ProcOps
is voided, not negotiated. A log record never overrides a Wall directive.

### 0.1 LLAW

The immutable tier. Read-only, hash-pinned, and unauthorable by the server —
strictly stronger than ProcOps, which is tunable. LLAW holds what the system
*is*; ProcOps holds how it currently works.

The split exists because one layer was carrying two incompatible jobs: things
that must never change, and operating parameters that have to be tunable for
the system to adapt at all. §10.4 deferred auto-evolution on exactly that
contradiction.

| # | Law |
|---|---|
| **L1** | PSYAI is the ONLY External Authority. |

PSYAI is Psy-ai LLC, New Mexico. L1 is the whole of LLAW today, deliberately:
it establishes the structure while imposing no limits on what is being built.

Adding or amending a law is a human act — it requires editing a reviewed
constant and its pinned digest together in `psyki/llaw.py`. A charter that can
change by accident is not a charter.


---

## 1. The cycle

```
  user NL ──▶ EMISSARY ──enum──▶ TasteTester ──▶ WALL
                  ▲                                │
                  │                                ▼
                  │              ProcOps ──▶ [Wall + State + History]
                  │                                │
                  │                                ▼
                  │                              PSY
                  │                    target → objectives → tasks
                  │                                │
                  │                             (task = toolset)
                  │                                ▼
                  │                               KI ──── certificate
                  │                          present state only
                  │                                │
                  │                            INITIATION
                  │                                ▼
                  │                          AGENTAGENT
                  │                     design · code · tests
                  │                     TaskMaster: model binding
                  │                                │
                  │                            CONTRACT
                  │                                ▼
                  │                       provisioned agent
                  │                       executes until gates green
                  │                                │
                  │                             DEBRIEF
                  └────────────────────────────────┘
                         (enum only — never prose)

        artifacts, prose, raw output ──▶ MNEMOS (archive)
```

**The Emissary is the only membrane.** Every piece of untrusted text — user
input, agent reports, fetched content, mnemos retrieval — crosses here and
converts to enum. Nothing else in the system reads free text.

**Consequence:** the enum protocol is the security boundary, not the model. A
compromised Emissary can only express what the vocabulary allows.

---

## 2. Invariants

| # | Invariant |
|---|---|
| **I1** | PSY's context is exactly `(Wall, State, History)`. Sealed; audited byte-wise. |
| **I2** | KI's context is exactly `(State, Plan, Event)`. No history, no future. |
| **I3** | KI is a pure total function. No RNG, no wall-clock, no model call. |
| **I4** | No prose crosses any internal boundary. Enum + typed fields only. |
| **I5** | ProcOps is read-only and hash-pinned. The server cannot author its charter. |
| **I6** | Only TasteTester-admitted bytes reach the Wall. |
| **I7** | Every objective carries a traceable `directive_id`. Orphans rejected at plan validation. |
| **I8** | A task is bounded by its toolset. Fan-out is internal to a task. |
| **I9** | Certificates are issued and revoked by KI alone. |
| **I10** | Both PSY and KI operate under a dynamic context choke ≤ server capacity. |
| **I11** | The server core is the sole writer of State. Components emit events; they never mutate State. |
| **I12** | KI reads a frozen State snapshot at tick. Determinism is over the snapshot, not the live struct. |
| **I13** | LLAW is immutable and outranks ProcOps. The system may change how it works; it may never change what it is. |

---

## 3. Task boundary rule

**A task is defined by its toolset.** Same tools = one task, regardless of
target count. Testing 1 model and testing 200 models are the same task with
different fan-out. The moment the required toolset changes, it is a new task.

This makes task decomposition deterministic rather than a judgment call, and
makes agent provisioning nearly free: the agent *is* the toolset plus a purpose.

The tool manifest therefore partitions the task-type space.

---

## 4. Enum protocol

Three vocabularies. Enums carry the **frame**; typed fields carry the
**content**. String fields exist but are never interpolated as instruction.

### 4.1 Intent (Emissary → Wall)

```
VERB     := CREATE | MODIFY | ANALYZE | TEST | RESEARCH
          | DEPLOY | REPAIR | DOCUMENT | REMOVE | EVALUATE
SCOPE    := FILE | MODULE | REPO | SERVICE | DATASET | MODEL | SYSTEM
URGENCY  := DEFER | NORMAL | PRIORITY | IMMEDIATE
```

**Emissary hard rule:** if intent cannot be encoded, it *refuses and re-asks*.
It never approximates. A silently lossy Emissary is the worst failure this
design admits, because nothing downstream can detect it.

### 4.2 Contract (AgentAgent → provisioned agent)

The contract is simultaneously the agent's lifecycle, sole purpose, and prompt.

```
Contract {
  contract_id
  certificate_id          # KI-issued; invalidated on fulfillment
  directive_id            # lineage to Wall — I7
  objective_id

  toolset_signature       # defines the task — I8
  fanout_targets[]        # 1..N; internal to the task

  agent_ref               # retinue hash-pin, or NEW
  model_binding           # TaskMaster-assigned
  capability_floor        # context, modality, tool-calling

  completion_predicate    # see below
  gate_chain              # format→lint→typecheck→test→coverage→security
  eval_threshold          # default 0.90; safety = 1.0 always

  retry_budget
  return_address          # Emissary debrief channel
}

COMPLETION := ALL | THRESHOLD(n) | BEST_EFFORT | FIRST_SUCCESS
```

Completion predicate is set at authoring time, not decided at debrief. This is
what resolves partial failure inside a fan-out task.

### 4.3 Verdict (agent → Emissary → Log)

```
VERDICT  := FULFILLED | PARTIAL | FAILED_GATE | FAILED_TOOL
          | FAILED_BUDGET | STALLED | REJECTED | ESCALATE

VerdictRecord {
  contract_id
  verdict
  gates_passed[]  gates_failed[]
  eval_score
  fanout_completed / fanout_total
  anomaly_flags[]
  artifact_refs[]         # pointers into mnemos — never inline
}
```

For code-shaped contracts the debrief **is** the test report. Already
enum-shaped, needs no interpretation.

---

## 5. Lifecycle

1. KI issues certificate → task becomes Initiation.
2. AgentAgent designs; TaskMaster binds model → Contract.
3. Agent executes until gate chain green or retry budget exhausted.
4. Debrief crosses the Emissary as enum → Log.
5. **KI revokes the certificate.** Model returns to pool. Agent code returns to
   Retinue, hash-pinned and versioned. Prose and artifacts go to mnemos.

The contract *is* the agent's lifespan. Nothing survives it but the record.

---

## 6. Escalation tiers

| Tier | Trigger | Handler |
|---|---|---|
| 1 | contract fails gates | AgentAgent retries within retry budget |
| 2 | tier-1 budget exhausted | PSY replans the objective |
| 3 | replan counter exceeded | **Emissary returns to the user** |

Tier 3 is the termination condition for the closed loop. The cycle
Emissary→Wall→PSY→KI→AgentAgent→execution→Emissary has no human in it; the
replan counter is what guarantees it halts.

**Ambiguous debrief also escalates to tier 3.** There is no user to interrogate
on the return path, so the Emissary surfaces rather than guesses.

---

## 6a. State

State is derived from **everywhere** and materialized as **one bounded struct**.
It is a projection, not a collection. Components write into it by emitting
events to the server core; nobody reads its sources through it.

Every field is scalar or enum. No prose ever enters State.

```
State {
  state_rev               # monotonic; the freshness anchor
  procops_hash            # I5 verification

  wall_rev                # revision number ONLY — never Wall contents
  log_head
  recent_verdicts[]       # last N, enum only

  certificates_outstanding[]
  agent_pool_available[]
  model_residency         # which model is loaded now
  toolset_locks[]         # tools currently held by a live contract
  contract_queue_depth

  ceilings { gpu, memory, disk, context }
}
```

**Who reads what:**

- PSY reads Wall contents directly, plus State, plus History. (I1)
- KI reads State, Plan, Event. Never Wall, never Log, never prose. (I2)
- The Emissary reads State only to report status back to the user.

**The freshness check.** PSY plans against `state_rev = N`. KI ticks at
`state_rev = M`. If any precondition changed between N and M, KI refuses
admission or revokes a running certificate. This is the entire justification
for KI seeing only the present, and it is why the revision counter exists.

**Write discipline.** Concurrent mutation on the one structure KI's determinism
depends on would be fatal, so the server core owns it: components emit events,
the core folds them into State and increments `state_rev`, KI takes a frozen
snapshot at tick. Determinism is over the snapshot. (I11, I12)

---

## 7. Memory discipline

- **Log** holds contract-level records only: verdict, deltas, counts, anomaly
  flags, pointers. Small, enum, bounded to a few sessions.
- **Mnemos** holds everything else: prose, artifacts, raw output. Unbounded.
- **Rule:** if PSY ever needs to read mnemos to understand the present, the
  split is wrong.
- Mnemos retrieval is **explicitly requested only** — PSY cannot trigger it.
  Retrieved content re-enters through the Emissary as enum, like any ingress.

---

## 8. Model binding

Role→model is configuration, not architecture. Swapping a model does not ripple
because the enum protocol isolates it.

| Role | Candidate | Rationale |
|---|---|---|
| PSY | VibeThinker-3B | deep single-shot reasoning, no dialogue, no tools |
| Emissary | Gemma 4 E4B | multimodal, conversational; disambiguation is a dialogue |
| AgentAgent | largest available + escalation hook | heaviest role; design quality gates everything |

**AgentAgent authors the design and the tests. A smaller model runs the
implement loop until green.** This is what makes local models viable — it
converts "write correct code" into "iterate until the oracle says yes." Keep
the escalation path for contracts that exhaust retries on genuinely hard work.

**Residency is a schedule, not an allocation.** The pipeline is sequential;
model swap cost per phase is an unmeasured number that determines whether an
objective loop takes seconds or minutes. Measure it early.

---

## 9. Port manifest

### From AgentAgent2 — take
- `AGENTAGENT2.system.md` — **truncated**: enters at DESIGN, exits at DELIVER.
  Its INTENT and PLAN phases are satisfied externally by the Contract. Its
  DEBRIEF becomes a boundary crossing, not a terminal phase.
- `skills/` (9) — especially `subagent-orchestration` → TaskMaster
- `style/` — 5-language style engine, keep whole
- `tools/tool_manifest.json` — becomes the task-type partition
- `design/schemas/agent_design.schema.json`
- `templates/agent_project_scaffold/` — gate-ready skeleton

### From AgentAgent2 — leave
Duplicate `(1)` files, `agentagent2-complete.zip`, session-event JSON at public
root, `verify_report*.json`. Do not inherit the hygiene.

### From PSYKI v0 — take
- ProcOps concept (read-only hash-pinned charter)
- KI determinism harness and CI gate
- Lateral-inhibition fix in the BG gate (Buridan deadlock)
- Sealed-context whitespace→word-boundary audit fix
- Wall append-only + hash chain **— but replace blake2b-XOR with
  XChaCha20-Poly1305 before the Wall takes a second writer**

### From PSYKI v0 — leave
- The corpus/database layer
- `NullPlanner` beyond its role as ablation control
- Regex-only taste test as a boundary (keep as speed bump with telemetry)
- The v0 module map, which never matched the tree

---

## 10. Open

1. **Model swap cost** — unmeasured. Gates the whole latency picture.
2. **State event ordering** — resolved that the core is sole writer (§6a). Open:
   whether the event fold is strictly ordered or batched per tick, and what
   happens to events arriving mid-tick.
3. **Retinue versioning** — a tool changing under a cached agent is a nasty
   silent failure. Needs a tool-version component in the signature.
4. **Auto-evolution** — deferred. A system with a return path that rewrites its
   own settings observes its own effects. Gate behind the replan counter and
   the escalation tiers, not just metrics. LLAW stays immutable regardless —
   that tier is what makes tuning ProcOps safe to contemplate at all.
