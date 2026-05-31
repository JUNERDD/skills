# Output Templates

Use these templates to produce concise, actionable deliverables.

## Contents

- [Reuse Audit Report](#reuse-audit-report)
- [Build-vs-Reuse ADR](#build-vs-reuse-adr)
- [Reusable Asset Catalog Entry](#reusable-asset-catalog-entry)
- [Consolidation RFC](#consolidation-rfc)
- [Migration Task List](#migration-task-list)

## Reuse Audit Report

```markdown
# Reuse Audit Report

## Scope
- Repos/modules/docs reviewed:
- Capability/problem:
- Constraints:

## Executive summary
- Duplicate/reinvention theme:
- Highest-impact recommendation:
- Expected benefit:

## Findings
| ID | Candidate | Type | Evidence | Confidence | Impact | Recommended action |
|---|---|---|---|---|---|---|

## Priority plan
1. [ ] Action:
   - Owner:
   - PR/task:
   - Acceptance criteria:
   - Risk/rollback:

## Metrics to track
- Baseline:
- Target:
- Review date:
```

## Build-vs-Reuse ADR

```markdown
# ADR: <decision title>

Status: Proposed / Accepted / Deprecated / Superseded
Date: YYYY-MM-DD
Owner: <team/person>

## Context
<Why this decision is needed, affected systems, constraints, and prior attempts.>

## Decision
<Adopt, adapt, wrap, build, keep separate, consolidate, or sunset.>

## Alternatives considered
| Alternative | Pros | Cons | Outcome |
|---|---|---|---|

## Consequences
- Positive:
- Negative:
- Follow-up work:
- Review date:
```

## Reusable Asset Catalog Entry

```yaml
apiVersion: internal/v1
kind: ReusableAsset
metadata:
  name: <asset-name>
  tags: [<domain>, <language>, <capability>]
spec:
  type: library | service | component | template | workflow | document | data-asset
  owner: <team>
  lifecycle: adopt | trial | assess | hold | deprecated
  capability: <problem this solves>
  source: <repo/path/package/service-url>
  docs: <link/path>
  examples: <link/path>
  consumers: []
  support: <channel or policy>
  versioning: <semver/api/deprecation policy>
  knownAlternatives: []
```

## Consolidation RFC

```markdown
# RFC: Consolidate <capability>

## Problem
<Which duplicated implementations/workflows exist and why they hurt delivery, quality, or ownership.>

## Goals
- 

## Non-goals
- 

## Current candidates
| Candidate | Owner | Consumers | Strengths | Gaps |
|---|---|---|---|---|

## Proposed target state
<Architecture, owner, API/interface, contribution path, migration route.>

## Migration plan
| Phase | Work | Consumers affected | Rollback | Done when |
|---|---|---|---|---|

## Risks and mitigations
- 

## Open questions
- 
```

## Migration Task List

```markdown
## Migration: <duplicate> -> <shared asset>

- [ ] Add characterization tests around current behavior.
- [ ] Add adapter/wrapper or compatibility layer.
- [ ] Migrate one low-risk consumer.
- [ ] Compare behavior and telemetry.
- [ ] Migrate remaining consumers in batches.
- [ ] Mark duplicate deprecated with owner and removal date.
- [ ] Remove duplicate after consumers are migrated.
- [ ] Update catalog, docs, examples, and ADR/RFC links.
```
