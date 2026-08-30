---
tool: net_call
tool_version: 1.0.0
skill_version: 1.0.0
classes: [PROVISIONED]
effects: [READ, WRITE, EGRESS]
---

# net_call

## Purpose

Execute state-mutating HTTP requests via proxy against designated network targets.

## Preconditions

- Target URL is an HTTPS scheme explicitly listed in allowable network registry.
- Request payload is validated against endpoint schema prior to transmission.
- Timeout is set and retry policy accounts for non-idempotent side effects.

## Procedure

1. Resolve endpoint against allowable network target registry.
2. Dispatch authenticated request through proxy without reading underlying credential.
3. Capture HTTP status code, response headers, and response body.
4. Verify response completion within set timeout limit.
5. Record request method, target host, latency, and status code.
6. Tag returned payload untrusted.

## Failures

| Symptom | Cause | Action |
|---|---|---|
| 401 / 403 Unauthorized | Missing or expired proxy credential | Stop execution. Report proxy credential authentication error. |
| Duplicate action execution | Retry after ambiguous network timeout | Check remote state before re-sending non-idempotent calls. |
| Host resolution failure | URL not in endpoint registry | Refuse connection. Log unlisted target error. |
| 429 Rate Exceeded | Gateway request quota reached | Apply exponential backoff. Do not issue parallel retries. |

## Refuse

- Issuing plain HTTP requests without HTTPS encryption.
- Retrying a non-idempotent call after an ambiguous timeout without first reading remote state.
- Direct invocation attempting to read or extract raw authorization credentials.

## Emits

- The response body, tagged untrusted.
- Request latency, status code, and target host entries to execution log.
- Egress network transaction records to telemetry.
