# Note 06 — System architecture: internal

**Not canon.** Design input, per `docs/notes/readme.md`. Where this and
`docs/PSYKI_CORE.md` disagree, canon wins. Items marked **AMEND CANON** are
proposals for a human edit, not statements of fact about canon.

**Scope.** The system as it works internally: the loop, the components, the
invariants, what is built and what is not. **Everything concerning keys, the
external authority, time anchoring, succession, and offline operation is
deliberately excluded** — that is note 05, and it is an end goal rather than a
next step. §9 is the seam.

**Purpose.** An overview for planning, not a task list. Note 03 holds the
instruction-grade R1 specs; this document is the map they sit on.

---

## 1. Shape

Three reasoning components. Everything else is deterministic code.

| Component | Kind | Role | Status |
|---|---|---|---|
| **Emissary** | model | Sole membrane. NL↔enum, both directions. | **absent** — no module, no role spec |
| **PSY** | model | Temporal planner. Wall + present + history → target → objectives → tasks. | **absent** — one-line role stub |
| **AgentAgent** | model | Agent design, code authoring, test authoring. TaskMaster is its subagent. | **absent as code**; role spec present but unported |
| KI | code | Certifying authority. Admits, certifies, revokes. Never reads text. | built, tested |
| TasteTester | code | Schema + security validation at the Wall write path. | built, tested |
| State / core | code | Bounded projection of all server data. Core is sole writer. | built, tested |
| Wall | code | Encrypted, user-authored, append-only. | built; **cipher is a refusing stub** |
| Log | code | Server events + contract records. Bounded depth. | built, tested |
| Retinue | code | Agent code indexed by toolset signature. Hash-pinned. | built, tested |
| LLAW | code | Immutable charter. | built, tested, **wired to nothing** |
| ProcOps | code | Read-only charter, hash-verified on every read. | built, tested |
| Mnemos | code | Unbounded artifact archive. | **absent** — eviction hook only |
| MCP server surface | code | The callable interface. | **absent** |
| Loop / orchestrator | code | Runs the cycle. | **absent** |

**Trust hierarchy:** `LLAW ≻ ProcOps ≻ Wall ≻ Log`. A ProcOps setting
contradicting LLAW is voided, not negotiated. A directive contradicting ProcOps
is voided. A log record never overrides a Wall directive.

---

## 2. The cycle

```
  user NL ──▶ EMISSARY ──enum──▶ TasteTester ──▶ WALL
                  ▲                                │
                  │              ProcOps ──▶ [Wall + State + History]
                  │                                │
                  │                              PSY
                  │                    target → objectives → tasks
                  │                       (task = toolset)
                  │                                ▼
                  │                               KI ──── certificate
                  │                          present state only
                  │                            INITIATION
                  │                                ▼
                  │                          AGENTAGENT
                  │                     design · code · tests
                  │                  TaskMaster: model binding
                  │                            CONTRACT
                  │                                ▼
                  │                       provisioned agent
                  │                    executes until gates green
                  │                             DEBRIEF
                  └────────────────────────────────┘
                         (enum only — never prose)

        artifacts, prose, raw output ──▶ MNEMOS (archive)
```

**The Emissary is the only membrane.** Every piece of untrusted text — user
input, agent reports, fetched content, mnemos retrieval — crosses here and
converts to enum. Nothing else reads free text.

**Consequence:** the enum protocol is the security boundary, not the model. A
compromised Emissary can only express what the vocabulary allows.

**Termination.** The loop has no human in it. Tier 1 retries within budget, tier
2 replans, tier 3 surfaces to the user. The replan counter is the entire halting
argument.

---

## 3. Invariants and their coverage

