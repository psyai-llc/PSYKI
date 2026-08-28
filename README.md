
# **PSYKI** a self-governing, auto-evolving, meta-agentic MCP server

> Two narrow agents, one substrate. **Psy** builds structure in *time*. **Ki** builds structure in *events*.
> Neither is general. Their intersection is.

Provenance note: `github.com/mypsyai/AgentAgent2` was not reachable during authoring (private/unindexed).
This design is derived from the specification given in-conversation plus the neuromorphic assessment.
Hooks marked `# AA2:` are the intended attachment points for the AgentAgent2 nine-phase loop.

---

## 0. Invariants

These are load-bearing. Violating any one collapses the security or determinism argument.

| # | Invariant | Enforced by |
|---|---|---|
| I1 | Psy's context is **exactly** `(MCPState, MCPHistory, MCPAgenda)`. Nothing else is representable in its prompt. | `SealedContext.__post_init__` + `Psy.render()` reads only `self._ctx` |
| I2 | Ki's context is **exactly** `MCPState` (plus the immutable `Plan` it consumes). | `Ki.on_event` signature; no I/O inside |
| I3 | Ki's output is **deterministic**: `f(state, plan, event) → bytes` is a pure total function. | property test `test_determinism.py`; no RNG, no wall-clock, total tie-order |
| I4 | Any nondeterministic/generative work is a `SubagentSpec` *inside* an `Initiation`. Ki never calls a model. | no backend field on `Ki` |
| I5 | Operating Procedures are read-only and content-pinned. The server cannot author them. | `ProcOps.load()` returns frozen; hash checked each read |
| I6 | Wall entries reaching the Agenda have passed `taste_test`. Untasted bytes never touch Psy. | `Wall.append()` is the only writer; requires `TasteVerdict.ADMIT` |
| I7 | Wall directives contradicting ProcOps are **voided**, not negotiated. | `Agenda.compose()` conflict rule |
| I8 | Objectives with no traceable `directive_id` are rejected at plan validation. | `Plan.validate()` |

---

## 1. Neuromorphic assignment

The split is not stylistic. It is the cortico-subcortical division, and it buys real properties.

```
                 ┌───────────────────────────────────────────────┐
   OP PROCS ─────▶                  AGENDA                        │  drive state
   (genome,       │   compose(op_procs, wall) → directives         │  (hypothalamic
    read-only)    │   op_procs ≻ wall on conflict                  │   setpoint)
   WALL     ─────▶└────────────────────┬──────────────────────────┘
   (interoceptive                      │
    drive, taste-                      ▼
    tested)          ┌──────────────────────────────────────┐
                     │  PSY — cortex + hippocampus          │  TEMPORAL
   STATE ───────────▶│  ctx = (state, history, agenda)      │  clocked by op-proc
   HISTORY ─────────▶│  neuromod: DA/ACh/NE/5-HT            │  maintenance schedule
                     │  predictive-coding delta context     │
                     │  replay consolidation (sleep pass)   │
                     └──────────────┬───────────────────────┘
                                    │  PLAN  (the only channel;
                                    │         filtered user intent)
                                    ▼
                     ┌──────────────────────────────────────┐
   STATE ───────────▶│  KI — basal ganglia + brainstem      │  EVENTAL
   EVENTS ──────────▶│  ALIF gate → BG go/nogo/STN          │  no clock; fires on
                     │  SDR resource allocator              │  event cycles only
                     │  homeostatic token/time budget       │
                     │  DETERMINISTIC OUTPUT                │
                     └──────────────┬───────────────────────┘
                                    │  INITIATIONS
                                    ▼
                      subagents · existing agents · server settings
```

