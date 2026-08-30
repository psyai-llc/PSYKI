# Note 09 — Consolidation

**Not canon.** Design input, per `docs/notes/readme.md`.

Everything designed across this session set, checked against the `dev` tree as
uploaded. Four parts: what the repo is now, what the architecture is, what does
not match, and what order to do it in.

No task specs here. This is the map.

---

# Part I — Repo state

67 files. `tests/test_invariants.py` runs green with zero failures.
`tests/test_repo_structure.py` requires pytest and could not be run in this
container. **`tools/test_tool_manifest.py` is red** (see M10).

## What landed since the last audit

The tool manifest work is in the tree — `tools/tool_manifest.json` and
`tools/sources.json`, both at schema 2.0.0, 12 tools, 11 toolsets, 49 sources.
Nine tool skills are present. That is real progress.

## What is misplaced

| Path in tree | Belongs at | Consequence |
|---|---|---|
| `tools/manifest.py` | `psyki/manifest.py` | **`tools/test_tool_manifest.py` fails**: `cannot import name 'manifest' from 'psyki'`. The module is not importable as designed. |
| `tools/test_tool_manifest.py` | `tests/` | Outside the test directory; CI will not collect it. |
| `skills/*.md` (flat) | `skills/tools/` | The skill oracle globs `skills/tools/*.md` and would find nothing. |

## What is missing

- **`skills/tools/net_fetch.md`, `process_run.md`, `llm_prompt.md`** — the three
  hand-written exemplars never landed. Nine of twelve tools have skills.
- **`procedures/`** — does not exist. `gate-chain.md` and
  `procedure-authoring.md` are not in the tree.
- **`style/gate_commands.json`** — does not exist. `skills/code-quality-gates.md`
  was deleted, and the five-language command matrix went with it. The content
  survives only in this session's output.
- **`tests/test_tool_skills.py`, `tests/test_procedures.py`** — neither oracle is
  in the tree.
- **`roles/emissary.md`** — still absent. The sole membrane has no specification.
- **`docs/notes/03` through `08`** — only notes 01 and 02 are committed.

## What survived that should not have

- **`skills/context-memory.md`** — marked for deletion. It instructs an agent to
  maintain `plan.md`, `scratchpad.md`, `decisions.md`. PSYKI has Log, Mnemos, and
  State, and an agent maintaining its own plan file is a second planner.
- **`config/agent.config.json`** — still the unported AgentAgent2 artifact. Names
  itself `AgentAgent2`, references `AGENTAGENT2.system.md` and three other paths
  that do not exist.

---

# Part II — The architecture, distilled

Everything decided across these sessions, in one place.

## 1. The four layers

| Layer | Question | Cardinality | Enforced by |
|---|---|---|---|
| **Tool** | What may be done | one per capability | the sandbox |
| **Skill** | How this tool behaves | one per tool | nothing |
| **Procedure** | How we do this *kind of work* | **many per skill** | nothing |
| **Style** | What the artifact may not be | one per language | a linter |

**Style is negative constraint; procedure is positive.** Style says *don't*,
procedure says *do it this way*. That is why style is machine-enforceable and
procedure is not: "never leave an unformatted file" is a predicate; "run the
gates in order and fix root causes" is a method.

A procedure is named for its **method**, never its tool. `inspect-workspace`,
not `fs_read-inspect` — a procedure named after a tool has collapsed into that
tool's skill, and twelve of those is a duplicate skills directory with no tuning.

## 2. Tools, sources, and trust classes

**Tools are capabilities; sources are endpoints.** Sources are arguments to
`net_fetch`, not capabilities. If sources were tools, "research against arXiv"
and "research against Crossref" would carry different signatures and cache two
byte-identical agents. Adding a source must be invisible to the signature.

**Two trust classes**, and the asymmetry is deliberate:

- **INTERNAL** — the meta-agents. Inside the server, under the invariants, with
  nothing but the invariants constraining them. Few tools.
- **PROVISIONED** — agents the server creates. Already double-filtered before
  they exist (PSY sets purpose, AgentAgent sets tools), bounded by a certificate,
  ended by a completion predicate, limited by a retry budget, revocable by KI.
  **The contract is the containment**, so the tool list can be wide.

`llm_prompt` is PROVISIONED-only. It is a tool a contracted agent uses to do its
job, not a role binding. Role→model assignment stays with TaskMaster under
`binding_strength`; nothing reachable by an agent can rebind PSY, the Emissary,
or AgentAgent.

**Trust class is part of task identity.** `META_READ` and `READ_ONLY` hold
identical tools; without the class in the signature the retinue would hand a
cached provisioned agent to a meta-agent request — a privilege crossing by cache
hit. Folded in via a reserved `@trust_class` key.

