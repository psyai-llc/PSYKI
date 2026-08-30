# Note 03 — R1 assessment and roadmap

**Not canon.** Design input, per `docs/notes/readme.md`. Where this and
`docs/PSYKI_CORE.md` disagree, canon wins. Items marked **AMEND CANON** are
proposals for a human edit to canon, not statements of fact about it.

**Basis:** the `dev` tree as of the R0 push (`cb84645..fd6fcff`, six commits),
plus the session log for that run.

---

## 1. Where we are

R0 did what it was asked. The tree is coherent, it imports, and it has a real
acceptance oracle for the first time.

| | |
|---|---|
| runtime modules | 10 (`core, escalation, ki, llaw, log, procops, retinue, tastetester, types, wall`) |
| runtime lines | ~1,100 |
| invariant suite | 36/36 green, zero dependencies |
| structural oracle | 14/14 green |
| CI jobs | 3 (structure, I3 determinism, full suite) |
| canon | 363 lines, 13 invariants, single file |

Against the state recorded before R0 — twelve invariants of which six were
aspirational, zero CI-gated, no `.github/` — this is a large move. The
deterministic half of the architecture is now largely built and largely proven.

**And that is the whole problem.** Every module is tested in isolation and
**none of them have ever run together.** There is no orchestrator, no server
surface, and none of the three reasoning components exist. The system has a
skeleton with no spine.

### 1.1 Canon vs. tree

| Canon component | Kind | Status |
|---|---|---|
| Emissary | model | **absent** — no module, no role spec |
| PSY | model | **absent** — no module, one-line role stub |
| AgentAgent | model | **absent as code**; role spec present but unported (§2.6) |
| TaskMaster | model | **absent as code**; role spec present |
| KI | code | built, tested. Does not consult LLAW (§2.3) |
| TasteTester | code | built, tested |
| State / core | code | built, tested |
| Wall | code | built; **cipher is a refusing stub** (§2.5) |
| Log | code | built, tested; mnemos is a callback with no store behind it |
| Retinue | code | built, tested |
| LLAW | code | built, tested, **and wired to nothing** (§2.3) |
| ProcOps | code | built, tested |
| Mnemos | code | **absent** — hook only |
| MCP server surface | code | **absent** — the stub was deleted in R0 |

### 1.2 Invariant coverage

