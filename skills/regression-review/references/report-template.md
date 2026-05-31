# User-Visible Regression Audit

## Scope

- Review date: `YYYY-MM-DD`
- Scope reviewed: `[working tree | staged diff | commit range | branch diff | PR]`
- Baseline: `[HEAD | commit SHA | branch | PR base]`
- Completion: `[Complete within reviewed scope | Incomplete - reason]`
- Assumptions: `[state defaults if scope, runtime setup, credentials, platform, or environment was inferred]`

## Gate Snapshot

- Recommendation: `[Block | Discuss | Pass with caveat | Pass]`
- Completion: `[Complete within reviewed scope | Incomplete - exact uncovered area]`
- Why now: `[one sentence that explains the review decision]`
- Must-review now: `[top 1-3 items only; full list is in Complete Findings Index]`
  1. `F#` `[short title]`
  2. `F#` `[short title]`
  3. `F#` `[short title]`
- Findings count: `Block [n] | Discuss [n] | Watch [n] | Intentional [n]`
- Coverage confidence: `[high | medium | low]`
- Behavior graph coverage: `[built for n surfaces | partial - reason | skipped - reason]`
- Biggest blind spot: `[short phrase, or None identified]`

## Complete Findings Index

If no findings exist, write `No user-visible regression findings identified in the reviewed scope.`
Otherwise add one row for every `F#` finding in the report.

| ID | Action | Surface | User-visible outcome | Confidence |
| --- | --- | --- | --- | --- |
| `F1` | `[Block | Discuss | Watch]` | `[route, command, API output, export, email, etc.]` | `[one-line outcome]` | `[high | medium | low]` |

## Block

If none exist, write `None.`
Otherwise repeat this card for every `Block` finding. Continue numbering across all finding sections as needed.

### F1 Block - [Short title]

User impact: `[what users will notice or fail to complete]`
Review reason: `[why this is worth blocking in review]`
Surface: `[route, feature, command, output, email, etc.]`
Confidence: `[high | medium | low]`

Look here first:
- `[primary](/abs/path/file.ts#L10)`
- `[secondary](/abs/path/file.tsx#L42)`

Behavior delta:
- Before: `[behavior before this change]`
- After: `[behavior after this change]`

Evidence:
- `[runtime repro, targeted test, log, screenshot, fixture, or code-path evidence]`

Reviewer action:
`[block until fixed | block until disproven | request targeted test | request runtime verification]`

## Discuss

If none exist, write `None.`
Otherwise repeat this card for every `Discuss` finding. Continue numbering across all finding sections as needed.

### F2 Discuss - [Short title]

User impact: `[what users may notice]`
Review reason: `[why this deserves review discussion]`
Surface: `[route, feature, command, output, email, etc.]`
Confidence: `[high | medium | low]`

Look here first:
- `[primary](/abs/path/file.ts#L10)`
- `[secondary](/abs/path/file.tsx#L42)`

Behavior delta:
- Before: `[behavior before this change]`
- After: `[behavior after this change]`

Evidence:
- `[what supports the concern and what is still missing]`

Reviewer action:
`[raise in review | confirm intent | ask for proof | request follow-up test]`

## Watch

If none exist, write `None.`
Otherwise repeat this card for every `Watch` finding. Continue numbering across all finding sections as needed.

### F3 Watch - [Short title]

User impact: `[minor or narrower visible effect]`
Review reason: `[why it is worth noting but not blocking]`
Surface: `[route, feature, command, output, email, etc.]`
Confidence: `[high | medium | low]`

Look here first:
- `[primary](/abs/path/file.ts#L10)`

Behavior delta:
- Before: `[behavior before this change]`
- After: `[behavior after this change]`

Evidence:
- `[what was checked]`

Reviewer action:
`[approve with caveat | monitor | add follow-up test | note for later]`

## Intentional Changes

If none exist, write `None.`

- `I1` `[short visible change]` - `[why it appears intentional]` - `[link](/abs/path/file.ts#L10)`

## Coverage Ledger

Every touched user-visible or unknown-impact surface must appear here, including surfaces with no findings.

| Surface / path | Touched files or entry points | Status | Result | Evidence |
| --- | --- | --- | --- | --- |
| `[surface]` | `[file or entry point links]` | `[Finding F# | Intentional I# | Reviewed - no user-visible regression found | Not user-visible | Not covered]` | `[short result]` | `[static trace, test, runtime check, fixture, or reason not covered]` |

## Evidence Appendix

### Behavior Graph Deltas

Include one row for each touched user-visible or unknown-impact surface where a scoped behavior graph was built. If no behavior graph was useful, write `None built - [reason]`.

| ID | Surface | Baseline path | After-change path | Delta | Ledger / finding link |
| --- | --- | --- | --- | --- | --- |
| `B1` | `[surface]` | `[Entry -> Input -> Guards -> Transform -> Output/effect]` | `[Entry -> Input -> Guards -> Transform -> Output/effect]` | `[changed input, moved/removed guard, changed transform, changed output, or none]` | `[Finding F# | Intentional I# | Reviewed | Not covered]` |

### Diff Inventory

| File or area | Classification | User-visible path considered |
| --- | --- | --- |
| `[path]` | `[surface | dependency | config | test-only | docs-only | generated | unknown]` | `[route, command, output, API, none, or unknown]` |

### Candidate Sweep Log

Use this section for meaningful candidates that were investigated and dismissed, or for duplicate candidates merged into another finding. Omit trivial unchanged paths.

| Candidate | Decision | Reason |
| --- | --- | --- |
| `[candidate behavior]` | `[dismissed | merged into F# | intentional I#]` | `[evidence or reasoning]` |

### Verification Commands

- `[command and key outcome]`
- `[command and key outcome]`

### Supporting Code Links

| ID | Role | Link | Why it matters |
| --- | --- | --- | --- |
| `F1` | `entry` | `[submit handler](/abs/path/file.ts#L10)` | `[where the journey starts]` |
| `F1` | `behavior` | `[guard removed](/abs/path/file.ts#L42)` | `[where the change happens]` |
| `F1` | `output` | `[render path](/abs/path/file.tsx#L88)` | `[where the user-visible result appears]` |

### Blind Spots

| Area | Risk introduced by the blind spot | What would resolve it |
| --- | --- | --- |
| `[unverified path]` | `[how this limits the review decision]` | `[specific next verification step]` |

### Report Self-Check

- `[yes | no]` Every touched user-visible or unknown-impact surface appears in `Coverage Ledger`.
- `[yes | no]` Every finding in an action section appears in `Complete Findings Index`.
- `[yes | no]` Every `Finding F#` ledger row has a matching card.
- `[yes | no]` Every `Not covered` row has a reason and next verification step.
- `[yes | no]` Every graphable user-visible or unknown-impact surface has a behavior graph delta row or a ledger reason for skipping it.
- `[yes | no]` Recommendation follows the mapping rules from the skill.