**Sources are classified, never excluded.** `enabled` (present but inert),
`auth` (honest), `constraints` (enforced at point of use). The MCP cannot assume
the scope of its own operation, so the registry accommodates rather than
pre-judges.

## 3. Toolsets are derived, not selected

Canon §3 read literally licenses bundles. Read as intended — *a tool is
provisioned only if the task necessitates it* — it is a **least-privilege rule**,
and least privilege is per-task. `BUILD_VERIFY` granting `fs_write` to a task
that only runs tests is an unnecessary capability arriving because a bundle was
convenient.

```
PSY:        task (intent, reason)          — never touches capability
AgentAgent: task → procedures              — the one judgement in the chain
            procedures → uses → tools      — derived
            tools → skills                 — one per tool, a lookup
```

One judgement call, everything downstream computed. A tool in a package that no
selected procedure declared is a bug an oracle can name.

**Cost:** the retinue caches on `toolset_signature`, and derived sets fragment.
Procedure combinations should cluster hard in practice, so the cache likely
survives as an empirical property rather than a guaranteed one. Measurable in
R1.3; do not assume either way.

## 4. Separation of powers

**PSY produces the reason. AgentAgent produces the package.** PSY never touches
agent features; AgentAgent never invents objectives. Neither can arrange its own
outcome.

**The divide is write permission to durable state.** Agents produce; meta-agents
commit. A provisioned agent writes only to per-contract ephemeral scope; nothing
it emits is durable until an authority takes it across.

**The tool does not split.** `fs_write` writes files; which paths exist is the
environment's answer. The server authorizes the userspace. Splitting the tool
would bake an environment property into a capability definition — the same
category error as sources-as-tools.

**Provisioning is by task, not by destination.** An agent is not "a server
agent"; it is an agent with a task, and the environment it lands in determines
what its tools reach.

## 5. The three userspaces

Singular **by construction**, not by rule. They are part of the server rather
than things it creates, so no mechanism would produce a second one.

| Role | Component | Mandate |
|---|---|---|
| **Director** | PSY | Decides what is to be done. |
| **Producer** | AgentAgent | Assembles what is needed. |
| **Conductor** | Emissary | Sole interface to everything outside. |

Each fans out to subagents without multiplying authority: a subagent writes only
to ephemeral scope, and nothing crosses back without a verdict.

**Boot constructs; KI recognizes.** KI is pure (I3) and cannot mount a
filesystem or spawn a process. Boot builds the three, binds each to an AK-signed
origin, then **seals** — after which a fourth construction attempt is a
detectable event rather than an accident of the boot script.

## 6. Artifact stores

Each meta-agent authors into its own store. **One writer per store**, so no
contention rules are needed.

| Author | Artifact | Store |
|---|---|---|
| Director | Agenda | agenda |
| Producer | Contracts | contract record |
| Conductor | Wall entries | Wall (via TasteTester) |

Artifact stores are **not State**. I11 governs State; the core remains its sole
writer. Authorship and write permission are different things.

**Each store needs its own admission check.** The Wall has TasteTester. The
agenda and contract record have nothing, and they are the two artifacts the
auditor reads to reconstruct intent against outcome.

**The Agenda's design tension is real:** it crosses into durable artifact, so I4
admits no prose — but an Agenda impoverished enough to be pure enum may be too
thin for an auditor to reconstruct intent months later. Rich enough to explain,
structured enough to stay lawful. That is the actual schema problem.

## 7. Lifecycle and lineage

```
Wall intent ──▶ agenda step ──▶ active contract ──▶ verdict ──▶ history
```

One place at a time. A satisfied intent stops entering PSY's context, so
completed work cannot keep influencing the agenda.

**Retire, do not erase.** Erasing traces collides with the Merkle-chained
ledger — a chain whose entries are removable is not a chain, and the
tamper-evidence the attestation design rests on goes with it. Retirement is a
**projection filter**: the record persists, State excludes it. Canon §6a already
defines State as a bounded projection, so this needs no new concept.

**Lineage extends `directive_id`** rather than adding a second correlation ID.
Path-shaped, so ancestry is a string operation and needs no index — which matters
because the auditor is ephemeral and draws its tools from a frozen mandate:

```
d:<hash8>              directive     ← Emissary, at Wall write
d:<hash8>/a3           agenda step   ← PSY
d:<hash8>/a3/c1        contract      ← AgentAgent
d:<hash8>/a3/c1/s2     subagent
d:<hash8>/a3/c1/v      verdict       ← KI
```

Retries are visible as `/c1`, `/c2` under one step. Hash is over the admitted
Wall bytes, so a duplicate intent is detectable rather than becoming two
directives racing.

**Minting authority is the forgery control.** Each component mints one segment
type and may only append to a path it was handed. AgentAgent never receives a
bare Wall entry, so it cannot fabricate lineage.