| Neuroanatomy | PSYKI component | Property bought |
|---|---|---|
| Genome / developmental constraint | `ProcOps` (read-only, hash-pinned) | system cannot rewrite its own charter |
| Interoceptive drive (hypothalamus) | `Wall` (encrypted token sequence) | user intent as a *drive*, not an instruction stream |
| Blood-brain barrier / gustatory aversion | `taste_test` | injection never becomes drive |
| Neocortex L2/3 (deliberation) | `Psy.plan()` | slow, expensive, generative, scheduled |
| Hippocampal SWR replay | `Psy.consolidate()` | history compaction w/ priority = \|reward\| + surprise |
| Neuromodulators (DA/ACh/NE/5-HT) | `Neuromod` | temperature, replan trigger, horizon, model tier |
| Basal ganglia direct/indirect | `BasalGangliaGate` go/nogo | objective selection, false-initiation suppression |
| Subthalamic nucleus (hyperdirect) | `stn_k` conflict term | global stop under hostile/ambiguous events |
| Thalamic relay + ALIF | `ALIFGate` | notification-storm collapse, refractory de-bounce |
| Synaptic scaling (Turrigiano) | `HomeostaticBudget` | token/time backpressure, no saturation |
| SDR overlap matching | `SDRRouter` | O(w) objective→resource allocation, bounded FP rate |
| Predictive coding (Rao–Ballard) | `DeltaContext` | Psy pays only for state *surprise*, not state |

**Why Ki must be deterministic:** the reflex arc has no cortex in it. Deterministic Ki is
auditable, replayable, and cannot be prompt-injected — because it never reads free text.
Its "fluidity" comes from being *event-clocked*, not from being stochastic.

---

## 2. Motive functions

Both agents are narrow because each optimizes one thing.

**Psy** — maximize agenda satisfaction subject to procedure:

```
maximize   Σ_d  w_d · satisfaction(d)          over admitted wall directives d
subject to ∀ d: complies(d, op_procs)          (else d is VOIDED, w_d := 0)
           replan cadence ∈ op_procs.schedule  (or NE-triggered emergency)
```

**Ki** — maximize objective throughput per unit cost:

```
maximize   Σ_o  completed(o) / (tokens(o) + λ·latency(o))
subject to homeostatic budget scale ∈ (0,1]
           BG gate: go_o − nogo_o − k·conflict ≥ θ
           determinism: output = pure_fn(state, plan, event)
```

These are **not** the same objective, and that is the point. Psy will happily spend
tokens to satisfy the Wall; Ki will refuse to. The tension is the governor.

---

## 3. Data flow, cycle by cycle

### 3.1 Psy cycle (temporal)
1. `tick(now)` — fires iff `op_procs.schedule` says so, **or** `neuromod.unexpected > θ_NE`.
2. Assemble `SealedContext(state, history, agenda)`. Nothing else exists.
3. `DeltaContext.forward(state)` → transmit only prediction error against Psy's own
   generative model of state. (Token economy; measured, see §6.)
4. Backend proposes `PlanDraft`. `Plan.validate()` rejects any objective without a live
   `directive_id`, and any action whose `kind` is not in `op_procs.permitted_actions`.
5. Emit `Plan` (versioned, content-hashed). Publish `plan/updated` notification.
6. `consolidate()` — SWR-style priority replay of history into semantic memory; prune.

### 3.2 Ki cycle (evental)
1. Event arrives on the bus (`resource/updated`, `agent/failed`, `plan/updated`,
   `threat/detected`, `budget/exhausted`, …).
2. `ALIFGate.stimulate(salience, now=event.ts)` — sub-threshold events integrate silently.
3. On fire: read `MCPState`; for each `Objective` in plan with `status ∈ {PENDING, STALLED}`,
   compute `go` (readiness × priority × staleness) and `nogo` (cost × risk × in-flight).
4. `BasalGangliaGate.select()` → objective index or `None` (global stop).
5. `SDRRouter.allocate()` → resources whose capability SDR overlaps the objective's
   requirement SDR at ≥ θ.
