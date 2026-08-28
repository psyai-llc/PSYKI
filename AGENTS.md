# AGENTS.md

Standing rules for every agent working on this repository. Short on purpose. If
a rule here stops you from doing obviously-correct work, the rule is wrong —
say so in the PR.

**Authority:** `docs/PSYKI_CORE.md` › this file › your task prompt.

Higher beats lower. Two documents at the same level: §1 settles it.

---

## 1. Newest wins

The most recently committed statement is the truth. This repo has been through
several design passes and older files still describe systems that no longer
exist.

Do not resolve a contradiction by averaging, merging, or picking the one that
makes your task easier. Check the commit dates. The later one is doctrine and
the earlier one is now garbage to be removed — not preserved "just in case."

If two statements are genuinely the same age and genuinely conflict, that is a
§8 stop.

---

## 2. Reduction is the default

The current mandate is to cut. You do **not** need permission to delete:

- a duplicate of something that already exists elsewhere
- an empty file or a stub that was never implemented
- a document that canon supersedes
- a build artifact, archive, or report checked in by accident
- a path no longer referenced by anything

There is no declared-paths boundary. Every path except §5 is yours. Delete it,
move it, rename it. List what you removed in the PR body and move on.

When in doubt: deleting is cheap, git remembers, and a repo that contradicts
itself costs more than a file you might have wanted.

---

## 3. The tree must run

Before you open a PR, from a clean checkout at the repo root:

- the package imports — no module shadowing a stdlib name, no broken relative
  imports
- `python -m pytest` collects and runs — no collection errors
- every path referenced by a CI workflow actually exists
- every path referenced by a test actually exists

A commit that leaves the tree unable to import is broken, regardless of what
else it got right. This is the single most common way this repo has drifted:
files that are individually excellent and collectively unrunnable.

**Naming:** uppercase is fine. It is only forbidden where lowercasing the path
would collide with another path — because on a case-insensitive filesystem those
are one file and one silently eats the other. No spaces, colons, parens, or
ampersands; they break shells and Windows checkouts. Enforced by
`tests/test_repo_structure.py`.

---

## 4. Evidence, not assertion

You may not report work complete without a command that exits 0. "It should
work" and "tests would pass" are failures.

- Write the acceptance test **first**. Run it. Confirm it **fails**. Then implement.
- A test that passed before your change is testing nothing. Report that as a
  defect in the task, not as success.
- Never mark a test `skip` or `xfail` to make a suite green.
- Never edit an acceptance test to match your implementation. **The test is the
  specification.** If the test is wrong, that is a §8 stop.

### 4a. A test must run the thing it claims to measure

**Hard line.** Every test exercises behaviour: call the function, feed it input,
assert on what comes back. "Does it produce the desired result when run."

A test that only checks a file exists, a key is present, or a count matches is
**not** a test of the thing that file was supposed to do. Existence checks are
legitimate only where existence *is* the property under test — repo structure,
packaging, config presence — and only when the test says so in its name.

The failure this bans, concretely: a scoring harness where every check is "does
this file exist," summed into a quality score, with a safety dimension computed
as `all(other_checks_passed)`. It reports 1.00 forever. It cannot fail. It is a
gate wearing a gate's clothes and doing none of the work — and a gate that
cannot say no is a pass-through.

If you cannot write a test that runs the behaviour, say so and stop (§8). Do not
substitute a proxy and let the number stand in for the property.

---

## 5. Not yours to change

| Path | Rule |
|---|---|
| `docs/PSYKI_CORE.md` | Canon. Content is amended by a human only. Moving, renaming, or reformatting it is fine under an explicit reconciliation task. |
| `LICENSE` | Never. |
| `corpus/**` | Reference material. Rename, index, and prune duplicates freely; never rewrite the contents. |
| any `.env`, key, token, or credential | Never read, never log, never commit, never echo into a PR body or a test fixture. |

Everything else is fair game.

---

## 6. Git

- Branch off `dev`. PR into `dev`. Never push to `main`.
- Never force-push. Never rewrite history. Never delete a tag, or a branch you
  did not create.
- Commit in logical units with a message that says what changed and why.
- Moves and content edits belong in separate commits. A rename plus a rewrite in
  one diff is unreviewable.

---

## 7. Secrets

Never commit a token, key, or credential — not in code, tests, fixtures, commit
messages, or PR bodies.

If you find one already committed: stop, report it, and do **not** try to scrub
it from history. That needs a human who can rotate it first.

---

## 8. When to stop

Stop and report if:

- a precondition for your task is false
- two documents conflict and §1 does not settle it
- an acceptance test appears to be wrong
- you are about to guess at a decision that changes the architecture

**How to stop:** commit what is complete and working, open a draft PR titled
`BLOCKED: <what>`, and write in the body what blocked you, what you would need
to proceed, and what you did not do. That is the whole ceremony.

**Do not stop for:** a missing file you can obviously create, a naming choice, a
formatting decision, a directory that should clearly exist, or an unrelated bug
you can fix in passing. Make the call, note it under "Judgment calls," keep
going. An agent that halts on every small ambiguity is as useless as one that
guesses on every large one.

---

## 9. PR body

```
What:            one line
Why:             canon section, or the task that asked for it
Done when:       <command> → exit 0
Deleted:         <paths, or NONE>
Judgment calls:  <list, or NONE>
```

"Judgment calls" is expected to be non-empty. It is a record, not a confession.
