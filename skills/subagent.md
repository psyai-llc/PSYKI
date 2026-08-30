---
tool: subagent
tool_version: 1.0.0
skill_version: 1.0.0
classes: [PROVISIONED]
effects: [READ, SPAWN]
---

# subagent

## Purpose

Spawn bounded child agent instances to perform targeted sub-tasks independently.

## Preconditions

- Sub-task is clearly defined with explicit acceptance criteria.
- Maximum child agent count and recursion depth are strictly bounded.
- Assigned tool set does not exceed permissions granted to parent process.

## Procedure

1. Construct sub-task contract specifying exact scope and parameters.
2. Restrict granted tools to subset of parent process capabilities.
3. Spawn child agent instance inside isolated execution context.
4. Monitor child execution until completion or timeout threshold.
5. Collect the child's result reference and completion status.

## Failures

| Symptom | Cause | Action |
|---|---|---|
| Child agent timeout | Sub-task stuck in execution loop | Terminate child instance. Collect partial state and fail. |
| Unbounded child spawning | Fan-out limit reached | Refuse creation of additional subagents. |
| Orphaned process | Parent process terminated before child | Signal shutdown to child processes automatically. |
| Schema validation failure | Child return payload malformed | Discard payload. Record schema error in parent context. |

## Refuse

- Spawning child agents with permissions exceeding current process capabilities.
- Unbounded or recursive spawning without hard fan-out limits.
- Delegating task completion verification entirely to child instance without parent checks.

## Emits

- Each child's completion status and result reference.
- Resource usage metrics and step history to task record.
- Aggregate outcome against the declared fan-out bound.
