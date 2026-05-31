# Build-vs-Reuse Decision Matrix

Use this reference when the user asks whether to build, reuse, buy, consolidate, or keep separate implementations.

## Scoring scale

Score each criterion 1-5. Higher favors reuse unless noted.

| Criterion | 1 | 3 | 5 |
|---|---|---|---|
| Functional fit | Major gaps | Fits core with adaptation | Fits most needs now |
| Domain alignment | Different semantics | Some overlap | Same business/technical knowledge |
| Change cadence | Likely to diverge | Unclear | Changes should move together |
| Quality/maturity | Unproven, fragile | Usable with gaps | Tested, documented, production-proven |
| Ownership/support | No owner | Partial owner | Clear owner, contribution path, SLA/SLO |
| Integration effort | Heavy migration | Moderate | Easy adoption path |
| Security/license/compliance | Blocking risk | Review needed | Acceptable/approved |
| Performance/reliability | Fails constraints | Unknown or needs tuning | Meets requirements |
| Exit cost/lock-in | Hard to leave | Manageable | Low or isolated behind interface |
| Strategic differentiation | Core differentiator; build may be justified | Mixed | Commodity capability; reuse favored |

Reverse the strategic differentiation criterion when the organization deliberately wants a proprietary capability.

## Decision rules

- **Reuse/adopt** when fit, ownership, maturity, and integration score high, and differentiation is low.
- **Adapt/upstream** when the existing asset is close and the maintainer accepts extensions.
- **Wrap** when callers need a stable local interface but the implementation can be reused or swapped.
- **Build** when requirements are strategically differentiating, existing options fail hard constraints, or ownership/support risk is unacceptable.
- **Keep separate** when code similarity is coincidental and domains will evolve independently.
- **Run a spike** when critical unknowns remain; define time-box, questions, and acceptance criteria before starting.

## Recommendation format

```markdown
## Build-vs-Reuse Recommendation

Decision: Adopt / Adapt / Wrap / Build / Keep separate / Spike
Confidence: High / Medium / Low

### Context
- Capability:
- Consumers:
- Constraints:

### Alternatives considered
| Option | Fit | Cost | Risk | Owner | Notes |
|---|---:|---:|---:|---|---|

### Rationale
- Why this option wins:
- Why rejected options lose:
- Assumptions to validate:

### Consequences
- Migration work:
- Test/rollback plan:
- Ownership/support impact:
- Review date:
```

## Red flags requiring escalation

- No accountable owner for the recommended shared asset.
- License, security, privacy, or compliance review is unresolved.
- A shared abstraction would couple teams with different release/regulatory constraints.
- Migration requires breaking changes without a compatibility plan.
- A golden path is being mandated without onboarding examples and troubleshooting.
- The decision affects multiple teams but has no ADR/RFC or stakeholder review.