6. `HomeostaticBudget.admit()` → backpressure. Deny ⇒ defer, do not drop.
7. Emit `Initiation(objective_id, goals=[steps], allocations=[...], subagents=[...])`.
   Byte-identical for identical inputs.

---

## 4. Threat model

| Vector | Mitigation | Invariant |
|---|---|---|
| Prompt injection via tool output | Tool outputs enter `MCPState` as typed fields only; free text is `str` but never interpolated as instruction — Psy's renderer emits it inside a fenced, labelled `UNTRUSTED_OBSERVATION` block | I1 |
| Injection via Wall | `taste_test` at certified endpoint: origin signature, imperative-pattern screen, op-proc compliance, entropy/length anomaly | I6 |
| Self-modifying charter | ProcOps read-only + hash pin verified on every read; drift → `HALT` | I5 |
| Ki subversion | Ki reads no text. Its inputs are numeric/enum. Determinism test is a CI gate | I2, I3 |
| Runaway spend | Homeostatic budget + STN global stop on conflict spikes | — |
| Objective laundering (plan contains work nobody asked for) | Every objective carries `directive_id`; orphans rejected | I8 |

Immune analogy is load-bearing here: `taste_test` is **innate** (fast, signature-based,
stateless); `Wall.reputation` is **adaptive** (slow, per-origin, memory of past rejections).

---

## 5. Module map

```
psyki/
  types.py      # frozen schemas + canonical serialization
  neuro.py      # ALIF, BasalGangliaGate, Neuromod, SDRRouter, HomeostaticBudget,
                #   EligibilityCredit, DeltaContext, replay consolidation
  agenda.py     # ProcOps (read-only), Wall (append-only), taste_test, Agenda.compose
  psy.py        # SealedContext, Psy, PlannerBackend protocol, plan validation
  ki.py         # Ki (pure), Initiation emission, allocator
  bus.py        # AER-style async event bus
  server.py     # FastMCP surface
tests/
  test_determinism.py   # I3, I4
  test_agenda.py        # I5, I6, I7
```

---

## 6. Verification — falsifiable, per invariant

| Claim | Measurement | Success criterion |
|---|---|---|
| Ki is deterministic | 10k randomized (state, plan, event) triples, hash outputs twice | 100% byte-identical; CI gate |
| ALIF collapses storms | Poisson notif. stream + injected salient bursts | ≥50% fewer Ki wakes at ≤5% missed-salient |
| STN suppresses false initiations | conflict-heavy plan, ablate `stn_k=0` | false-initiation rate rises with STN off (else STN is metaphor — **delete it**) |
| SDR allocation ≥ embedding baseline | precision@1 on paraphrased capability queries | ≥ baseline precision at lower p99 latency |
| Delta context saves tokens | tokenizer count, full vs delta, 100-cycle session | ≥30% reduction at 100% reconstruction |
| Replay > random compaction | retrieval MRR on long-horizon task | priority > uniform > none |
| Taste test blocks injection | red-team corpus of wall payloads | 0 admits of imperative/op-proc-violating payloads |
| Homeostasis stabilizes spend | bursty load, variance of served rate | lower variance + no saturation vs token bucket |

**Every neuromorphic component ships with an ablation flag.** A component whose ablation
changes no metric was metaphor, and gets deleted. This is the rule that keeps the system honest.

---

## 7. Phased rollout

- **P0** — types + bus + determinism CI gate. Ki emits initiations against a hand-written plan.
- **P1** — ProcOps/Wall/taste_test/Agenda. Psy with `NullPlanner` (deterministic stub) end-to-end.
- **P2** — real `PlannerBackend`; SealedContext audit (assert prompt bytes ⊆ ctx bytes).
- **P3** — neuromod + BG + ALIF live; run every ablation.
- **P4** — delta context + replay consolidation; token accounting.
- **P5** — auto-evolution: Psy authors objectives that modify server settings via Ki; ProcOps
  still immutable. This is the only phase where the system edits itself, and it is gated on
  P0–P4 metrics holding.

