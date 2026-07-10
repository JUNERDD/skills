# Investigation and Root-Cause Document

Use one evolving Markdown document to preserve the hypothesis plan, evidence, rejected paths, root cause, fix, and verification for a debug session.

## Table of contents

- Creation timing
- File placement and retention
- Update rules
- Status model
- Document template
- Self-check

## Creation timing

- In one-shot mode, create the document after the causal map and initial hypothesis-probe matrix are ready, before adding probes.
- In standard mode, create it no later than the first leading evidence-backed root-cause candidate and before applying a fix.
- Create one document per session. Update the same file even when the leading theory changes.
- Never overwrite an unrelated existing report.

Creating the document before reproduction in one-shot mode keeps a large matrix out of chat context and preserves the plan if the conversation compacts.

## File placement and retention

Prefer this order:

1. Use an established incident, RCA, or engineering-report directory when the user wants durable evidence.
2. Otherwise create an ephemeral file at `.debug-logs/<SESSION_ID>.root-cause.md`.
3. Keep the path inside `workspaceRoot` and use a `.md` suffix.

Use a unique session ID or random suffix when needed. Do not infer cleanup from Git status.

Retention policy:

- Keep the document throughout investigation, reruns, failed verification, and intermediate log clears.
- After success, retain it when the user asked for evidence or the repository has an established durable RCA convention.
- Otherwise update it with final verification and cleanup status, then delete it with `debug_session.py stop --delete-root-cause-document <PATH>` or delete it separately and verify removal.
- Never delete a document from an incomplete or failed investigation unless the user explicitly requests deletion.

## Update rules

Before every update, read the current document.

Append an investigation-ledger row for each of these events:

- Initial plan
- Reproduction analysis
- Targeted rerun
- Root-cause change
- Fix decision
- Failed verification
- Successful verification
- Cleanup or retention decision

Preserve prior hypotheses and evidence. When a theory is displaced, move it to `Superseded or Rejected Causes` with the evidence that displaced it. Do not retry a rejected path without new contradictory evidence.

Separate verified facts from inferences. A root cause requires evidence for:

1. Originating invalid state, decision, ordering, or external result
2. Propagation through one or more boundaries
3. The observed symptom

Record enabling conditions and downstream symptoms separately from the root cause.

## Status model

Use these document statuses:

- `Planning`
- `Instrumented`
- `Awaiting reproduction`
- `Analyzing`
- `Working theory`
- `Confirmed root cause`
- `Fix applied; awaiting verification`
- `Fixed and verified`
- `Still failing`
- `Incomplete`

Use these hypothesis statuses:

- `PENDING`
- `CONFIRMED`
- `REJECTED`
- `INCONCLUSIVE`
- `NOT_REACHED`
- `SUPERSEDED`

`NOT_REACHED` means enclosing evidence proves the flow terminated or branched before the hypothesized path. A missing probe without enclosing evidence remains `INCONCLUSIVE`.

## Document template

````md
# Root-Cause Investigation

## Scope

- Debug date: `YYYY-MM-DD`
- Issue: `[precise failure contract]`
- Workspace: `[absolute path]`
- Session ID: `[session]`
- Ready file: `[path]`
- Evidence file: `[NDJSON path]`
- Mode: `[one-shot | standard]`
- Status: `[status]`
- Last updated: `[timestamp and timezone]`
- Reproduction cost: `[low | medium | high | single opportunity]`
- Assumptions and constraints: `[explicit list]`

## Failure Contract

- Expected: `[observable behavior]`
- Observed: `[observable failure]`
- Trigger: `[smallest realistic flow]`
- Scope and frequency: `[details]`
- Last known good boundary: `[version/config/date or unknown]`

## Causal Map

```text
[input] -> [boundary] -> [state transition] -> [boundary] -> [symptom]
```

| Boundary | Input/invariant | Output/invariant | Probe IDs |
| --- | --- | --- | --- |
| `[name]` | `[expected]` | `[expected]` | `[ids]` |

