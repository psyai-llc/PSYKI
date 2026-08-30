---
tool: browser
tool_version: 1.0.0
skill_version: 1.0.0
classes: [PROVISIONED]
effects: [READ, EGRESS, EXECUTE]
---

# browser

## Purpose

Render dynamic web pages in an isolated browser environment to extract content.

## Preconditions

- A static HTTPS fetch cannot produce the content. Prefer net_fetch whenever it can.
- Target URL is an HTTPS scheme within allowed registry bounds.
- Browser execution sandbox is healthy and isolated from workspace host.

## Procedure

1. Launch isolated headless browser session with network egress limits.
2. Navigate to target URL and wait for page load lifecycle completion.
3. Extract DOM content, render tree, or target text elements.
4. Close dynamic page context and clean script runtime state.
5. Tag all extracted text and DOM content untrusted.

## Failures

| Symptom | Cause | Action |
|---|---|---|
| Script execution hang | Infinite loop in third-party page JavaScript | Force terminate tab session when timeout expires. |
| Rendering engine crash | Unhandled browser memory overhead | Restart dynamic engine sandbox and retry once. |
| Egress restriction blocked | Subresource loading outside allowlist | Ignore blocked resource and extract partial DOM. |
| Page element missing | Dynamic DOM element failed to load in time | Capture snapshot of current DOM state and log warning. |

## Refuse

- Dynamic rendering when a static HTTPS fetch achieves required outcome.
- Executing downloaded binary artifacts or untrusted browser extensions.
- Storing session cookies or credentials across dynamic browsing sessions.

## Emits

- Extracted text and DOM tree structure tagged untrusted.
- Render performance metrics, load times, and resource logs.
- Screenshots to the archive via artifact when the task needs them.