**Retirement becomes a predicate:** a step retires on a terminal verdict; a
directive retires when all its steps have. Partial satisfaction works correctly —
three of four done leaves only the fourth live, which a boolean flag could not
express.

**Gap:** a directive PSY judges unactionable generates no steps and never
retires. Needs a terminal non-verdict state — a nil step `d:<hash>/a0` carrying
an enum reason — or the choke I10 manages fills with items nothing can clear.

## 8. Verdict routing

The verdict returns through the **Emissary**, not AgentAgent. AgentAgent is
furthest from the original intent and incentivised to close contracts, so it is
the wrong judge of whether one succeeded. The Emissary is specialized in intent
and has no stake in completion — and routing through it restores the membrane
symmetry I4 already asserts.

**Canon §4.3 already says `agent → Emissary → Log`.** This is aligned; no change
needed.

Two constraints: the Emissary's assessment is a **judgement, not a certificate**
— KI still revokes (I9), or the self-certification problem has only moved. And
TasteTester checks schema and security, not fitness, so "refused because
malformed" and "refused because it missed the point" must stay distinguishable
in the record.

**TaskMaster tracks the lifecycle** — it already spans the whole thing. It should
**observe transitions, not author them.** A tracker that can move an item can
move one that should not. Witnesses are safer than movers.

## 9. Governance — L2

**Two independent triggers.** Rapid mutation and stagnation are different
failure modes and neither catches the other. Event delta (`state_rev`) is pure
and KI-evaluable in-loop. **Time delta must be evaluated by a supervisor outside
the loop** — its purpose is catching a stalled loop, and an in-loop trigger
cannot fire when the loop is the failure. A watchdog inside the process it
watches is not a watchdog.

**Time enters as stamped data at ingress**, never as an ambient call. KI reads a
value it was handed, so I3 holds and replay uses the recorded stamp.

**The mandate is a separate frozen constant in `llaw.py`**, folded into the same
digest — not the law statements, which are documentation and never interpolated
(I4). This generalizes: one frozen mandate per meta-agent role is the mechanism
for putting governance in front of a model without interpolating law.

**The auditor emits a typed proposal, not modules.** A report writing ProcOps
destroys I5. The proposal is a diff, runs the gate chain, gets a verdict, gets
logged; **application is out-of-band by the external authority with a pin
update.** I5 needs amending to distinguish "tunable" from "authored by the
server."

**Auditor independence is structural:** toolset from the frozen mandate, never
from PSY. Under I8 the planner partitions toolsets; PSY assigning them would let
PSY constrain the audit of PSY.

**Reports persist; the auditor is ephemeral.** Continuity lives in the artifact.
Prior reports are evidence, never instruction.

**Reserved admission lane.** An audit held under saturation never runs precisely
when most needed. The two things that must never be crowded out are the human
and the auditor.

**Urgent semantics.** Urgent buys priority and non-refusal. It does **not** mean
unvalidated — TasteTester still runs. And "enforced immediately" means recorded,
surfaced, and unignorable, **not self-applied**. Two readings of one word, and
the permissive one gets chosen under time pressure unless the law says which.

**Named risk:** `KiPolicy` holds `max_queue_depth` and `max_plan_age_revs`. If
those become ProcOps-tunable the auditor can propose loosening the constraints
governing its own admission. The out-of-band application step keeps a human in
that loop.

**Proposed law — L2: Governance is periodic and mandatory.** `enforced_by`: a
pure predicate over `(state_rev, last_audit_rev, interval)`. Everything else is
ProcOps and `roles/`.

## 10. Trust architecture

**The stack.** PSYAI root key signs: successor delegation (pre-signed,
escrowed, attenuable), migration grant, offline lease, LLAW amendment record,
liveness responses. Below the deployment boundary: TPM EK (per-deployment
identity, non-signing) → AK via credential activation → ephemeral leaf keys.

**Hash is not signature.** Every authority artifact is a signature over a
message, never a digest including a public key. Public keys are non-secret.

**Root rotation is two-phase.** Successor slot in platform config, null by
default; while null the root cannot change. POST validates five things —
algorithm allowlist, well-formedness, distinctness after canonicalization,
proof of possession, epoch monotonicity. A clean boot makes the successor
*eligible*; promotion needs a **separate rotation record signed by the current
root**. Without that separation, whoever writes platform config owns the
deployment after one reboot.

**PoP challenge is derived, not random**, because the holder is not present at
boot: domain separator ‖ EK ‖ current root ‖ algorithm ‖ successor key ‖ epoch.
`llaw_digest` deliberately excluded — it would force re-signing on every
amendment, and PoP proves possession, not authorization.