Named and behaviourally tested: I2, I3, I4, I6, I8, I11, I12.
Behaviourally tested without an ID assertion: I5, I7, I9, I13.
**Zero implementation and zero tests: I1** (PSY's sealed context) **and I10**
(dynamic context choke). Both depend on PSY, which does not exist. They are the
two invariants that cannot be closed by wiring alone.

### 1.3 Continuity with the prior AgentAgent2 roadmap

The M0–M6 roadmap written for `mypsyai/AgentAgent2` is **superseded**.
AgentAgent2 is no longer a peer server to be stood up separately; canon §9
absorbed it into PSYKI as a role specification plus a skills/style/tools port.
Its M1 goal — a read-only MCP server behind Cloudflare — survives, but as
R1.4 of *this* repo, exposing PSYKI resources rather than an AgentAgent2 corpus.

One item from that roadmap is still live and still unblocked: moving
`psyai.cloud` nameservers to Cloudflare. It is the only step with propagation
delay, it commits to no cloud, and it is a prerequisite for R1.4. Do it out of
band; it is not on the critical path of anything else here.

---

## 2. Defects and drift

Numbered for reference in task specs below. Each has been verified against the
tree, not inferred.

### 2.1 `config/` and `tools/` are unported AgentAgent2 artifacts — **BLOCKING**

`config/agent.config.json` names itself `AgentAgent2`, points at
`system_prompt_file: AGENTAGENT2.system.md`, and declares four paths that do not
exist in this tree: `AGENTAGENT2.system.md`, `design/schemas/`,
`templates/agent_project_scaffold/`, `outputs/`.

This survived R0 because `tests/test_repo_structure.py` checks paths referenced
by *tests and CI*, not paths referenced by *config*. It is the exact failure
AGENTS.md §3 exists to prevent, one layer out of the oracle's reach.

### 2.2 The tool manifest is the missing half of a mechanism that already works

Canon §3: *"the tool manifest partitions the task-type space."* Canon §10.3
flags tool-versioning in the retinue signature as open.

But `retinue.toolset_signature()` already takes `dict[name → version]` and
`test_tool_version_changes_signature` already passes. The mechanism is built and
proven. What is missing is the **data**: `tools/tool_manifest.json` carries 19
AgentAgent2 tool definitions with no versions and no signature grouping.

So §10.3 is not an open design question. It is an unported file. Closing it is
a data migration, not a research task.

### 2.3 LLAW is an island — **BLOCKING for I13**

`psyki/llaw.py` is complete, well-argued, and covered by nine tests. It is also
imported by **nothing but the test file**.

Concretely:
- `StateSnapshot` has `procops_hash` and no `llaw_hash`, though `llaw.py`'s own
  docstring says the digest exists *"for embedding in State and certificates."*
- `ki.admit()` refuses on `CHARTER_DRIFT` by comparing `procops_hash`. It never
  checks the tier above it.
- `llaw` is absent from `psyki/__init__.py`'s `__all__`.

I13 says LLAW outranks ProcOps. Today that ranking exists in `llaw.voids()`,
which no runtime path calls. The law is enforceable in principle and enforced
nowhere. This is the highest-value small fix in the tree.

### 2.4 Mnemos has a hook and no store

`Log._evict()` calls an optional `self._mnemos(dropped)` callback. Canon §7
gives Mnemos real duties: unbounded artifact storage, explicit-request-only
retrieval, re-entry through the Emissary as enum. None of that exists. The
`artifact_refs[]` field on `VerdictRecord` points into a store that isn't there.

### 2.5 Wall cipher is a refusing stub

`DevCipher` correctly refuses to run without an explicit insecurity
acknowledgement — good design, and `test_dev_cipher_refuses_by_default` proves
it. But canon §9 requires XChaCha20-Poly1305 before the Wall takes a second
writer, and no real AEAD exists. Note 01 deferred multi-producer work on the
grounds that no second producer exists yet. That reasoning holds; this stays
deferred, but it must land **before** any sensor, scanner, or subsystem writes.

### 2.6 `roles/agentagent.md` is untruncated

Canon §9 specifies the ported system prompt is **truncated — enters at DESIGN,
exits at DELIVER**, because INTENT and PLAN are satisfied externally by the
Contract and DEBRIEF becomes a boundary crossing.

The file in the tree is the full nine-phase AgentAgent2 prompt, INTENT through
DEBRIEF, with its own approval gates, its own `agentagent_log.md`, and its own
user-communication protocol. Dropped in as-is, it would run a second planning
loop inside a system whose whole point is that PSY does the planning, and it
would talk to the user directly across a boundary that only the Emissary may
cross (I4).

`roles/ki.md` and `roles/psy.md` are one-line stubs. `roles/emissary.md` does
not exist — the sole membrane has no specification.

### 2.7 Canon §8 model table is stale

Lists VibeThinker-3B as the PSY candidate. That binding was withdrawn on
licence incompatibility; it is retained only as a fine-tune design concept.
Leaving it in canon invites an agent to bind it. **AMEND CANON.**

### 2.8 Canon is titled `# PSYKEY`

Flagged at the end of R0 and left for a human. Still open. One word.

---

## 3. R1 roadmap

### 3.1 Sequencing

```
R1.0  reconciliation            EXCLUSIVE — touches canon + every config path
        │
        ├── R1.1  LLAW wiring          ─┐
        ├── R1.2  tool manifest port    ├─ parallel, independent
        ├── R1.8  wall crypto           ─┘  (R1.8 optional in R1)
        │
        ▼
R1.3  the spine (loop + null roles)     ← keystone; everything below waits
        │
        ├── R1.4  MCP server surface
        └── R1.5  Emissary  ──▶  R1.6  PSY  ──▶  R1.7  AgentAgent + TaskMaster
```

**R1.0 is EXCLUSIVE.** It edits canon and rewrites config paths that other tasks
read. No parallel work starts until it merges. This is the same constraint that
governed R0.3; it was caught before execution last time and must be again.

**R1.3 is the keystone.** Do not start R1.5 before it merges.

### 3.2 The argument for R1.3 before any model work

The obvious next move is to build the Emissary, because nothing is callable
without it. That is a trap. Three reasoning components on top of a substrate
that has never executed as a unit means debugging model behaviour and plumbing
at the same time, with no way to tell which is lying.

Instead: **wire the deterministic spine end to end with the reasoning components
stubbed to fixed enums.** `NullEmissary` returns a canned `Directive`.
`NullPSY` returns one objective with one task. `NullAgentAgent` returns a
contract that immediately reports `FULFILLED`.

If that loop runs — Wall append → fold → PSY → KI admit → certify → contract →
verdict → Emissary → Log → KI revoke → retinue return — then every real model
that follows is a **single-component swap against a proven harness**, and any
failure is unambiguously attributable to that model.

This is the `NullPlanner` ablation-control pattern canon §9 said to keep. It is
also the only thing in this roadmap that produces a running system, and it is
achievable from what is already built. No new subsystems required.

---

## 4. Task specifications

Instruction-grade. Each states its acceptance test first, per AGENTS.md §4:
**write the test, run it, confirm it fails, then implement.** A test that passes
before the change is a defect in the task.

---

### R1.0 — Reconciliation (EXCLUSIVE)

**Done when:** `python tests/test_invariants.py && python -m pytest tests/ -v`
→ exit 0, and no tracked file references a nonexistent path.

**R1.0-a — Path oracle.** Add `test_config_paths_exist` to
`tests/test_repo_structure.py`: parse every `.json` under `config/` and
`tools/`, collect every value that looks like a repo-relative path (contains
`/` or ends in a known suffix), assert each resolves. Run it. It must fail on
the four paths in §2.1. This test is the reason the rest of R1.0 is safe.

**R1.0-b — Port or delete `config/agent.config.json`.** Rewrite as
`config/psyki.config.json` describing *this* system: gate chain, eval
thresholds (0.90 / safety 1.0), escalation budgets matching
`escalation.Budgets`, ceilings matching `types.Ceilings`. Drop
`system_prompt_file`, `logging.*` (the Log module owns that), and every path in
§2.1. If a key has no consumer in `psyki/`, delete it rather than port it —
AGENTS.md §2.

**R1.0-c — Truncate `roles/agentagent.md`.** Cut INTENT and PLAN entirely. Cut
"Communication with the User" — AgentAgent does not address the user; I4 forbids
it. Convert DEBRIEF from a terminal phase to a `VerdictRecord` emission. Retain
DESIGN → SCAFFOLD → IMPLEMENT → VERIFY → EVALUATE → DELIVER, the quality bar,
style bindings, and the subagent section (TaskMaster lives there).

**R1.0-d — Write `roles/emissary.md`.** The sole membrane has no spec and it is
the security boundary (canon §1: *"the enum protocol is the security boundary,
not the model"*). Must state: the three vocabularies from §4.1 verbatim; the
hard refuse-and-re-ask rule; that it converts in **both** directions; and that
it never forwards prose across any internal boundary.

**R1.0-e — Fill `roles/psy.md` and `roles/ki.md`.** PSY: context is exactly
`(Wall, State, History)`, output is target → objectives → tasks, every objective
carries a `directive_id`. KI: this file should say KI is **code, not a model**,
and point at `psyki/ki.py`. A role file for a deterministic component invites
someone to bind a model to it.

**R1.0-f — Export `llaw`.** Add to `psyki/__init__.py`'s `__all__`.

**R1.0-g — Canon amendments (human).** §2.7 model table; §2.8 title. Flag, do
not edit — AGENTS.md §5.

---

### R1.1 — Make L1 enforceable

**Acceptance test first**, `tests/test_invariants.py`:

```
test_certificate_carries_llaw_hash
    admit() a valid task; assert ruling.certificate.llaw_hash == llaw.llaw_hash()

test_ki_refuses_on_llaw_drift
    build a snapshot whose llaw_hash differs from the live pin;
    assert admit() returns REFUSE / Reason.LAW_DRIFT

test_ki_revokes_live_certificate_on_llaw_drift
    tick() a live cert against a drifted snapshot; assert REVOKE

test_llaw_outranks_procops_at_runtime
    a snapshot with a matching procops_hash and a drifted llaw_hash
    must still be refused — the lower tier passing does not rescue it
```

All four must fail before implementation.

**Implementation.** Add `llaw_hash: str` to `StateSnapshot` and to
`Certificate`. `ServerCore.bind_llaw()` alongside `bind_procops()`, set once at
boot from `llaw.verify()`. Add `Reason.LAW_DRIFT`. In `ki.admit()`, check
`llaw_hash` **before** `procops_hash` — the order encodes the hierarchy and the
fourth test is what proves the order is real. Same check in `ki.tick()`. Feed
`llaw_hash` into `mint_certificate_id()`.

**Watch:** `ki.py` must not `import psyki.llaw` at module scope if that would
put a non-pure call inside KI. It does not — `llaw.verify()` is pure, no RNG, no
clock — but the I3 CI grep is a substring match on import lines. Verify the
determinism job still passes before opening the PR.

---

### R1.2 — Tool manifest as task-type partition

**Acceptance test first**, `tests/test_tool_manifest.py`:

```
test_every_tool_has_a_version
test_toolsets_are_named_and_disjoint_by_signature
    for each declared toolset, retinue.toolset_signature(tools) is distinct

test_signature_changes_when_a_tool_version_bumps
    load manifest, bump one version in memory, assert signature differs

test_manifest_tools_resolve_to_declared_permissions
    every tool named in a toolset exists in the tools list
```

**Implementation.** Rewrite `tools/tool_manifest.json`:

1. Every tool gains `"version": "<semver>"`. Start everything at `1.0.0`.
2. Add a top-level `"toolsets"` array. Each entry: `name`, `tools[]` (names),
   `purpose`, `safety_ceiling`. These are the task-type partitions — a task
   *is* one of these plus a purpose (canon §3).
3. Initial toolsets, derived from the existing 19 tools:
   `READ_ONLY` (read_file, list_dir, grep_search, glob_search),
   `CODE_EDIT` (+ write_file, edit_file, vcs_*),
   `BUILD_VERIFY` (+ run_shell, run_tests, run_linters, pkg_install),
   `RESEARCH` (read-only + web_search, web_fetch),
   `ORCHESTRATE` (spawn_subagent, message_subagent, artifact_*).
4. Add `psyki/manifest.py` — a loader that returns `dict[name → version]` for a
   named toolset, feeding `retinue.toolset_signature()` directly.

This closes canon §10.3. Note in the PR that it was a data gap, not a design gap.

---

### R1.3 — The spine (KEYSTONE)

**Acceptance test first**, `tests/test_loop.py`. One test that is the whole
milestone:

```
test_one_full_cycle_with_null_reasoning
    core = ServerCore(); core.bind_procops(...); core.bind_llaw(...)
    loop = Loop(core, wall, log, retinue,
                emissary=NullEmissary(), psy=NullPSY(), agentagent=NullAgentAgent())
    outcome = loop.run_once("create a file")   # NL in

    assert outcome.verdict is Verdict.FULFILLED
    assert outcome.certificate_id not in core.snapshot().certificates_outstanding  # revoked
    assert log.head == 1
    assert wall.verify_chain()
    assert loop.trace == [EMISSARY_IN, TASTE, WALL, FOLD, PSY, KI_ADMIT,
                          CERTIFY, AGENTAGENT, CONTRACT, EXECUTE,
                          EMISSARY_OUT, LOG, KI_REVOKE]
```

The `trace` assertion is doing real work: it proves the cycle ran in canon §1's
order, not that it merely produced the right answer.

Second test, equally required:

```
test_failed_contract_escalates_and_terminates
    NullAgentAgent configured to always FAILED_GATE.
    assert the loop halts, assert final tier is SURFACE,
    assert retries then replans were consumed in that order.
```

Both must fail before implementation.

**Implementation.** `psyki/loop.py`:

```
Loop.run_once(nl_input) ->
    directive  = emissary.ingress(nl_input)        # NL → Directive (enum)
    tasting    = tastetester.taste(directive, charter)
                 → refuse ⇒ SURFACE, done
    wall.append(directive)
    core.emit(WALL_APPENDED); core.fold()
    plan       = psy.plan(wall.read(), core.snapshot(), history)
    for task in plan.tasks:
        ruling = ki.admit(snapshot, task, plan_procops_hash, plan_wall_rev)
                 → HOLD ⇒ requeue; REFUSE ⇒ escalate
        init   = ki.certify(ruling, task)
        core.emit(CERT_ISSUED); core.fold()
        contract = agentagent.design(init, retinue, manifest)
        verdict  = execute(contract)               # null: returns canned
        record   = emissary.egress(verdict)        # → VerdictRecord
        esc      = escalation.escalate(record.verdict, ledger)
        log.append(record); core.emit(LOG_APPENDED)
        ki.revoke(init.certificate, snapshot); core.emit(CERT_REVOKED)
        core.fold()
```

Also in this milestone:

- `psyki/roles.py` — `Protocol` definitions for `Emissary`, `PSY`,
  `AgentAgent`. These are the seams every later milestone plugs into. Getting
  the signatures right here is most of R1.5–R1.7's design work, done once.
- `psyki/nulls.py` — the three null implementations. Keep them permanently as
  ablation controls; they are how you prove a regression is in the model rather
  than the loop.
- `History` — currently nowhere. PSY's context is `(Wall, State, History)` per
  I1. Define it now as a bounded tuple of `VerdictRecord` derived from the Log,
  even though NullPSY ignores it. Defining it late means retrofitting I1.

**Judgment call to record:** the loop is single-threaded. Concurrency is a
later problem and adding it now would put the one structure KI's determinism
depends on back under concurrent mutation.

---

### R1.4 — MCP server surface

**Depends on R1.3.** There is nothing to expose until the loop runs.

**Acceptance test first:** start the server on loopback, call
`tools/list` over stdio, assert the advertised tools match the manifest
toolsets; call one read-only tool and assert the response shape. Then assert
the server **refuses to bind a non-loopback address without explicit auth
configuration** and exits nonzero. That refusal test is the one that matters.

**Implementation.** `psyki/server.py`. Fail closed on bind. Read-only surface
first: expose State (the bounded projection — safe by construction, canon §6a),
the manifest, and the canon documents. Write paths come after the read surface
is proven. ADR-006 from AgentAgent2 applies directly.

Deployment target `mcp.psyai.cloud` via Cloud Run behind Cloudflare. The
nameserver move (§1.3) must be done before this milestone can be exercised
end to end.

---

### R1.5 — Emissary (first real model)

**Depends on R1.3.** Swap `NullEmissary` for a Gemma binding. The R1.3 trace
test must still pass unchanged — that is the point of having built it.

**Acceptance test first:** the refusal path, not the happy path. Feed inputs
that cannot be encoded in the §4.1 vocabulary and assert the Emissary
**refuses and re-asks** rather than approximating. Canon calls a silently lossy
Emissary *"the worst failure this design admits, because nothing downstream can
detect it."* Test that failure mode first and hardest. Include an
injection-shaped input and assert nothing but enum crosses the boundary.

---

### R1.6 — PSY, and the two untested invariants

**Depends on R1.5.** This is where I1 and I10 finally get implementations.

- **I1** — sealed context, audited byte-wise. PSY receives exactly
  `(Wall, State, History)` and the audit is a byte comparison, not a review.
  Port the whitespace→word-boundary fix from v0 (canon §9).
- **I10** — dynamic context choke ≤ server capacity, for both PSY and KI.
  Neither the field nor the enforcement exists today.

Model binding is open pending §2.7. Do not bind VibeThinker.

---

### R1.7 — AgentAgent, TaskMaster, and `binding_strength`

**Depends on R1.6.** The user goal that motivates the whole roadmap —
AgentAgent running inside PSYKI on on-device models, off the pay-per-token
scheme — lands here.

Carry in `binding_strength` from note 02: local weights bind cryptographically,
hosted APIs can only be *asserted*, and asserted-only models are barred from
sensitive capability tiers. On-device makes this more important, not less: it
is the field that says the loaded model is the model that was contracted.

Canon §8's division is what makes local models viable — AgentAgent authors the
design and the tests, a smaller model runs the implement loop until the oracle
says yes. Preserve that split; it is the token argument.

**Measure model swap cost in this milestone.** Canon §10.1 has it open and
unmeasured, and it decides whether an objective loop takes seconds or minutes.
It is cheap to measure once two bindings exist and expensive to discover late.

---

### R1.8 — Wall AEAD (parallel, optional in R1)

Replace `DevCipher` with XChaCha20-Poly1305 per canon §9. Independent of
everything above; can run at any point after R1.0.

**Hard constraint:** this must land before the Wall takes a second writer. Note
01's deferral of per-origin budgets is sound while the only producer is one
human. The moment a sensor, scanner, or subsystem writes, both §2.5 and note
01's per-origin quotas become blocking, and the human channel needs its
reserved floor before it can be crowded out.

---

## 5. Open — carried and new

| # | Item | Status |
|---|---|---|
| C1 | Model swap cost (canon §10.1) | Open. Measure in R1.7. |
| C2 | State event fold ordering mid-tick (canon §10.2) | Partly resolved in code — `fold()` batches, one increment, mid-tick events queue for the next fold. Canon §10.2 should be updated to match. **AMEND CANON.** |
| C3 | Retinue tool-versioning (canon §10.3) | Not a design question — a data gap. Closes with R1.2. **AMEND CANON.** |
| C4 | Auto-evolution (canon §10.4) | Deferred. LLAW unblocks it in principle; do not touch until R1.3 proves the loop halts in practice. |
| N1 | PSY model binding | Open — §2.7. |
| N2 | Mnemos store | Open — §2.4. Not blocking R1.3; blocking for artifact-producing contracts. |
| N3 | What PSYAI verifies before issuing a model cert | Open. FLAG-A gave it an owner; it has no procedure. Blocks R1.7's `binding_strength`. |
| N4 | Canon title `PSYKEY` vs `PSYKI` | Open — one word, human. |

---

## 6. What I would do first

1. **Move the nameservers to Cloudflare.** Out of band, propagation delay, no
   cloud commitment, unblocks R1.4.
2. **R1.0** — one exclusive pass. Nothing else runs alongside it.
3. **R1.1 and R1.2 in parallel** — both small, both close open canon items,
   both independent.
4. **R1.3** — the keystone, and the first point at which PSYKI is a running
   system rather than a set of proven parts.
