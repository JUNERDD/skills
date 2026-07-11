# Investigation and Root-Cause Ledger

Use one evolving Markdown ledger when a debug session spans a user handoff, context compaction, multiple runs, an expensive reproduction, a repair, or a request for durable evidence. Keep the validated `debug-plan/v1` JSON file as the authority for boundaries, hypotheses, probes, and coverage.

## Table of contents

- Creation and placement
- Update rules
- Status model
- Root-cause proof
- Template
- Retention and cleanup

## Creation and placement

Create the ledger after the initial coverage plan validates and before the first expensive or user-owned reproduction. For a short agent-owned diagnosis that remains within one turn and does not require durable evidence, the validated plan and final evidence summary may be sufficient.

Prefer this order:

1. Use an established incident or RCA directory when the user requests durable evidence.
2. Otherwise use `.debug-logs/<SESSION_ID>.root-cause.md` as an ephemeral ledger.
3. Keep the path inside the authorized workspace and never overwrite an unrelated report.

Record the coverage-plan path rather than duplicating its full hypothesis-probe matrix. Create one ledger per session and update the same file even when the leading theory changes.

## Update rules

Read the current ledger before every update. Append one investigation row for each material transition:

- initial validated plan;
- failing reproduction analysis;
- targeted blind-spot run;
- root-cause change;
- diagnosis-only terminal handoff;
- authorized repair decision;
- failed verification;
- successful verification;
- cleanup or retention decision.

Preserve rejected and superseded paths with the evidence that displaced them. Do not retry one without new contradictory evidence. Separate verified facts from inference, and separate root cause from enabling conditions and downstream symptoms.

## Status model

Use these document statuses:

- `Planning`
- `Instrumented`
- `Awaiting reproduction`
- `Analyzing`
- `Confirmed root cause`
- `Diagnosis complete; repair not authorized`
- `Repair applied; awaiting verification`
- `Root cause repaired and verified`
- `Still failing`
- `Incomplete`

Use these hypothesis statuses, matching the coverage plan:

- `PENDING`
- `CONFIRMED`
- `REJECTED`
- `INCONCLUSIVE`
- `NOT_REACHED`
- `SUPERSEDED`

Use `NOT_REACHED` only when enclosing evidence proves the flow terminated or branched before the hypothesized path. Treat an otherwise missing probe as `INCONCLUSIVE`.

## Root-cause proof

Require evidence for all three links:

1. The originating invalid state, decision, ordering, or external result.
2. Its propagation across the relevant boundaries.
3. The observed symptom under the failure contract.

Cite run, parent flow, operation, child correlation or request, sequence/time, probe ID, location, and bounded values. Do not promote a hypothesis from correlation alone.

For an authorized repair, additionally record:

- the owning boundary and violated invariant;
- why the repair eliminates the causal mechanism;
- why every changed layer is necessary and unrelated cleanup is excluded;
- the same relevant probe and invariant results from a separate verification run.

## Template

```md
# Root-Cause Investigation

## Scope

- Debug date: `YYYY-MM-DD`
- Issue: `[precise failure contract]`
- Workspace: `[absolute path]`
- Session ID: `[session]`
- Ready file: `[path]`
- Coverage plan: `[debug-plan/v1 path]`
- Evidence file: `[NDJSON path]`
- Status: `[status]`
- Reproduction owner: `[agent | user | external]`
- Reproduction cost: `[low | medium | high | single opportunity]`
- Constraints: `[list]`

## Failure Contract

- Expected: `[observable behavior]`
- Observed: `[observable failure]`
- Trigger: `[smallest realistic flow]`
- Scope and frequency: `[details]`
- Last known good: `[boundary or unknown]`

## Coverage

- Plan validation: `[passed at timestamp]`
- Boundaries / hypotheses / probes: `[counts]`
- Reviewed cause-family exclusions: `[families and reasons]`
- Observer and privacy controls: `[summary]`
- Residual ambiguities: `[list]`

## Current Root Cause

- Root cause: `[precise mechanism or Not proven]`
- Confidence: `[high | medium | low]`
- Origin: `[first invalid boundary/location]`
- Enabling conditions: `[list]`
- Downstream symptoms: `[list]`

Causal chain:

1. `[origin with probe evidence]`
2. `[propagation with probe evidence]`
3. `[symptom with probe evidence]`

## Evidence Timeline

| Run | Parent flow / operation | Sequence/time | Probe | Evidence | Interpretation |
| --- | --- | --- | --- | --- | --- |
| `initial` | `[ids]` | `[sequence/time]` | `[probeId]` | `[bounded values]` | `[what this proves]` |

## Hypothesis Dispositions

| ID | Status | Decisive evidence | Residual ambiguity |
| --- | --- | --- | --- |
| `H-...` | `CONFIRMED` | `[evidence]` | `[none or detail]` |

## Investigation Ledger

| Attempt | Trigger | Evidence reviewed | Decision | Blind spot closed / next authorized step |
| --- | --- | --- | --- | --- |
| `1` | `initial plan` | `[plan and paths]` | `[validated]` | `[coverage]` |

## Repair and Verification

- Repair authorization: `[not requested | authorized]`
- Repair: `[file/function/behavior or Not applied]`
- Mechanism eliminated: `[mechanism]`
- Invariant restored: `[invariant]`
- Scope rationale: `[causal necessity]`
- Verification run: `[runId or Not run]`
- Verification status: `[Not run | Passed | Failed | Blocked]`
- Before/after evidence: `[same probe IDs and selected values]`

## Rejected or Superseded Causes

- `[theory]` — `[status]` — `[decisive evidence]`

## Cleanup and Retention

- Temporary probes: `[present | removed and verified]`
- Location state: `[active count | synced empty]`
- Collector artifacts: `[present | deleted | retained by request]`
- Plan and ledger: `[ephemeral | retained by request/convention | deleted]`

## Open Questions

- `[remaining uncertainty or none]`
```

## Retention and cleanup

Keep the plan and ledger through targeted reruns, intermediate log clears, failed verification, and incomplete investigations.

After success:

- Retain them when the user requests evidence or the repository has a durable RCA convention.
- Otherwise update the terminal diagnosis or verification status and cleanup decision, then delete owned ephemeral files.
- Use `debug_session.py stop --delete-root-cause-document <PATH>` only for a ledger inside the workspace after a terminal diagnosis or successful repair verification.
- Delete the plan separately only when it is owned by the current invocation and no evidence retention was requested.

Never infer cleanup from Git status because `.debug-logs/` is commonly ignored. Never delete host-owned evidence or an incomplete investigation unless the user explicitly requests it.
