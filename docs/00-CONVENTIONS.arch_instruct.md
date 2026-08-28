# 00 — Conventions

**Class:** arch_instruct · **Pass:** R0 · **Status:** issued

---

## 1. Naming law

```
<PASS>.<N>-<kebab-slug>.<class>.md
```

`class ∈ {arch_instruct, code_instruct, human_instruct}`

Rules, non-negotiable because tooling will depend on them:

- lowercase kebab slug; **no spaces, no colons, no parentheses, no `(1)`**
- one class per file — if a file needs both design and code, split it
- numbers never reused; a superseded file is **deleted**, not renumbered
- an instruct file that has been executed gets `Status: executed @ <sha>` in its header and is never edited again — write a new one instead

---

## 2. Mandatory header

Every instruct file opens with:

```
**Class:** <class> · **Pass:** <R0..R4> · **Status:** issued | executed @ <sha> | superseded by <file>
**Depends on:** <files that must be executed first, or NONE>
**Touches:** <paths this file is permitted to modify>
```

`Touches` is a hard boundary. An implementation model that edits a path not listed
under `Touches` has failed the instruction regardless of whether the code works.

---

## 3. `code_instruct` anatomy — fixed, in order

1. **Context** — one paragraph. Why this exists. No rationale beyond what's needed to execute.
2. **Preconditions** — checkable assertions. If any fails, **stop and report**; do not adapt.
3. **Files** — explicit table: path · action (`create`/`modify`/`move`/`delete`) · note.
4. **Specification** — what the code must do, expressed as behaviour and signatures.
5. **Acceptance tests** — the exact test file and the exact assertions. Written before the implementation.
6. **Definition of done** — a command that exits 0.
7. **Do not touch** — paths and behaviours explicitly out of scope.

**The rule that makes this work:** a `code_instruct` must contain zero decisions.
If the implementing model has to choose, the instruction is defective and must be
escalated back to an `arch_instruct`, not resolved locally. This is escalation
tier 2 applied to the authoring pipeline itself.

---

## 4. `arch_instruct` anatomy

1. **Decision** — stated up front, in one sentence.
2. **Rationale**
3. **Consequences** — what this forecloses, not just what it enables.
4. **Flaw enumeration** — known weaknesses of the decision, written by the author, not discovered later. A section with nothing in it means the analysis was not done.
5. **Open flags** — `FLAG-<n>`, each with a named owner and the pass that closes it.

---

## 5. `human_instruct` anatomy

Checklist only. Each item: **one action, one verifiable result.** No item may
require the reader to hold prior context in their head. Ordered by dependency,
with any waiting periods (DNS, billing, propagation) started first.

---

## 6. Flaw enumeration for this convention

- **Overhead.** Seven mandatory sections is heavy for a three-line change. Mitigation: changes under ~20 lines that alter no behaviour go through normal commits, not instruct files. Instruct files are for *structural* change.
- **Staleness.** Executed instruct files become an archaeological record that will drift from the code. They are deliberately immutable, so the repo will accumulate correct-at-the-time documents that describe a past tree. Accepted: the alternative is editing history, which destroys the audit trail. `00-INDEX.md` is the only live map.
- **The `Touches` boundary is unenforced** until R1 lands a CI check that diffs a PR's changed paths against the `Touches` header of the instruct file named in the commit message. Until then it is honour-system.

## 7. Open flags

- **FLAG-1** — no machine-readable form of these conventions exists. `AGENTS.md` in R1 must encode them so coding agents inherit them without reading prose. Owner: R1.4.
- **FLAG-2** — no linter validates instruct filenames or headers. R1.3. Owner: R1.3.
