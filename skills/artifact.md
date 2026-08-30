---
tool: artifact
tool_version: 1.0.0
skill_version: 1.0.0
classes: [INTERNAL, PROVISIONED]
effects: [READ, WRITE]
---

# artifact

## Purpose

Persist large output payloads to external archive and return pointer references.

## Preconditions

- Payload size exceeds standard result record budget limits.
- Archive storage directory or repository is available and writable.
- Payload format is validated before archive transmission.

## Procedure

1. Receive bulk output data payload from calling process.
2. Generate unique immutable reference identifier and storage path.
3. Write payload atomically into target archive location.
4. Calculate payload checksum and verify written byte size.
5. Return pointer reference containing identifier and metadata to caller.

## Failures

| Symptom | Cause | Action |
|---|---|---|
| Archive write failure | Target storage partition full or unmounted | Abort archive write. Flag storage error to caller. |
| Checksum mismatch | Data corruption during atomic write | Delete corrupted file and re-attempt write once. |
| Reference collisions | Duplicate identifier generation | Regenerate identifier using cryptographically unique random seed. |
| Payload schema invalid | Input data structure malformed | Reject input before disk write attempt. |

## Refuse

- Writing small payloads that fit within standard result record budgets.
- Storing unindexed or non-referencable transient data.
- Overwriting existing immutable archive artifacts.

## Emits

- Immutable artifact pointer reference and storage metadata.
- Byte count, payload hash, and archive timestamp to execution log.
- The reference, for the record to carry in place of the payload.
