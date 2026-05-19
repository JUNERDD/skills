# React Wide API Recursive Review

## Contents

- [Scope](#scope)
- [Gate Snapshot](#gate-snapshot)
- [AST / Static Analysis Coverage](#ast--static-analysis-coverage)
- [Complete Wide-API Index](#complete-wide-api-index)
- [Block](#block)
- [Discuss](#discuss)
- [Watch](#watch)
- [Intentional Exceptions](#intentional-exceptions)
- [Field-Flow Ledger](#field-flow-ledger)
- [Recursive Coverage Ledger](#recursive-coverage-ledger)
- [Evidence Appendix](#evidence-appendix)

## Scope

- Review date: `YYYY-MM-DD`
- Scope reviewed: `[working tree | staged diff | commit range | branch diff | PR | named component | named hook | named context | implementation slice]`
- Baseline: `[HEAD | commit SHA | branch | design doc | current implementation | user-provided code]`
- Entry surface(s): `[component/hook/context/type/module names]`
- Completion: `[Complete within reviewed scope | Incomplete - exact reason]`
- Analysis method: `[AST-first via tool/parser/language server | AST unavailable - heuristic text fallback | mixed]`
- Assumptions: `[scope, ownership, runtime setup, schema, architecture, or field meaning inferred]`
- Analysis mode: `[type-aware AST | syntax AST | mixed AST/search | heuristic search only | manual only]`
- AST/project coverage: `[tsconfig/project root, files parsed, unresolved symbols, parse/type gaps, or N/A]`
- UI behavior oracle: `[build/typecheck/tests/smoke/visual/accessibility/manual checks needed to preserve externally observable behavior, or N/A for report-only scope]`

## Gate Snapshot

- Recommendation: `[Block | Discuss | Pass with caveat | Pass]`
- Completion: `[Complete within reviewed scope | Incomplete - exact uncovered boundary]`
- Why now: `[one sentence explaining the decision]`
- Must-review now: `[top 1-3 items only; full list is in Complete Wide-API Index]`
  1. `F#` `[short title]`
  2. `F#` `[short title]`
  3. `F#` `[short title]`
- Findings count: `Block [n] | Discuss [n] | Watch [n] | Intentional [n]`
- Recursive coverage confidence: `[high | medium | low]`
- Evidence mode: `[AST-verified dominant | mixed AST/text | text-fallback dominant | runtime supplemented]`
- Biggest blind spot: `[short phrase, or None identified]`
- AST confidence impact: `[none | low | medium | high; explain if AST was unavailable/incomplete]`
- User-visible UI regression risk: `[none identified | low | medium | high; name affected screens/interactions and oracle gaps]`

## AST / Static Analysis Coverage

Use this section when AST or static-analysis tooling was available. If it was not available, write `AST not available` and explain the fallback.

| Area | Status |
| --- | --- |
| Parser mode | `[type-aware AST | syntax AST | mixed | not available]` |
| Project config | `[tsconfig path or N/A]` |
| Files parsed | `[count and scope summary]` |
| Unresolved symbols | `[imports, re-exports, wrappers, HOCs, generated code, aliases, any-typed boundaries, or None]` |
| Fallback evidence | `[grep/script/manual/runtime evidence used where AST could not prove the path]` |
| Confidence impact | `[how gaps affect findings or recommendation]` |

## Complete Wide-API Index

If no findings exist, write `No wide-API findings identified in the reviewed scope.` Otherwise add one row for every `F#` finding.

| ID | Action | Boundary / surface | Structural liability | Primary field-flow category | Confidence |
| --- | --- | --- | --- | --- | --- |
| `F1` | `[Block | Discuss | Watch]` | `[component, hook, context, provider, form, table, view model]` | `[one-line liability]` | `[pass-through, context fan-out, effect-bound, etc.]` | `[high | medium | low]` |

## Block

If none exist, write `None.` Otherwise repeat this card for every `Block` finding. Continue numbering across all finding sections.

### F1 Block - [Short title]

Engineering impact: `[how this wide API increases ownership drift, fan-out, false dependencies, or future fragility]`

Review reason: `[why this should block or stop approval until fixed or disproven]`

Surface: `[component/hook/context/flow]`

Confidence: `[high | medium | low]`

Look here first:
- `[primary](/abs/path/file.tsx#L10)`
- `[secondary](/abs/path/file.ts#L42)`

Field-flow delta:
- Current owner: `[where the broad object is created or grouped]`
- Current consumer path: `[where it is passed, spread, consumed, or subscribed]`
- Expected owner: `[where the field/group should be consumed or selected]`

Evidence:
- `[static field read, call-site search, context consumer search, profiler result, or targeted check]`
- `[what proves the API is wider than the boundary owns]`

Reviewer action: `[block until narrow props | use field-level selector | split context | split hook return | replace callback bag | prove intentional boundary]`

UI behavior preservation: `[expected unchanged UI behavior and verification oracle, or explicit product-facing change requiring user approval]`

## Discuss

If none exist, write `None.` Otherwise repeat this card for every `Discuss` finding.

### F2 Discuss - [Short title]

Engineering impact: `[what may drift, subscribe too broadly, or become misleading]`

Review reason: `[what uncertainty should be resolved]`

Surface: `[component/hook/context/flow]`

Confidence: `[high | medium | low]`

Look here first:
- `[primary](/abs/path/file.tsx#L10)`
- `[secondary](/abs/path/file.ts#L42)`

Field-flow delta:
- Current owner: `[where the fields are grouped]`
- Current consumer path: `[where the group flows]`
- Unclear point: `[intent, migration, existing owner, or runtime impact]`

Evidence:
- `[supporting evidence]`
- `[missing proof]`

Reviewer action: `[confirm intent | inspect sibling callers | ask for migration plan | trace consumers | add targeted verification]`

UI behavior preservation: `[expected unchanged UI behavior and verification oracle, or unclear UI risk to resolve]`

## Watch

If none exist, write `None.` Otherwise repeat this card for every `Watch` finding.

### F3 Watch - [Short title]

Engineering impact: `[bounded debt or local maintainability risk]`

Review reason: `[why it is worth noting but not blocking]`

Surface: `[component/hook/context/flow]`

Confidence: `[high | medium | low]`

Look here first:
- `[primary](/abs/path/file.tsx#L10)`

Field-flow delta:
- Current owner: `[where the fields are grouped]`
- Bounded consumer path: `[where the group is used]`

Evidence:
- `[what was checked]`

Reviewer action: `[approve with caveat | follow-up task | test | TODO with exit trigger | monitor]`

UI behavior preservation: `[expected unchanged UI behavior and light verification, or reason no UI behavior is affected]`

## Intentional Exceptions

If none exist, write `None.`

- `I1` `[short exception]`
  - Why it appears deliberate and bounded: `[schema adapter, compatibility shim, design-system wrapper, migration layer, etc.]`
  - Owner / exit trigger: `[owner, issue, deadline, migration flag, or removal condition]`
  - Evidence: `[link](/abs/path/file.ts#L10)`

## Field-Flow Ledger

Every field or field group that matters to the review should appear here. For extremely large generated schemas, group fields by schema section and explain the grouping.

| Surface | Field or group | Source | Flow category | Direct consumer(s) | Pass-through / propagation path | Proposed owner or boundary | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `[UserEditorProps]` | `[contact.email]` | `[user.email]` | `[Directly consumed | Passed through | Spread propagated | Derived | Effect-bound | Context-propagated | Hook-return propagated | Callback/action | Selector candidate | Ref/cache/non-render state | Unused or unverified | Out of scope]` | `[EmailField]` | `[UserEditorView -> ContactSection]` | `[EmailField via useField('email')]` | `[Finding F# | Intentional I# | Reviewed | Not covered]` |

## Recursive Coverage Ledger

Every reviewed implementation-relevant or unknown boundary reached by recursion must appear here.

| Boundary / node | Parent path | Type | Fields considered | Status | Result | Evidence / next step |
| --- | --- | --- | --- | --- | --- | --- |
| `[UserEditorView]` | `[UserEditorContainer -> UserEditorView]` | `[Container | View | Section | Leaf | Hook | Context Provider | Context Consumer | Form Field | Table Row/Cell | Third-party adapter | Unknown]` | `[value, meta, actions, status]` | `[Finding F# | Intentional Exception I# | Reviewed - no wide-API risk found | Not wide-relevant | Not covered]` | `[short result]` | `[field trace, search, runtime check, or why not covered]` |

## Evidence Appendix

- Analysis method used: `[AST-first | language-server assisted | heuristic fallback | manual]`
- Structured parsing limitations: `[unresolved spreads, aliases, dynamic keys, generated code, or None]`


### Entry Inventory

| Entry | Kind | File / link | Why included | Initial width signal |
| --- | --- | --- | --- | --- |
| `[UserEditorProps]` | `[type/interface]` | `[link]` | `[user-specified | scanner | diff]` | `[46 fields]` |

### Boundary Graph

Use a compact tree or adjacency list.

```text
UserEditorContainer
└─ UserEditorView(value, meta, status, permissions, actions)
   ├─ BasicSection(value.basic, meta.errors.basic, actions.changeField)
   ├─ ContactSection(form)  <-- F1 pass-through
   └─ Toolbar(status, permissions, actions)
```

### AST / Static Analysis Notes

Record parser, language-server, AST, or fallback mode. Include important unresolved aliases, HOCs, generated schemas, computed keys, spreads, or dynamic fields that affected confidence.

| Item | Analysis mode | Result / limitation |
| --- | --- | --- |
| `[UserEditorProps]` | `[AST-verified | AST-inferred | Text-fallback | Unknown]` | `[what was proven or why confidence is limited]` |

### Candidate Sweep Log

Use this section for candidates that were investigated and dismissed, merged, or treated as intentional.

| Candidate | Decision | Reason |
| --- | --- | --- |
| `[large ProductEditorViewModel]` | `[dismissed | merged into F# | intentional I#]` | `[evidence or reasoning]` |

### Verification Commands

- `[command]` -> `[key outcome]`
- `[command]` -> `[key outcome]`

### Supporting Code Links

| ID | Role | Link | Why it matters |
| --- | --- | --- | --- |
| `F1` | `broad owner` | `[UserEditorView](/abs/path/file.tsx#L42)` | `[where the whole object enters]` |
| `F1` | `leaf consumer` | `[EmailField](/abs/path/file.tsx#L17)` | `[only reads email-specific fields]` |
| `F1` | `sibling path` | `[PhoneField](/abs/path/file.tsx#L27)` | `[shows repeated over-wide leaf subscription]` |

### Blind Spots

| Area | Risk introduced by blind spot | What would resolve it |
| --- | --- | --- |
| `[unverified provider consumers]` | `[context fan-out may be wider than observed]` | `[run full consumer search or inspect missing package]` |

### Report Self-Check

- `[yes | no]` Every reachable implementation-relevant or unknown boundary appears in `Recursive Coverage Ledger`.
- `[yes | no]` Every finding in an action section appears in `Complete Wide-API Index`.
- `[yes | no]` Every `Finding F#` ledger row has a matching card.
- `[yes | no]` Every `Not covered` row has a reason and next verification step.
- `[yes | no]` Recommendation follows the mapping rules from the skill.