---

## 8. Findings from the reference implementation

Two bugs surfaced on first execution. Both are worth recording because both are
cases where the neuroscience was *load-bearing*, not decorative.

**8.1 Buridan's ass in the basal-ganglia gate.** The first `BasalGangliaGate`
had direct, indirect, and hyperdirect pathways but no striatal cross-inhibition.
With N equal-priority objectives — the *normal* case for a procedure-derived
plan — every accumulator rose together, so the STN conflict term (runner-up
activation) never decayed, and the gate returned `None` forever. Ki emitted zero
initiations while reporting perfect health.

The fix is the anatomy: striatal collateral / GPe cross-inhibition, i.e. a leaky
competing accumulator (Usher & McClelland 2001). Lateral inhibition suppresses
the runner-up, conflict decays, the leader escapes. Biology also needs baseline
heterogeneity to break exact symmetry; Ki cannot use noise (invariant I3), so a
monotone `rank_prior` over the caller's total order substitutes. `_candidates`
therefore sorts by `(-priority, oid)` — the ordering is semantic, not incidental.

Measured, post-fix:

| Condition | `stn_k=2, lateral=.35` | ablate STN | ablate lateral |
|---|---|---|---|
| 7 tied candidates, no threat | select 0 | select 0 | **deadlock** |
| 7 tied, threat=0.9 | **stop** | select 0 | deadlock |
| net-negative evidence (go .3, nogo .9) | **stop** | — | — |

Both terms are load-bearing: ablating either changes behavior in a direction the
design predicted. Under §6's rule, both stay.

**8.2 The context seal fails closed, and should.** `SealedContext.assert_sealed`
initially tokenized on whitespace and flagged `surprise=0.000` — a formatted
literal from `render()` — as a seal breach. The correct fix was *not* to loosen
the audit but to tokenize on word boundaries and maintain `_RENDER_VOCAB` as an
explicit whitelist of every literal `render()` emits. Consequence: growing Psy's
context surface now requires editing a reviewed constant. That is the property
worth having.

**Reference run** (`python examples/e2e.py`, no model calls, `NullPlanner`):

- 4 wall submissions → 2 admitted, 2 rejected (`reject_imperative`, `reject_procs`);
  hostile origin reputation drops 0.5 → 0.1
- agenda: 7 live directives, chain verified
- Psy cycle 0 → plan `51158ac7…`, 7 objectives, all traceable
- Ki on `plan/updated` → 3 initiations (`max_parallel`), 6 subagent specs
- 40 low-salience events → 1 wake, 19 refractory drops (**98.1% wake reduction**
  vs. the ungated arm over a 1000-event storm)
- outcome → DA `+0.143`, horizon extends 4200 → 4302.9 s via 5-HT
- `threat/detected` → reflexive quench, **0 subagents spawned**, thresholds doubled
- determinism: `canon(Ki_a) == canon(Ki_b)` across 200 randomized worlds

## 9. Known gaps

- `Wall._stream` is a blake2b keystream XOR — integrity comes from the hash
  chain, not from an AEAD. Replace with XChaCha20-Poly1305 before it faces an
  adversary who can request many encryptions. Marked in the docstring.
- `NullPlanner` emits one AUDIT+COLLECT objective per directive. It exists to
  make the system testable with zero model calls and to serve as the control arm
  for planner ablations — it is not a planner.
- The taste test's innate tier is regex-based and will be evaded. The adaptive
  tier (per-origin reputation) is what degrades a persistent attacker; treat the
  regex list as a speed bump with telemetry, not a boundary.
- No eligibility-trace *task* yet: `EligibilityCredit` is wired and accumulating,
  but §6's "priority replay > uniform" claim is untested until a long-horizon
  retrieval benchmark exists. Until then it is extrapolation, not result.
