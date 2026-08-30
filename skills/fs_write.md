---
tool: fs_write
tool_version: 1.0.0
skill_version: 1.0.0
classes: [PROVISIONED]
effects: [READ, WRITE]
---

# fs_write

## Purpose

Write file contents or construct directories safely inside the workspace boundary.

## Preconditions

- The target path resolves entirely inside the workspace root boundary.
- Parent directories exist or can be created within the workspace.
- The write payload is fully formed and validated prior to execution.

## Procedure

1. Resolve the target path against the workspace root and enforce the boundary.
2. Create parent directories if missing within the workspace.
3. Write payload atomically to the designated path.
4. Verify file write completed successfully and check written byte length.
5. Record path, byte count, and operation status to execution log.

## Failures

| Symptom | Cause | Action |
|---|---|---|
| Traversal attempt blocked | Target path escapes workspace root | Refuse operation immediately. Report security error. |
| Disk space full | Host storage exhausted | Abort operation. Clean temporary files and report failure. |
| Permission denied | Read-only filesystem or locked path | Check target file permissions before retry. |
| Partial write failure | Process interrupted during write | Clean partial files. Re-attempt atomic write once. |

## Refuse

- Any path outside the workspace root boundary under all circumstances.
- Writing unvalidated or unparsed external data streams directly to disk.
- Overwriting locked system or configuration files.

## Emits

- File path, written byte size, and timestamp to execution log.
- Operation status and error flags to the system record.
- Security anomaly flags on path traversal attempts.