**Migration: two ceremonies, two-of-two.** The grant names `EK_old → EK_new`
explicitly, so it is a transfer and not a fork. Orderly (old hardware alive,
failure is clean reversion) and recovery (old hardware dead, failure means no
valid deployment). Recovery uses the **pre-signed escrowed delegation**, because
requiring a live authority signature fails exactly the scenario succession
exists for. EK binding is **identity**, not confinement.

**Liveness: response is life; time only measures silence.** A fresh server-issued
nonce, signed by the authority. Unauthenticated responses prove nothing — an
attacker could keep a dead authority looking alive and block succession forever.
A signature over an old nonce is a recording.

**Peer clock check** — one check among several, never the authenticator. Under
5 minutes flags `PEER_CLOCK_ANOMALY`; 5 or more breaks. **A broken check is
`LIVENESS_INCONCLUSIVE`, not `LIVENESS_MISSED`** — otherwise anyone who can add
five minutes of delay runs the countdown to completion by doing nothing.

**Time is a quorum, not a source.** Reducing time sources concentrates the attack
surface rather than shrinking it. One reading is attacker-choosable; agreement
across independent operators is not. **Every HTTPS response carries a Date
header**, so 35 enabled sources is 35 free witnesses. Three tiers: SIGNED
(Roughtime/RFC 3161, authoritative alone), QUORUM (min 5 witnesses, 30s spread,
median with outlier discard), OBSERVED (display only). Insufficient quorum yields
`UNANCHORED`, never a guess. **Elapsed time is always the monotonic TPM clock** —
quorum answers what o'clock it is and cannot measure duration.

**Dead-man switch.** `missed_checks` 0–5. Reset only by a valid signed response.
Held on `LIVENESS_INCONCLUSIVE`, while `UNANCHORED`, and under a valid offline
lease. Miss 1 and 2 notify; **miss 3 is the firm-date notice** naming the exact
date and remaining checks; miss 4 declares the authority dead.

**Grace pauses, never resets.** An acknowledgement buys +2 checks, once per
countdown, capped hard. If a notification response could reset, anyone with inbox
access could suspend succession indefinitely. **Invariant: no sequence of
acknowledgements without a signature ever prevents death.**

**Registration at first boot** records the authority key and contact endpoints.
Contact data is security-relevant and belongs in the pinned tier — whoever
rewrites it redirects every alert. Changes notify both old and new addresses.

**Offline: freeze by default, lease to operate.** An offline server that keeps
working **produces a fork** — signing under a charter it cannot verify, timestamped
by a clock it cannot verify. Freeze stops durable signed writes; log and read
surface stay alive. Transient loss is not offline mode; a threshold of missed
anchors precedes freeze.

The lease is **EK-bound, TPM-clock-expiring, and starts at issuance, not at going
offline.** Max ~30 days. Renewal is a **reconciliation ceremony** — anchor time,
verify LLAW and ProcOps against the authority, submit the offline ledger segment,
receive charter updates, and *only then* issue the next lease. **Atomic**: drop
mid-ceremony and the old lease runs to its original expiry. **No override on
expiry, ever** — an override makes the lease meaningless.

**LLAW amendment requires shutdown.** `CharterDrift` stops being runtime
detection and becomes physical impossibility; enforcement moves to boot, fail
closed. Costs accepted deliberately: clean drain, no emergency runtime override
ever, and friction as the feature. **Restart must verify the new digest against a
signed amendment record**, or the ceremony launders arbitrary changes.

**Per-contract ProcOps pin at admission**, so a contract is judged under the
charter that admitted it.

## 11. Model binding

PSY's profile is unusual: no tools, no dialogue, no prose, sealed context choked
by I10. Long context, tool use, multimodality, agentic coding are all worthless
to it. What remains is decomposition quality and structured-output reliability.

**Structured-output reliability comes from grammar-constrained decoding** built
from the §4.1 vocabulary, not from the model. Malformed emission becomes
unrepresentable rather than unlikely, I4 is enforced at the sampler, and the
failure mode that normally forces a larger model disappears. Small then becomes a
feature, since residency is a schedule and parameter count is a latency tax.

Phi-4-reasoning 14B MIT primary; Phi-4-mini 3.8B as the swap-cost tier; Qwen3.5
small as fallback. Not Gemma — bound to the Emissary where multimodal and
conversational ability earn their keep.

**Build the eval in R1.3 using the `NullPSY` slot.** Frozen directives with
Wall/State/History fixtures, scored on valid-emission rate under grammar, orphan
`directive_id` rate (I7), toolset partition correctness (I8), objective-count
stability across identical reruns. Yields the §10.1 swap-cost number as a side
effect and converts model choice from opinion to measurement.

**AgentAgent needs the highest reasoning of the three.** Under derived toolsets
it holds the only judgement call in the pipeline, and two commercial models
failed simpler composition work in this session.