## Coverage Summary

- Hypotheses: `[count]`
- Probes: `[count]`
- Shared probes: `[count]`
- Hypotheses mapped: `[percentage]`
- Causal boundaries covered: `[count/total]`
- Hot-path controls: `[count and types]`
- Residual ambiguities: `[list]`

## Hypothesis-Probe Matrix

| ID | Mechanism | Boundary | Confirmed by | Rejected by | Probe IDs | Expected order | Volume control | Priority | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `H-...` | `[specific mechanism]` | `[boundary]` | `[observation]` | `[observation]` | `[probe ids]` | `[sequence]` | `[control]` | `[high/medium/low]` | `PENDING` |

## Current Root Cause

- Root cause: `[one precise sentence or Not proven yet]`
- Confidence: `[high | medium | low]`
- Origin: `[first invalid boundary/location]`
- Enabling conditions: `[conditions that make the bug possible]`
- Downstream symptoms: `[effects, not causes]`

Causal chain:

1. `[originating condition with probe evidence]`
2. `[propagation with probe evidence]`
3. `[reported symptom with probe evidence]`

Key evidence:

- `[run, correlation, sequence, probeId, location, selected values]`

Look here first:

- `[primary code path](/absolute/path/file.ts#L10)`
- `[secondary code path](/absolute/path/file.ts#L42)`

## Evidence Timeline

| Run | Correlation | Sequence/time | Probe | Evidence | Interpretation |
| --- | --- | --- | --- | --- | --- |
| `initial` | `[id]` | `[seq/time]` | `[probeId]` | `[bounded values]` | `[what this proves]` |

## Investigation Ledger

| Attempt | Trigger | Evidence reviewed | Decision | Blind spot closed / next step | Do not repeat unless |
| --- | --- | --- | --- | --- | --- |
| `1` | `initial plan` | `[files/map]` | `[matrix created]` | `[coverage]` | `[new evidence condition]` |

## Fix and Verification

- Fix applied: `[file/function/behavior or Not applied]`
- Why this fixes the origin: `[causal explanation]`
- Verification run: `[runId]`
- Verification status: `[Not run | Passed | Failed | Blocked]`
- Before evidence: `[probe evidence]`
- After evidence: `[same probe evidence]`
- Unchanged invariants: `[proof no adjacent regression]`

## Superseded or Rejected Causes

- `[theory]` — `[status]` — `[evidence that rejected/displaced it]`

## Cleanup and Retention

- Temporary probes: `[present | removed and verified]`
- Location state: `[active count | synced empty]`
- Collector artifacts: `[present | deleted | retained by request]`
- Investigation document: `[ephemeral; scheduled for deletion | retained at path by request/convention]`

## Open Questions

- `[remaining uncertainty or none]`

## Self-Check

- `[yes/no]` Every material hypothesis has confirming and falsifying evidence definitions.
- `[yes/no]` Missing probes were interpreted only with enclosing sentinels and suppression metadata.
- `[yes/no]` The root cause cites origin, propagation, and symptom evidence.
- `[yes/no]` Rejected or superseded paths retain their exclusion evidence.
- `[yes/no]` Every analysis/verification pass has an append-only ledger row.
- `[yes/no]` The fix addresses the origin rather than only the symptom.
- `[yes/no]` Before/after verification uses the same relevant probe IDs.
- `[yes/no]` Temporary instrumentation and artifacts are accounted for.
- `[yes/no]` Secrets and unnecessary PII are absent or redacted.
````

## Self-check

Before claiming success, verify:

- The current status matches the latest evidence.
- The earliest invalid state or ordering is identified.
- At least one evidence chain links origin to symptom.
- Alternative causes at adjacent boundaries are rejected or explicitly unresolved.
- The verification run completed the same flow.
- Cleanup did not delete externally owned artifacts.
