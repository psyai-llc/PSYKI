---
tool: time_witness
tool_version: 1.0.0
skill_version: 1.0.0
classes: [INTERNAL]
effects: [READ, EGRESS]
---

# time_witness

## Purpose

Collect independent network time observations and return a verified quorum timestamp.

## Preconditions

- Multiple independent network time sources are configured in registry.
- Network egress is operational across available time endpoints.
- Quorum threshold parameters are initialized prior to query.

## Procedure

1. Query multiple independent time providers simultaneously over network.
2. Collect response timestamps and tag incoming observations untrusted.
3. Calculate time variance across returned observations.
4. Evaluate consensus against required quorum threshold.
5. Return anchor timestamp if quorum is achieved, or mark output unanchored.

## Failures

| Symptom | Cause | Action |
|---|---|---|
| Quorum not reached | Time observations drift beyond variance threshold | Mark result explicitly as unanchored. Do not guess timestamp. |
| Egress timeout | Multiple time servers unreachable | Retry query with alternative independent endpoints once. |
| Malformed time payload | Response format corrupted or intercepted | Discard invalid server response from quorum pool. |
| Single source response | Too few providers available for consensus | Reject single reading as unverified anchor. |

## Refuse

- Accepting a single time server reading as a verified timestamp anchor.
- Emitting a best guess timestamp when quorum consensus fails.
- Querying unverified or single-operator time endpoints.

## Emits

- Verified quorum timestamp or explicit unanchored status flag.
- Raw time observations tagged untrusted to archive.
- Variance metrics and quorum consensus logs to execution record.