## 12. Cortical layer

PSY does **not** see the whole server. I1 pins its context; §6a makes State a
bounded projection whose sources are unreadable through it. **State is the
thalamus.**

The v0 assignment was correct and R0 did not reject it — it demoted `neuro.py`
into `ki.py`, which is right since basal ganglia is action gating and KI is the
admit/refuse authority. But everything surviving is *subcortical*. The proposal
is the deferred half.

- **`DeltaContext`** (predictive coding) closes I10 — send prediction error, not
  State. **Catch:** the predictor is stateful across cycles, colliding with I1's
  byte-wise seal. Resolvable only if it lives *outside* PSY and the delta is
  computed on the way in. Must be designed that way from the start or I1 breaks
  quietly.
- **`consolidate()`** gives History a definition it lacks. Left alone History
  defaults to last-N verdicts — uniform recency, the weakest option.
- **`Neuromod` deferred hard.** It touches the replan counter, which is the
  entire halting argument.

**Every neuromorphic component ships with an ablation flag; one whose ablation
changes no metric was metaphor and gets deleted.** No ablation harness exists.

**This layer is code, not a model.** Delta over enums is still enums, so I4
holds, and the layer stays model-agnostic — one fused to Phi would be a liability.

## 13. Meta-agent prompts

**Monolithic, not composed.** A provisioned agent's prompt is a disposable build
artifact. PSY's prompt is a statement of what PSY *is* and must be coherent with
I1, I4, and I10 as a whole — composition gives you fragments each correct and an
assembly that is not.

Which makes `roles/` **governance surface**: hash-pinned, changed only under
review, so the server cannot author its own reasoning components' instructions.

**Monolithic about identity and method, not about tools.** Role files reference
tool skills rather than absorbing them, or a skill change diverges silently.

**KI has a role file and is code.** Keep it, marked explicitly as a specification
of a pure function with no model behind it, so nobody provisions a model against
it.

## 14. Wall as single ingress

One Wall for all systems. The consequence, cheap now and expensive later: it
becomes a queue with contention. Ordering is undefined and tolerable at one
producer. **Rate asymmetry is a denial channel** — a sensor at 1000/sec and a
human at 1/hour share a bounded context, and without per-origin quotas the fast
producer evicts the slow one. Per-origin reputation stops being optional.

Fix: origin-tagged admission, per-origin bounded budgets, **and a floor reserved
for human drives that no other producer can consume.**

## 15. Scope boundaries

**Psymbiote is a separate project.** Not a layer, not a milestone, nothing here
depends on it. Also out of scope: the Spectral Neural Network.

---

# Part III — Gap lists

## A. Designed here, absent from the repo

### A1. Structural

| # | Item |
|---|---|
| A1.1 | `psyki/manifest.py` — present but at `tools/manifest.py`, breaking its own test |
| A1.2 | `skills/tools/` directory — skills are flat in `skills/` |
| A1.3 | `skills/tools/net_fetch.md`, `process_run.md`, `llm_prompt.md` |
| A1.4 | `procedures/` — entire directory, including `gate-chain.md` and `procedure-authoring.md` |
| A1.5 | `style/gate_commands.json` — the 5×6 matrix, lost when `code-quality-gates.md` was deleted |
| A1.6 | `tests/test_tool_skills.py`, `tests/test_procedures.py` |
| A1.7 | `roles/emissary.md` |
| A1.8 | `docs/notes/03`–`08` |

### A2. Code that does not exist

| # | Item |
|---|---|
| A2.1 | `psyki/loop.py` — the orchestrator. Nothing runs the cycle. |
| A2.2 | `psyki/roles.py` — Protocol definitions; the seams every later milestone plugs into |
| A2.3 | `psyki/nulls.py` — NullEmissary, NullPSY, NullAgentAgent; permanent ablation controls |
| A2.4 | `psyki/server.py` — MCP surface |
| A2.5 | `psyki/boot.py` — boot sequence, POST, userspace construction |
| A2.6 | `psyki/keys.py` — crypto isolation layer |
| A2.7 | `psyki/origin.py` — origin identity, pure `verify()` |
| A2.8 | `psyki/userspace.py` — Role, Scope, Userspace, `construct()`, `seal()` |
| A2.9 | `psyki/agenda.py` — the agenda store |
| A2.10 | `psyki/mnemos.py` — `Log._evict()` calls a hook into nothing; `artifact_refs[]` points nowhere |
| A2.11 | Emissary, PSY, AgentAgent, TaskMaster — no implementation of any |
| A2.12 | `DeltaContext`, `consolidate()` — the cortical half |
| A2.13 | Ablation harness |
| A2.14 | Grammar-constrained decoding layer |