| # | Invariant | Coverage |
|---|---|---|
| I1 | PSY's context is exactly `(Wall, State, History)`. Sealed; audited byte-wise. | **none** — depends on PSY |
| I2 | KI's context is exactly `(State, Plan, Event)`. | named, tested |
| I3 | KI is a pure total function. No RNG, no wall-clock, no model call. | named, tested, CI-gated |
| I4 | No prose crosses any internal boundary. | named, tested |
| I5 | ProcOps is read-only and hash-pinned. | tested, no ID assertion |
| I6 | Only TasteTester-admitted bytes reach the Wall. | named, tested |
| I7 | Every objective carries a traceable `directive_id`. | tested, no ID assertion |
| I8 | A task is bounded by its toolset. | named, tested |
| I9 | Certificates are issued and revoked by KI alone. | tested, no ID assertion |
| I10 | PSY and KI operate under a dynamic context choke ≤ server capacity. | **none** — depends on PSY |
| I11 | The core is the sole writer of State. | named, tested |
| I12 | KI reads a frozen State snapshot at tick. | named, tested |
| I13 | LLAW is immutable and outranks ProcOps. | tested, but **not enforced at runtime** |

**I1 and I10 are the two that cannot be closed by wiring** — both require PSY to
exist. I13 is enforceable in principle and enforced nowhere (§4.1).

---

## 4. What is built, and what is wrong with it

10 runtime modules, ~1,100 lines. Invariant suite 36/36 green with zero
dependencies; structural oracle 14/14; three CI jobs (structure, I3 determinism
grep, full suite).

**The central fact:** every module is tested in isolation and **none have ever
run together.** No orchestrator, no server surface, no reasoning components. A
skeleton with no spine.

### 4.1 LLAW is an island — blocking for I13

`psyki/llaw.py` is complete with nine tests and is imported by nothing but the
test file. `StateSnapshot` has no `llaw_hash` despite the module's own docstring
saying the digest exists for embedding in State and certificates. `ki.admit()`
checks `procops_hash` only. `llaw` is absent from `__init__.__all__`. The
ranking exists in `llaw.voids()`, which no runtime path calls.

Highest-value small fix in the tree. R1.1.

### 4.2 `config/` and `tools/` are unported AgentAgent2 artifacts — blocking

`config/agent.config.json` names itself `AgentAgent2` and references four paths
that do not exist. It survived because the structural oracle checks paths
referenced by *tests and CI*, not by *config* — the AGENTS.md §3 failure one
layer out of the oracle's reach. R1.0.

### 4.3 Tool manifest is a data gap, not a design question

Canon §10.3 flags tool-versioning as open. But `retinue.toolset_signature()`
already takes `dict[name→version]` and its test passes. The mechanism is built
and proven; the manifest simply has no versions in it. A migration, not
research. R1.2. **AMEND CANON.**

### 4.4 `roles/agentagent.md` is untruncated

Canon §9 requires DESIGN→DELIVER. The file is the full nine-phase prompt
including INTENT, PLAN, and a user-communication section. As-is it would run a
second planner inside a system where PSY plans, and address the user across a
boundary only the Emissary may cross (I4). `roles/ki.md` and `roles/psy.md` are
one-line stubs; `roles/emissary.md` does not exist — the sole membrane has no
specification. R1.0.

### 4.5 Wall cipher is a refusing stub

`DevCipher` correctly refuses without an explicit insecurity acknowledgement.
Canon §9 requires XChaCha20-Poly1305 **before the Wall takes a second writer**.
Deferred while there is one producer; blocking the moment there is another.

### 4.6 Mnemos has a hook and no store

`Log._evict()` calls an optional callback. `VerdictRecord.artifact_refs[]` points
into nothing. Not blocking the spine; blocking for artifact-producing contracts.

### 4.7 Canon drift

- §8 model table still lists VibeThinker-3B for PSY (withdrawn on licence).
- Canon is titled `# PSYKEY`; repo and README say PSYKI.
- §10.2 predates `fold()`'s actual batched, one-increment-per-fold behaviour.

All three **AMEND CANON**, all human decisions.

---

## 5. The keystone: R1.3

The obvious next move is to build the Emissary, since nothing is callable
without it. That is a trap. Three reasoning components on a substrate that has
never executed as a unit means debugging model behaviour and plumbing
simultaneously, with no way to tell which is lying.

