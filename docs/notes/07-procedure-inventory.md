# Note 07 — Task inventory and the procedure layer

**Not canon.** Design input, per `docs/notes/readme.md`.

Three questions answered here: what the service is actually asked to do, which
of those need a procedure rather than a skill alone, and what makes a procedure
necessary.

---

## 1. The four layers

| Layer | Question it answers | Cardinality | Enforced by |
|---|---|---|---|
| **Tool** | What may be done | one per capability | the sandbox |
| **Skill** | How this tool behaves | one per tool | nothing |
| **Procedure** | How we do this *kind of work* | **many per skill** | nothing |
| **Style** | What the artifact may not be | one per language | a linter |

**Style is negative constraint. Procedure is positive constraint.** Style says
*don't*; procedure says *do it this way*. That is also why style is machine-
enforceable and procedure is not — "never leave an unformatted file" is a
predicate; "run the gates in this order and fix root causes" is a method.

The consequence for naming: **a procedure is named for its method, not its
tool.** `inspect-workspace`, not `fs_read-inspect`. A procedure named after a
tool has collapsed into the skill for that tool, and twelve of those would give
you a second skills directory with no tuning knob.

---

## 2. What necessitates a procedure

A skill describes a tool. It cannot describe how to do *work*, because the same
tool serves many methods. The question is when a skill alone leaves too much
open.

**A skill needs a procedure when its correct use is underdetermined by the tool
and a wrong use does not announce itself.**

Five triggers. Any one is sufficient; none means the skill stands alone.

| # | Trigger | Why the skill is not enough |
|---|---|---|
| **D1** | **Order dependence** | The steps must happen in sequence, and the wrong order still produces output. Nothing in the tool enforces the sequence. |
| **D2** | **Tempting shortcut** | A faster wrong path exists and looks like success. Patching a symptom passes the same gates as fixing a cause, until it doesn't. |
| **D3** | **Silent failure** | Being wrong looks exactly like being right. A single unverified source, a test asserting nothing, a scan that exits 0 because it found nothing to scan. |
| **D4** | **Downstream contract** | The output feeds a schema, another agent, or the record. Format drift breaks a consumer that is not present to complain. |
| **D5** | **Multi-agent consistency** | Many agents do this work and their outputs are compared. Individually-optimal but mutually inconsistent is worse than uniformly adequate. |

**The test for a proposed procedure:** name the trigger. If you cannot, the
skill already covers it and the procedure is ceremony.

---

## 3. Task inventory

What a meta-agentic build service is actually asked for, in rough frequency
order. Tier 1 is the daily load; tier 3 is real but rare.

### Tier 1 — the daily load

| Task | Triggers | Procedure |
|---|---|---|
| Verify a slice of work | D1, D3 | `gate-chain` ✔ written |
| Fix a defect | D2, D3 | `root-cause-repair` |
| Implement a change | D2, D4 | `slice-and-verify` |
| Write tests for existing code | D2, D3 | `behaviour-first-tests` |
| Answer from the corpus | D3 | `corpus-answer` |
| Inspect the workspace | D5 | `inspect-workspace` |

### Tier 2 — regular

| Task | Triggers | Procedure |
|---|---|---|
| Research an external topic | D3 | `source-triangulation` |
| Integrate an external service | D3, D4 | `schema-first-integration` |
| Review code adversarially | D2, D3, D5 | `adversarial-review` |
| Scaffold a new project | D5 | `scaffold-from-template` |
| Refactor without behaviour change | D2, D3 | `behaviour-preserving-refactor` |
| Update dependencies | D1, D3 | `dependency-uplift` |

### Tier 3 — infrequent, high consequence

| Task | Triggers | Procedure |
|---|---|---|
| Audit the system | D1, D3, D5 | `governance-audit` — blocked on L2 |
| Triage a failure | D1, D2 | `incident-triage` |
| Design an agent | D4, D5 | `agent-design` |
| Author a procedure | D4, D5 | `procedure-authoring` ✔ written |
| Port between languages | D2, D4 | `cross-language-port` |
| Generate fixtures or data | D3, D5 | `fixture-generation` |

### Tasks that need no procedure

Recorded so they are not re-proposed. Each is fully covered by its skill: read
one named file, list a directory, fetch one known URL, archive an artifact,
collect a time quorum. Single-step, self-announcing failure, no method to
choose. **Adding a procedure here would be ceremony.**

---

## 4. Where drift actually happens

Three worth calling out because they are the expensive ones.

**Symptom repair (D2).** The fastest path to a green gate is often a change
that makes the gate stop complaining. It passes. It ships. The defect is still
there and now has a test asserting the wrong thing. `root-cause-repair` exists
entirely for this, and its standard has to be that the fix explains the original
failure — not that the gate turned green.

**Single-source research (D3).** One authoritative-looking page becomes the
answer. Nothing signals the absence of corroboration. This is the same shape as
the time-quorum argument: one reading is a value someone else chose.
`source-triangulation` requires independent agreement before a claim enters the
record.

**Assertion-free tests (D2 + D3).** A test that exercises code without asserting
behaviour raises coverage and catches nothing. The gate chain reports 85% and
the number is a lie. `behaviour-first-tests` requires the test to fail before the
implementation exists — the same rule AGENTS.md §4 already applies to us.

---

## 5. Build order

1. **`procedure-authoring`** ✔ — written. Everything else is authored under it,
   so it comes first or the rest drift while being written.
2. **`root-cause-repair`, `behaviour-first-tests`** — the two D2 procedures.
   Highest drift cost, most frequently exercised.
3. **`slice-and-verify`, `corpus-answer`, `inspect-workspace`** — completes tier 1.
4. **Tier 2**, in the order given.
5. **Tier 3** as the tasks become real. `governance-audit` is blocked on L2 and
   L2 is blocked on R1.3.

Tier 1 minus `gate-chain` is five procedures. That is the batch to generate.

---

## 6. Open

| # | Item |
|---|---|
| **P1** | **Toolsets are derived, not selected.** Canon §3 as written reads as though a task carries a fixed bundle; the intent is least privilege — a tool is provisioned only if a task necessitates it. Under that reading AgentAgent grants what the selected procedures require and nothing more, and the "toolset" is an output. **AMEND CANON.** |
| **P2** | Consequence of P1: the retinue caches on `toolset_signature`, and derived sets fragment. Procedure combinations should cluster hard in practice, so the cache likely survives as an empirical property rather than a guaranteed one. Measure in R1.3 before assuming either way. |
| **P3** | The eleven groups in `tool_manifest.json` are not toolsets under P1. Either delete them or demote them to named envelopes used by tests to assert a derived set falls inside a known bound. Nothing grants from them. |
| **P4** | `test_standards_are_measurable` is satisfiable by decoration — "zero write operations" restates an effect, "100% of matching entries" is a tautology. Tighten to reject standards that only restate a tool's effects, and accept that the rest is a review judgement. |
| **P5** | `type-casting` under this model is an archetype family, not a skill. Whether the five roles or some other set are the archetypes is undecided, and P1 changes what an archetype even is. |
