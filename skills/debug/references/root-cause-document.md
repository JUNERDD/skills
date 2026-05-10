# Root-Cause Document

Use this reference when runtime evidence identifies, changes, or verifies the likely root cause during a debug session.

## Creation Rules

- Follow the same report-file convention used by the project's `hack-review` and `regression-review` skills: unique random id, obvious report directory when one exists, `tmp/reviews` fallback, and no overwrites.
- Create one Markdown document per debug session once runtime evidence identifies a leading root-cause candidate. Do this no later than the first `CONFIRMED` root cause and before applying the fix.
- Keep updating the same document for that debug session. Do not create a new document just because a hypothesis is rejected, narrowed, or superseded.
- Generate a fresh random id for the filename, such as 8 lowercase hex characters from `openssl rand -hex 4`, `uuidgen`, or an equivalent local source.
- If the repo already has an obvious location for reports or review artifacts, follow that directory convention, but still append the random id immediately before `.md` unless that convention already guarantees a unique per-run filename.
- Otherwise write to `tmp/reviews/YYYY-MM-DD-root-cause-report-<random-id>.md`.
- Do not overwrite an existing report. If the chosen path already exists, generate a new id and choose a new path before writing.
- Report the document path in every handoff after the file exists.
- Use absolute file links with line anchors when the environment supports clickable local links.
- Do not include secrets, tokens, passwords, API keys, or PII. Redact sensitive runtime values and state what was redacted.

## Update Rules

- Update the document after every log-analysis pass that changes hypothesis status or the leading root cause.
- When the root cause changes, replace `Current Root Cause` with the new evidence-backed cause and move the previous cause to `Superseded or Rejected Causes` with the evidence that displaced it.
- When evidence is still incomplete, mark the document status as `Working theory` or `Incomplete` instead of presenting the cause as proven.
- After applying the fix, update `Fix and Verification` before asking for the verification reproduction.
- After verification, record whether the before/after evidence proves the fix. If verification fails, mark the document status as `Superseded`, `Still failing`, or `Incomplete`, preserve the failed-fix evidence, and continue the investigation in the same document.
- After successful cleanup, record that temporary instrumentation and collector-owned artifacts were removed, or state what was intentionally retained at the user's request.

## Document Shape

Use this shape by default:

```md
# Root-Cause Analysis

## Scope

- Debug date: `YYYY-MM-DD`
- Issue: `[short user-visible or runtime symptom]`
- Workspace: `[absolute workspace path]`
- Debug session: `[session id, log file, dashboard URL if available]`
- Status: `[Working theory | Confirmed root cause | Fixed and verified | Still failing | Incomplete]`
- Last updated: `YYYY-MM-DD HH:MM TZ`
- Assumptions: `[runtime setup, reproduction scope, credentials, or environment details inferred]`

## Current Root Cause

Root cause: `[one precise sentence naming where the invalid state or failure originates]`
Confidence: `[high | medium | low]`
Affected surface: `[feature, route, command, job, API, component, service, etc.]`

Causal chain:
1. `[source condition or invalid input/state]`
2. `[where the system propagates or transforms it]`
3. `[where the observed symptom appears]`

Key evidence:
- `[log entry, run id, hypothesis id, source location, or targeted command result]`

Look here first:
- `[primary code path](/abs/path/file.ts#L10)`
- `[secondary code path](/abs/path/file.ts#L42)`

## Hypothesis Ledger

| ID | Hypothesis | Status | Evidence | Disposition |
| --- | --- | --- | --- | --- |
| `A` | `[specific hypothesis]` | `[CONFIRMED | REJECTED | INCONCLUSIVE | SUPERSEDED]` | `[log id, command, file link, or trace]` | `[why this changes the investigation]` |

## Evidence Timeline

| Run | Evidence | Interpretation |
| --- | --- | --- |
| `[initial | verification | rerun id]` | `[log entry, command result, screenshot, or output]` | `[what this proves or rules out]` |

## Fix and Verification

- Fix applied: `[file/function and behavior changed, or Not applied yet]`
- Verification status: `[Not run | Passed | Failed | Blocked]`
- Before evidence: `[pre-fix log or observation]`
- After evidence: `[post-fix log or observation]`
- Cleanup status: `[temporary logs removed, collector artifacts deleted, or retained by request]`

## Superseded or Rejected Causes

- `[previous root-cause theory]` - `[why it was rejected or superseded]` - `[evidence]`

## Open Questions and Next Steps

- `[remaining uncertainty, blocked verification, or follow-up]`

## Document Self-Check

- `[yes | no]` Every `CONFIRMED` root-cause statement cites runtime evidence.
- `[yes | no]` Every rejected or superseded cause explains what evidence displaced it.
- `[yes | no]` The current status matches the latest verification result.
- `[yes | no]` Temporary instrumentation and collector artifacts are either cleaned up or explicitly retained.
- `[yes | no]` Secrets, tokens, passwords, API keys, and PII are absent or redacted.
```

## Writing Rules

- Start with the current status and root cause, not a chronology dump.
- Keep the causal chain concrete enough that another engineer can reproduce the reasoning without reading the entire chat.
- Separate verified runtime facts from inferred consequences.
- Preserve enough rejected-hypothesis evidence to explain why the investigation changed direction.
- Prefer concise tables for ledgers and timelines; use short cards or bullets for causal explanation.
- Treat the document as a durable debugging artifact, not temporary collector state. Do not delete it during collector cleanup unless the user explicitly asks.