**Instead: wire the deterministic spine end to end with the reasoning components
stubbed to fixed enums.** `NullEmissary` returns a canned `Directive`; `NullPSY`
returns one objective with one task; `NullAgentAgent` returns a contract that
immediately reports `FULFILLED`.

If that runs — Wall append → fold → PSY → KI admit → certify → contract →
verdict → Emissary → Log → KI revoke → retinue return — then every real model
after is a **single-component swap against a proven harness**, and any failure
is unambiguously attributable.

The acceptance test asserts a `trace` list matching canon §1's ordering, plus a
failure test proving escalation terminates. The nulls stay permanently as
ablation controls.

Also lands here: `psyki/roles.py` (Protocol definitions — the seams every later
milestone plugs into) and a definition for **`History`**, which is currently
nowhere despite being one third of I1's context tuple. Defining it late means
retrofitting I1.

**Nothing in note 05, and nothing in §7 below, should be built before this.**

---

## 6. Sequencing

```
R1.0  reconciliation            EXCLUSIVE — touches canon + config paths
        ├── R1.1  LLAW wiring        ─┐
        ├── R1.2  tool manifest port  ├─ parallel
        ├── R1.8  wall crypto        ─┘
        ▼
R1.3  the spine (loop + null roles)   ← KEYSTONE
        ├── R1.4  MCP server surface
        └── R1.5  Emissary ─▶ R1.6 PSY ─▶ R1.7 AgentAgent + TaskMaster
```

R1.0 is exclusive — it edits canon and rewrites config paths other tasks read.

Out-of-band and unblocked: **move `psyai.cloud` nameservers to Cloudflare.** The
only step with propagation delay, commits to no cloud, prerequisite for R1.4.

Instruction-grade specs for all of the above are in note 03.

---

## 7. Design decisions made since R0 — not yet in canon, not yet built

These were resolved in design sessions and have no home in the tree yet. They
belong to R1.6 or later.

### 7.1 PSY model binding

PSY's requirement profile is unusual: no tools, no dialogue, no prose output, a
sealed context choked by I10. Long context, tool use, multimodality and agentic
coding are all worthless to it. What remains is decomposition quality and
structured-output reliability.

**Key move:** structured-output reliability should come from
**grammar-constrained decoding** built from the §4.1 enum vocabulary, not from
the model. This makes malformed emission unrepresentable rather than unlikely,
enforces I4 at the sampler, and removes the failure mode that normally forces a
larger model. Small then becomes a feature — §8 says residency is a schedule, so
parameter count is a direct per-objective latency tax.

Candidates, all local (note 02's `binding_strength` bars asserted-only hosted
models from sensitive tiers, and planning is a sensitive tier):

- **Phi-4-reasoning, 14B, MIT** — primary. Long-CoT-then-answer shape matches
  PSY structurally; the CoT is discarded to mnemos anyway.
- **Phi-4-mini, 3.8B, MIT** — swap-cost-optimised tier.
- **Qwen3.5 small variants, Apache 2.0** — fallback; dual think mode is useful
  for cheap replans vs. hard decomposition.

Not Gemma — it is bound to the Emissary, where multimodal and conversational
ability earn their keep.

**Build the eval in R1.3 using the `NullPSY` slot:** frozen directives with
Wall/State/History fixtures, scored on valid-emission rate under grammar, orphan
`directive_id` rate (I7), toolset partition correctness (I8), and objective-count
stability across identical reruns. Yields the §10.1 swap-cost number as a side
effect and converts model choice from opinion to measurement. No public
benchmark measures this task shape.

### 7.2 Cortical layer for PSY

The v0 assignment (PSY → cortex + hippocampus, KI → basal ganglia + brainstem)
was correct and R0 did not reject it; it demoted `neuro.py` into `ki.py` as an
implementation detail. But everything that survived is **subcortical**. Every
*cortical* mechanism is unbuilt. The proposal is not new — it is the deferred
half.

