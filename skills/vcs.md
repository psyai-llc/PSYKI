---
tool: vcs
tool_version: 1.0.0
skill_version: 1.0.0
classes: [PROVISIONED]
effects: [READ, WRITE]
---

# vcs

## Purpose

Manage version control repositories within the workspace boundary safely.

## Preconditions

- Target repository directory exists within the workspace boundary.
- Version control binary is installed and executable in sandbox.
- Working tree status is checked prior to issuing state mutations.

## Procedure

1. Verify workspace status and branch health before executing command.
2. Execute version control operation with explicit parameters.
3. Separate file moves and structural edits into distinct commits.
4. Capture stdout, stderr, and exit status code.
5. Record action details, commit hashes, and branch state.

## Failures

| Symptom | Cause | Action |
|---|---|---|
| Merge conflict | Overlapping edits across branches | Abort merge operation. Flag conflict locations for manual resolution. |
| Detached HEAD | Checked out specific commit directly | Create explicit branch before making edits or commits. |
| Command execution failure | Unrecognized flag or invalid syntax | Verify parameters against supported subset and retry. |
| Uncommitted changes blocking | Stale modified files in workspace | Stash or commit existing changes before switching context. |

## Refuse

- Any force-push operation or history rewriting command.
- Deleting a branch it did not create.
- Combining file moves and content modifications into a single commit.

## Emits

- Repository commit hashes, diff summaries, and status logs.
- Branch state updates and structural changes to execution record.
- Failure alerts on merge conflicts or dirty workspace states.