### A3. Type and field additions

| # | Item | Why |
|---|---|---|
| A3.1 | **`Event.origin`** | KI cannot tell who asked. Until it can, the divide is unenforceable in code. Retrofitting after KI has a test suite is expensive. |
| A3.2 | `StateSnapshot.llaw_hash` | LLAW is an island; I13 is enforced nowhere |
| A3.3 | `StateSnapshot.roles_hash` | `roles/` is an unguarded tier |
| A3.4 | `Certificate.llaw_hash` | Same drift check on the issued artifact |
| A3.5 | Stamped time field at ingress | Note 05's whole time architecture |
| A3.6 | `SuccessorStatus`, `LivenessState`, `OfflineState` enums | Trust architecture state, auditor-readable |
| A3.7 | `Reason.LAW_DRIFT`, `ROLE_DRIFT`, `UNKNOWN_ORIGIN` | Refusals must be distinguishable |
| A3.8 | Path-shaped `directive_id` | Lineage from intent to verdict |
| A3.9 | Nil agenda step (`/a0`) with enum reason | Unactionable directives otherwise never retire |
| A3.10 | `llaw.MANDATE` frozen constants, in the digest | Governance in a prompt without interpolating law |
| A3.11 | `SUCCESSOR_ALGS` in the digest | A law whose meaning depends on unpinned data |
| A3.12 | `__init__.__all__` += `llaw`, `manifest` | Both absent |

### A4. Data and configuration

| # | Item |
|---|---|
| A4.1 | Tool versions verified against the toolchain — every `verified_on` is null |
| A4.2 | `pending_import` — ~30 source ids with truncated endpoint records |
| A4.3 | Local model registry (params, licence, context, quant sizes, VRAM) |
| A4.4 | PSY eval fixtures |
| A4.5 | Negative-test corpus for TasteTester |
| A4.6 | Language scaffolds — five, ~60 files |
| A4.7 | Vendor adapters — OpenAI, Anthropic, Gemini schema translation |
| A4.8 | Five tier-1 procedures: `root-cause-repair`, `behaviour-first-tests`, `slice-and-verify`, `corpus-answer`, `inspect-workspace` |

## B. Present in the repo, undefined by this design

Not defects — genuinely undiscussed. Each is a decision nobody has made.

| # | Item | Question |
|---|---|---|
| B1 | **`corpus/`** — 18 files, PDFs and markdown, with `INDEX.md` | How is it exposed? R1.4 assumed read-only MCP exposure, but there is no loader, no index schema, no chunking policy, and no statement of whether corpus retrieval crosses the Emissary. Given I4, it must. |
| B2 | `config/mcp.servers.json` | Never examined. What servers, what trust, and how it relates to `sources.json`. |
| B3 | `style/style_core.md` + five language files | Never read against the design. `style_core` is cross-language principles, which is closer to a procedure than a style. |
| B4 | `psyki/escalation.py` | Tiers exist in code and canon §6, never reconciled with the retry budgets in procedures or the auditor's urgent lane. |
| B5 | `CapabilityFloor`, `Ceilings` in `types.py` | Never discussed. Ceilings appear in `StateSnapshot` twice (as limits and as usage). Relationship to per-origin Wall budgets is unexamined. |
| B6 | `CompletionPredicate`, `CompletionKind` | The mechanism that ends a contract. Never mapped to verdict routing or retirement. |
| B7 | `Gate` enum | Exists in types; relationship to `gate_commands.json` unestablished. |
| B8 | `EventKind` — 12 kinds | Needs extension for agenda transitions, audit triggers, and origin events. |
| B9 | `docs/v0/README-v0.md` | Partially superseded, partially the source of the cortical design. Status undeclared. |
| B10 | `AGENTS.md` | The working rules. Never checked against the four-layer model or the procedure oracle. |
| B11 | `.github/workflows/main.yml` | Three jobs. None run the new oracles. |
| B12 | `roles/taskmaster.md` — 2 lines | TaskMaster's role expanded considerably here (lifecycle tracking, model binding, observation-not-authorship). None of it is written down. |

## C. Misalignments and conflicting statements