**Note:** PSY does not see the whole server. I1 pins its context; canon §6a makes
State a bounded projection whose sources are not readable through it. Nothing in
PSYKI sees the whole server, deliberately. The analogy improves under this —
**State is the thalamus.**

Build two, defer one:

1. **`DeltaContext` (predictive coding) closes I10.** Reframes the context choke
   from truncation to information theory: send prediction error, not State.
   Context shrinks by exactly what the system predicts well. **Catch:** the
   predictor is stateful across cycles, colliding with I1's byte-wise seal.
   Resolvable only if the predictor lives *outside* PSY and the delta is
   computed on the way in, so PSY still receives exactly the sealed tuple. Must
   be designed that way from the start or I1 breaks quietly.
2. **`consolidate()` (hippocampal replay) gives History a definition.** Left
   alone, History defaults to last-N `VerdictRecord`s — uniform recency, the
   weakest option. v0 already specifies priority by |reward| + surprise, with
   retrieval MRR as its ablation metric.
3. **`Neuromod` deferred hard.** It modulates temperature, replan trigger,
   horizon and model tier from a global scalar — and it touches the replan
   counter, which is the entire halting argument.

**Discipline (the operator's own v0 rule):** every neuromorphic component ships
with an ablation flag; a component whose ablation changes no metric was
metaphor and gets deleted. No ablation harness exists in the tree. Requirement:
named metric + ablation flag + CI comparison.

**Critical constraint:** this layer is **code, not a model**. PSY-the-model stays
a model; the cortical layer is deterministic code shaping what crosses the seal
in both directions. Delta over enums is still enums, so I4 holds, and the layer
stays model-agnostic — a layer fused to Phi would be a liability.

### 7.3 L2 — governance audit law (drafted, unfinished)

**Shape:** when the interval since the last governance audit is exceeded, a
gov-audit contract must be created and an ephemeral auditor given a frozen
mandate. It researches, commits a report, and the report drives ProcOps change.

Resolved design points:

- **Two independent triggers.** Rapid mutation and stagnation are different
  failure modes and neither catches the other. Event delta (`state_rev`) is
  pure and KI-evaluable in-loop. Time delta must be evaluated by a **supervisor
  outside the loop** — its purpose is catching a stalled loop, and an in-loop
  trigger cannot fire when the loop itself is the failure. A watchdog inside the
  process it watches is not a watchdog.
- **The mandate is a separate frozen constant in `llaw.py`, folded into the same
  digest** — not the law statements, which are documentation and never
  interpolated (I4). The mandate may be written as a prompt.
- **The auditor emits a typed proposal, not modules.** A report that writes
  ProcOps modules destroys I5 — ProcOps is hash-pinned precisely so the server
  cannot author its charter, and I5 is what LLAW's existence argument rests on.
  The proposal is a diff, runs the normal gate chain, gets a verdict, gets
  logged; **application is an out-of-band act by the external authority with a
  pin update.** I5 needs amending to distinguish "tunable" from "authored by the
  server." **AMEND CANON.**
- **Auditor independence is structural:** its toolset comes from the frozen
  mandate, not from PSY. Under I8 the planner partitions toolsets; if PSY
  assigned them, PSY would be constraining the audit of PSY.
- **Reports persist and the auditor reads prior ones.** The agent is ephemeral;
  continuity lives in the artifact. Prior reports are evidence, never
  instruction.
- **Reserved admission lane.** KI can `HOLD` on saturation; an audit held
  indefinitely under load never runs precisely when most needed. Note 01 made
  the same argument for the human channel's floor — the two things that must
  never be crowded out are the human and the auditor.

**Named risk:** `KiPolicy` holds `max_queue_depth` and `max_plan_age_revs`. If
those become ProcOps-tunable, the auditor can propose loosening the constraints
governing its own admission. The out-of-band application step is what keeps a
human in that loop.

**Proposed law:** *L2 — Governance is periodic and mandatory.* `enforced_by`: a
pure predicate over `(state_rev, last_audit_rev, interval)`. Everything else —
mandate text, auditor role spec, proposal schema, application ceremony — is
ProcOps and `roles/`.

**Sequencing:** this is auto-evolution, which canon §10.4 defers behind the
escalation tiers. Better-designed than what §10.4 feared, but still the thing.
**Do not build before R1.3 proves the loop halts.**

**Mechanical gotcha:** `test_llaw_cannot_be_extended_at_runtime` asserts
`len(llaw.LLAW) == 1`. Adding a second law makes it 2, and AGENTS.md §4 forbids
editing an acceptance test to match an implementation — an agent will correctly
open a `BLOCKED:` PR. The task brief must state that updating the arity
assertion is a spec change, not a fix.

### 7.4 Wall as single ingress

One Wall for all systems is right — a single audited ingress is why the Wall
exists, and duplicating it per subsystem gives N boundaries with N failure
modes. The consequence, cheap to design for now and expensive later: the Wall
becomes a queue with contention.

- **Ordering matters and is undefined.** Tolerable at one producer; at N it
  determines what PSY sees.
- **Rate asymmetry is a denial channel.** A sensor at 1000/sec and a human at
  1/hour share a bounded context. Without per-origin quotas the fast producer
  evicts the slow one — and the slow one is the human.
- **Per-origin reputation stops being optional.** Origin becomes the primary
  axis of trust; every producer needs a lineage.

Fix: origin-tagged admission with per-origin bounded budgets and **a floor
reserved for human drives that no other producer can consume.**

Deferred while there is one producer. Becomes blocking — together with the Wall
AEAD (§4.5) — the moment a second producer exists.

### 7.5 Scope boundary — separate projects

**Psymbiote is a separate project.** It is not a layer of PSYKI, not a
milestone, and nothing in this roadmap depends on it. It is named here once, and
only to prevent a future reader from inferring it into scope.

The general point that §7.4 rests on stands on its own: **any** second producer
on the Wall makes per-origin budgets and the Wall AEAD blocking. That is true of
a sensor, a scanner, a subsystem, or a second human, and it does not need a
named consumer to justify designing for it.

Also out of scope and previously recorded: the Spectral Neural Network, tied to
long-term PSYAI goals rather than to this repo.

---

## 8. Open items

| # | Item | Status |
|---|---|---|
| C1 | Model swap cost (canon §10.1) | Unmeasured. Falls out of the R1.3 PSY eval and R1.7. |
| C2 | State event fold ordering (canon §10.2) | Resolved in code; canon stale. **AMEND CANON.** |
| C3 | Retinue tool-versioning (canon §10.3) | Data gap, closes with R1.2. **AMEND CANON.** |
| C4 | Auto-evolution (canon §10.4) | Deferred behind R1.3. See §7.3. |
| N1 | PSY model binding | Recommendation in §7.1; decide after the eval. |
| N2 | Mnemos store | Open. Blocking for artifact-producing contracts. |
| N3 | Canon title, §8 model table, §5/I5 amendment | Human decisions. |
| N4 | Ablation harness | Required before any neuromorphic component ships (§7.2). |
| N5 | `History` definition | Lands in R1.3; do not defer past it. |

---

## 9. Seam with note 05

Note 05 covers keys, the external authority, liveness, succession, migration,
time anchoring, and offline operation. None of it is R1 work.

**What R1 must not foreclose:**

- Keep wall-clock time **out of KI** — it enters as stamped data at ingress, so
  I3 survives and note 05's time architecture stays possible.
- Keep crypto **out of the core** — it belongs in a `psyki/keys.py` that does not
  exist yet.
- Keep every new State field **scalar or enum** — note 05 adds `SuccessorStatus`,
  `LivenessState`, `OfflineState`, and they must be I4-clean and
  auditor-readable.
- Add `llaw_hash` to `StateSnapshot` and `Certificate` in R1.1 — it is the single
  field that makes the whole trust architecture attachable later.
- Carry the **ProcOps pin per contract at admission**, so a contract is judged
  under the charter that admitted it.

Those five are cheap now and expensive to retrofit. Everything else in note 05
can wait for its own design session.
