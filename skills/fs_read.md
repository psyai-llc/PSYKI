---
tool: fs_read
tool_version: 1.0.0
skill_version: 1.0.0
classes: [INTERNAL, PROVISIONED]
effects: [READ]
---

# fs_read

## Purpose

Read file contents or directory structures within the workspace root boundary.

## Preconditions

- The target path resolves inside the workspace root.
- The path exists and is readable by the process.
- Target file size is checked and fits within the memory allocation.

## Procedure

1. Resolve the requested path against the workspace root.
2. Verify the file size does not exceed the maximum reading budget.
3. Read the file contents or list directory nodes.
4. Record the file path, byte size, and access status.
5. Return the retrieved contents to the caller.

## Failures

| Symptom | Cause | Action |
|---|---|---|
| Path access denied | Path attempts traversal outside workspace | Refuse execution. Report boundary violation. |
| File not found | Invalid path or missing file | Report the missing path. Do not create it. |
| Memory budget exceeded | File size exceeds maximum read limit | Truncate reading or use dynamic chunking. |
| Encoding error | Binary file read as UTF-8 text | Change parse mode to raw binary. |

## Refuse

- Any target path that escapes the designated workspace boundary.
- Files exceeding maximum readable memory budget without explicit chunking.
- Attempting to read device nodes or special system sockets.

## Emits

- Raw file contents or directory entries to the caller.
- Path, byte size, and access logs to the record.
- Boundary violation flags on invalid path resolution attempts.