| # | Conflict | Resolution |
|---|---|---|
| **C1** | Canon titled `# PSYKEY — Core Architecture`; repo, README, and every note say PSYKI | One word. **Human decision.** |
| **C2** | Canon §8 lists **VibeThinker-3B** for PSY — withdrawn on licence | Replace with Phi-4-reasoning primary, Phi-4-mini tier, Qwen3.5 fallback. **AMEND CANON.** |
| **C3** | Canon §3: *"A task is defined by its toolset… the tool manifest partitions the task-type space"* | Read literally this licenses bundles and contradicts least privilege. Intended reading is *a tool is provisioned only if the task necessitates it*. **AMEND CANON** — this is the largest single wording change. |
| **C4** | Canon §3 implies the manifest is the partition | Under the sources/capabilities split the manifest holds capabilities; toolsets are derived from procedures. **AMEND CANON.** |
| **C5** | Canon §10.2 open: state event ordering | Resolved in code — `fold()` is batched, one increment per fold. Canon stale. **AMEND CANON.** |
| **C6** | Canon §10.3 open: retinue tool-versioning | Closed. `toolset_signature()` takes name→version, manifest 2.0.0 supplies them, trust class is folded in. **AMEND CANON.** |
| **C7** | Canon §5 / I5: *"the server cannot author its charter"* | Blocks the L2 audit-proposal path. Must distinguish **tunable** from **authored by the server**. **AMEND CANON.** |
| **C8** | I11: *"the core is the sole writer of State"* vs. meta-agents authoring artifacts | Not a conflict once artifact stores ≠ State — but canon defines no artifact stores at all. **ADD TO CANON.** |
| **C9** | `config/agent.config.json` names `AgentAgent2`, references four nonexistent paths | Survives because the structural oracle checks paths referenced by *tests and CI*, not by *config*. **BLOCKING.** |
| **C10** | `tools/manifest.py` vs `from psyki import manifest` | Test is red. **BLOCKING, one move.** |
| **C11** | `skills/*.md` flat vs the oracle's `skills/tools/*.md` | Oracle finds nothing. **BLOCKING.** |
| **C12** | Nine tool skills present, twelve tools declared | `test_every_tool_has_a_skill` fails. |
| **C13** | `skills/context-memory.md` instructs an agent to keep `plan.md` | A second planner inside a system where PSY plans. **DELETE.** |
| **C14** | `llaw.LLAW` holds one law; L2 undecided | `test_llaw_cannot_be_extended_at_runtime` asserts `len == 1`. Adding a law makes it 2, and AGENTS.md §4 forbids editing an acceptance test to match an implementation — an agent will correctly open a `BLOCKED:` PR. **The brief must state that updating the arity is a spec change.** |
| **C15** | `roles/agentagent.md` is 62 lines including INTENT and PLAN | Canon §9 requires DESIGN→DELIVER. As-is it runs a second planner and addresses the user across a boundary only the Emissary may cross (I4). |
| **C16** | `roles/psy.md`, `roles/ki.md` are one line; `roles/taskmaster.md` two | Under monolithic role prompts these are the governance surface. |
| **C17** | `roles/emissary.md` does not exist | The sole membrane has no specification. |
| **C18** | `llaw` absent from `__init__.__all__`; `ki.py` does not import it; `StateSnapshot` has no `llaw_hash` | I13 is enforced nowhere. `llaw.voids()` is called by nothing. |
| **C19** | Wall cipher `DevCipher` is a refusing stub | Canon §9 requires XChaCha20-Poly1305 before a second Wall writer. |
| **C20** | Canon §1 diagram shows no agenda, active-contract, or history stores | The lifecycle designed here is invisible in canon. **ADD TO CANON.** |
| **C21** | `Event` has no origin field | The agent/meta-agent divide is unenforceable. |
| **C22** | `tools/test_tool_manifest.py` sits outside `tests/` | CI will not collect it. |

**Already aligned — no change needed.** Canon §4.3 already routes the verdict
`agent → Emissary → Log`, which is the Emissary-as-judge design. §6a already
defines State as a bounded projection, which is exactly what retirement needs.
§8 already states that AgentAgent authors design and tests while a smaller model
runs the implement loop — the offload pattern this session leaned on.

---

# Part IV — Roadmap

Five rounds. R1 unchanged in shape from note 03; R2–R4 are new and everything
in them was designed here.

```
R1.0  reconciliation                    EXCLUSIVE
        ├── R1.1  LLAW wiring          ─┐
        ├── R1.2  manifest relocation   ├─ parallel
        ├── R1.9  skills + procedures  ─┤
        └── R1.8  wall crypto          ─┘
        ▼
R1.3  THE SPINE — loop + null roles     ◀── KEYSTONE
        ├── R1.4  MCP server surface
        └── R1.5  Emissary ─▶ R1.6 PSY ─▶ R1.7 AgentAgent + TaskMaster
        ▼
R2    identity and the divide
R3    lifecycle and lineage
R4    governance
R5    trust architecture
```

## R1 — make the tree consistent and run the loop once

**R1.0 — reconciliation (exclusive).** Port or delete `config/agent.config.json`;
path-existence oracle first. Truncate `roles/agentagent.md` to DESIGN→DELIVER.
Write `roles/emissary.md`. Fill `psy.md`, `taskmaster.md`; mark `ki.md` as code.
Export `llaw` and `manifest`. Flag C1–C8 for human amendment.

