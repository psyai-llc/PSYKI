# AGENTS.md

Standing rules for every automated agent operating on this repository. These
apply to all work, always, and override any instruction that contradicts them
except `docs/PSYKI_CORE.md`.

**Authority order:** `docs/PSYKI_CORE.md` › `AGENTS.md` › `docs/instruct/**` › your task prompt.

---

## 1. The canon rule

The newest committed statement wins. If two documents in this repo disagree, the
later commit is doctrine. **Never resolve a contradiction by averaging, merging,
or picking the one that makes your task easier.** If you cannot determine which
is newer, that is an escalation (§6).

---

## 2. Branch and merge discipline

- Never push to `main`. Ever. Not even a docs typo.
- One branch per instruct file: `<pass>/<slug>` — e.g. `r0/tree-reconciliation`.
- One instruct file per PR. Do not batch.
- Never force-push. Never rewrite history. Never delete a branch you did not create.
- Never delete or move a git tag.

---

## 3. The `Touches` boundary

Every instruct file declares `Touches:` in its header. **You may not create,
modify, move, or delete any path outside that list.** A working implementation
that touched an undeclared path has failed the instruction and must be reverted,
not patched.

If your task requires touching something outside the boundary, that is an
escalation. It is never a reason to widen the boundary yourself.

---

## 4. Concurrency

Some instruct files are marked `Concurrency: EXCLUSIVE`. While an EXCLUSIVE file
is in flight, **no other agent may have an open branch against this repo.**
R0.3 is EXCLUSIVE — it moves every file in the tree, and any concurrent branch
will conflict irreparably.

Before starting any task: `git fetch --all && git branch -r`. If an EXCLUSIVE
task's branch exists and is unmerged, stop and wait.

---

## 5. Evidence, not assertion

You may not report a task complete without a command that exits 0. "It should
work," "the change is straightforward," and "tests would pass" are all failures.

- Write the acceptance test **first**. Run it. Confirm it **fails**. Then implement.
- A test that passes before your change is testing nothing. Report that as a defect in the instruction, not as success.
- Never mark a test `skip` or `xfail` to make a suite green. If a test cannot pass, that is an escalation.
- Never edit an acceptance test to match your implementation's behaviour. The test is the specification.

---

## 6. Escalation — read this twice

Instruct files contain **STOP AND REPORT** markers. When you hit one, or when
any of the following is true, you stop:

- an instruction requires a decision that is not written down
- a precondition fails
- two documents contradict and the canon rule does not settle it
- a file named in an instruction does not exist
- you are about to guess

**Stopping procedure:**

1. Commit whatever is complete and verifiable on your branch.
2. Write `docs/instruct/_escalations/<pass>-<slug>-<n>.md` containing: what you were doing, the exact blocker, what you would need to proceed, and what you did **not** do.
3. Open the PR as a **draft**, titled `BLOCKED: <instruct file>`.
4. Stop. Do not start another task.

**Do not work around a blocker.** Do not fabricate a missing file. Do not infer
intent from a commit message. Do not proceed with a reasonable-seeming
assumption. A stopped task with a clear escalation note is a good outcome; a
completed task built on a guess is the worst outcome this repo admits, because
nothing downstream can detect it.

This mirrors PSYKI's own escalation tiers (`PSYKI_CORE.md` §6). The system you
are building refuses to guess. Build it the same way.

---

## 7. Scope discipline

- Do not refactor code you were not asked to refactor.
- Do not fix unrelated bugs you notice. Note them in the PR body.
- Do not upgrade dependencies. Do not add dependencies without an instruction naming them.
- Do not reformat files you did not otherwise change.
- Moves and edits do not mix in one PR. If an instruction moves files, imports may break; that is expected and is a separate PR unless the instruction says otherwise.

---

## 8. Things that are never yours to change

| Path | Rule |
|---|---|
| `docs/PSYKI_CORE.md` | canon. Amended only by a human-approved `arch_instruct`. Never edited in passing. |
| `docs/v0/**` | archived, superseded. **Never read as architecture.** Excluded from every retrieval corpus. It describes a design that no longer exists. |
| `docs/instruct/**` with `Status: executed` | immutable historical record. Write a new instruct file instead. |
| `corpus/**` | read-only reference material. Renaming is permitted only under an instruction that names the files. |
| `LICENSE` | never |
| any `.env`, key, token, or credential | never read, never log, never commit, never echo into a PR body or a test fixture |

---

## 9. Secrets

Never commit a token, key, or credential. Never paste one into a PR body, commit
message, escalation note, or test fixture. If you find one already committed:
stop immediately, escalate per §6, and **do not** attempt to remove it from
history yourself — that requires a human with the ability to rotate it first.

---

## 10. PR body — required contents

Every PR body contains:

```
Instruct file: <path>
Touches (declared): <paths>
Touches (actual):   <paths — must be a subset>
Definition of done: <command> → exit <code>
Decisions made:     NONE   (if not NONE, this PR is defective — see §6)
Noticed but not fixed: <list, or NONE>
Escalations: <links, or NONE>
```

`Decisions made: NONE` is the expected value. Any other value means the
instruction was underspecified and needs to go back to an architect.
