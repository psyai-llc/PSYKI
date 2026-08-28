# PSYKI Instruction Set — Index

**Authority:** `docs/PSYKI_CORE.md` is canon. This instruction set implements it.
Where an instruct file disagrees with CORE, CORE wins and the instruct file is a bug.

**Canon rule (repo-wide):** *the newest committed statement wins.* If two documents
disagree, the later commit is doctrine and the earlier one must be explicitly
archived or deleted — never left in place to rot. Silent contradiction is the
failure mode this rule exists to kill.

---

## Instruction classes

| Suffix | Audience | Contains |
|---|---|---|
| `.arch_instruct.md` | reasoning model / human architect | decisions, rationale, schemas, flaw enumeration, open flags. **No literal code.** |
| `.code_instruct.md` | small implementation model | exact files, exact changes, acceptance tests, definition of done. **No judgment calls.** |
| `.human_instruct.md` | Joshua | things only a human with credentials or physical access can do. Checklist form. |

---

## Passes

| Pass | Name | Status | Gate to next |
|---|---|---|---|
| **R0** | Canon — resolve contradictions, register invariants, fix the tree | **ISSUED** | R0.3 merged; `main` tree matches target |
| **R1** | Enforcement — packaging, CI, AGENTS.md, hygiene | pending R0 | all R0.2 invariants have a named test file, passing or `xfail` |
| **R2** | Protocol — enum vocabulary, typed fields, Contract/Verdict/State schemas | pending R1 | schemas validate; round-trip tests green |
| **R3** | Components — substrate, KI, Emissary, PSY, AgentAgent port | pending R2 | e2e runs with `NullPlanner` |
| **R4** | Deploy — MCP surface, runtime topology, `mcp.psyai.cloud` | pending R3 | reachable, authenticated, logged |

---

## R0 — issued

| File | Class | Purpose |
|---|---|---|
| `00-CONVENTIONS.arch_instruct.md` | arch | how every instruct file is structured; naming law |
| `R0-canon/R0.1-supersession.arch_instruct.md` | arch | README v0 vs PSYKI_CORE — which dies, which lives, how |
| `R0-canon/R0.2-invariant-register.arch_instruct.md` | arch | I1–I12 → enforcing test → honest current status |
| `R0-canon/R0.3-tree-reconciliation.code_instruct.md` | code | exact target tree; every move, delete, rename |
| `R0-canon/R0.4-model-binding.arch_instruct.md` | arch | amends CORE §8 to the actual model roster |
| `R0-canon/R0.5-operator-runbook.human_instruct.md` | human | Joshua's checklist for this pass |

**Execution order:** R0.5 first (tag + zip extraction — blocks everything), then
R0.3 (mechanical), then R0.1 and R0.2 (doc commits), then R0.4.

---

## Blocked, awaiting input

| Item | Blocks | Needed from |
|---|---|---|
| `agentagent2-complete (1).zip` contents | R0.3 §4, all of R3 | Joshua — upload the zip into a chat, not the repo |
| Typed-field schemas (CORE §4 names them, nothing specifies them) | R2 entirely | authored in R2.2 unless they exist elsewhere |
| Emissary lossy-encode detector | R2.1 | design decision, R2 |
| Human abort path (no emergency stop exists in the closed loop) | R2.4 | design decision, R2 |
| Website scope, stack, host | R4 | Joshua |