**R1.1 — LLAW wiring.** `llaw_hash` into `StateSnapshot` and `Certificate`;
`bind_llaw()`; `Reason.LAW_DRIFT`; check llaw **before** procops in `admit()` and
`tick()`. Highest-value small fix in the tree.

**R1.2 — manifest relocation.** Move to `psyki/manifest.py`, test to `tests/`.
Verify green. Three file moves.

**R1.8 — wall crypto.** XChaCha20-Poly1305. Deferred while one producer;
blocking the moment there are two.

**R1.9 — skills and procedures.** `skills/tools/`, the three missing exemplars,
`procedures/`, `style/gate_commands.json`, both oracles, delete
`context-memory.md`. Then verify every gate command against a fixture — all 30
are currently unverified.

**R1.3 — the spine (keystone).** `loop.py`, `roles.py`, `nulls.py`, and a
definition for **History**, which is nowhere despite being one third of I1's
context tuple. Acceptance test asserts a `trace` matching §1 ordering, plus a
failure test proving escalation terminates. Nulls stay permanently as ablation
controls. Build the PSY eval here using the `NullPSY` slot.

**R1.4 — MCP server surface.** Read-only first. Load-bearing test: it *refuses*
to bind non-loopback without auth. Prerequisite: Cloudflare nameservers for
`psyai.cloud` — out of band, propagation delay, unblocked today. **Resolve B1
(corpus exposure) before this**, since corpus is what the read-only surface
serves.

**R1.5 → R1.7 — the three components.** Emissary first (test the
refuse-and-re-ask path hardest), then PSY with I1/I10 and grammar-constrained
decoding, then AgentAgent and TaskMaster with `binding_strength` and the §10.1
swap-cost measurement.

## R2 — identity and the divide

`keys.py` → `origin.py` → `userspace.py` → `boot.py` → the KI changes, in that
order. KI last because those are the changes that can break a green suite.

**`Event.origin` decided in R1 even if built here** (A3.1) — retrofitting after
KI has a suite around the current tuple is a change across every test.

Also: `roles/` pinning, `roles_hash`, the sandbox isolation mechanism, per-contract
tmp with a lifetime and a size bound.

## R3 — lifecycle and lineage

Path-shaped `directive_id`. Agenda store with its own admission check. Active
contract list. Retirement as a projection filter. The nil-step terminal state.
TaskMaster as observer. Mnemos, which unblocks artifact-producing contracts.

The Agenda schema — rich enough for an auditor, structured enough for I4 — is
the real design work in this round.

## R4 — governance

L2. Dual triggers with the out-of-loop supervisor. The frozen mandate constants.
Typed audit proposals. Reserved admission lane. Urgent-lane semantics. The
ProcOps per-contract pin.

**Do not start before R1.3 proves the loop halts.** This is auto-evolution, which
§10.4 defers behind the escalation tiers, and a self-modifying system whose
termination is undemonstrated is the one configuration where being wrong is
expensive.

## R5 — trust architecture

Everything in note 05. Registration, rotation, migration, liveness, dead-man
switch, offline leases, LLAW amendment ceremony.

**T1 (bootstrap/TOFU) has no proposed answer and everything here rests on it.**
Decide it before the round starts.

## What R1 must not foreclose

Cheap now, expensive to retrofit:

- Keep wall-clock time **out of KI** — it enters as stamped data at ingress.
- Keep crypto **out of the core** — `psyki/keys.py`, which does not exist yet.
- Keep every new State field **scalar or enum** — the trust architecture adds
  three, and they must be I4-clean and auditor-readable.
- Add `llaw_hash` in R1.1 — the one field that makes the whole trust
  architecture attachable later.
- Carry the **ProcOps pin per contract at admission**.
- Decide `Event.origin` now.

---

# Part V — Decisions waiting on you

| # | Decision | Blocks |
|---|---|---|
| 1 | Canon title, §8 model table, §3 wording, §5/I5, §10.2, §10.3 (C1–C8) | R1.0 |
| 2 | **T1 — bootstrap / TOFU.** How the first authority is established. | All of R5 |
| 3 | `Event.origin` — commit now or accept the retrofit | R2, cheap today |
| 4 | **B1 — corpus exposure.** No loader, no index schema, no statement on whether retrieval crosses the Emissary. | R1.4 |
| 5 | `type-casting` — archetype family, or delete | Nothing yet; will block AgentAgent design |
| 6 | Sandbox isolation mechanism — namespaces, bubblewrap, Cloud Run per-instance | R2, and it touches the deployment target |
| 7 | Whether the next law is L2-audit, L2-succession, or both | R4 |
| 8 | The four remaining meta-agent prompts — who writes them, and when | R1.0 |
