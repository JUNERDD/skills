# Reuse Playbook

Use this reference when the task is about team/org-level治理, shared assets, platform capabilities, or reducing repeated work beyond one local refactor.

## Principles

1. **Reuse knowledge, not just text.** The expensive duplication is duplicated business rule, platform workflow, integration contract, or decision rationale. Identical code can be acceptable if the domains will diverge; different code can still be duplicate if it encodes the same rule.
2. **Discoverability is a product requirement.** A reusable asset must be findable through names, tags, examples, catalog metadata, docs, and search terms that match how consumers describe their problem.
3. **Ownership precedes centralization.** Shared assets need maintainers, contribution path, release/deprecation policy, and support expectations. Ownerless reuse becomes a bottleneck or a stale dependency.
4. **Prefer paved roads over mandates.** Reduce reinvention by making the recommended path faster, safer, and better documented than custom work.
5. **Record decisions.** Use ADRs/RFCs for material choices so teams do not re-litigate the same build-vs-reuse debate.
6. **Optimize for lifecycle cost.** Include adoption effort, integration risk, support load, security, license, future change cadence, and exit cost—not only initial build time.

## Common root causes

- Assets exist but are hidden across repos, wikis, tickets, or team tribal knowledge.
- Existing asset is hard to adopt: missing examples, unstable API, unclear versioning, poor error messages, or no owner.
- Teams have different names for the same capability, making search fail.
- Delivery pressure rewards local copy/paste and ignores future maintenance.
- Platform teams expose raw complexity instead of a self-service golden path.
- Architecture decisions are buried in PR comments, chat threads, or prompts.
- Incentives reward new builds more than improving shared capabilities.

## Asset taxonomy

Classify findings and recommendations using these categories:

| Category | Examples | Reuse unit | Typical owner |
|---|---|---|---|
| Code utility/library | validation, auth client, date logic, SDK wrapper | package/module | library maintainer or domain team |
| UI/design component | button, table, form pattern, dashboard template | component or design-system token | design system/platform team |
| Service/API | identity, notifications, billing, audit log | API or managed service | service-owning team |
| Platform workflow | CI/CD, Terraform module, observability bootstrap | golden path/template | platform team |
| Data/ML asset | schema, feature pipeline, evaluation harness | dataset/schema/pipeline | data product owner |
| Knowledge/decision | ADR, runbook, policy, standard | doc/catalog entry | architecture or owning team |

## Intervention patterns

| Pattern | Use when | Avoid when | Output |
|---|---|---|---|
| Adopt as-is | Existing asset fits and is maintained | Migration breaks compatibility | Usage PR, docs link, consumer added |
| Adapt via extension | Asset fits most needs and has extension seams | Changes are one-off hacks | Upstream contribution, new option, tests |
| Wrap/facade | Consumers need stable API over external/internal variability | Wrapper hides too much or becomes another platform | Thin wrapper, contract tests, owner |
| Extract shared module | Same knowledge appears in multiple places and change cadence is aligned | Similarity is accidental or domains will diverge | Package/module, versioning, migration PRs |
| Merge/consolidate services | APIs overlap and operating two services adds cost/risk | Teams need separate scaling/security domains | Target architecture, migration plan |
| Publish golden path | Repeated workflow has common safe route | Workflow is still experimental or user feedback is absent | Template, automation, troubleshooting guide |
| Sunset/archive | Duplicate is unused or superseded | Consumers still depend on it | Deprecation notice, telemetry, removal plan |
| Justified divergence | Local needs, compliance, or domain semantics differ | Divergence is only historical accident | ADR/RFC explaining exception and review date |

## Operating model for sustained reuse

1. **Create a catalog.** Track name, type, owner, lifecycle, capability, interface, examples, docs, maturity, dependencies, consumers, and known alternatives.
2. **Put metadata near code.** Keep catalog metadata in source control or another authoritative system that changes with the asset.
3. **Assign maturity.** Example rings: `adopt`, `trial`, `assess`, `hold`. Make “adopt” assets boring, well-supported, and easy to start.
4. **Use contribution contracts.** Define who approves changes, expected review time, compatibility rules, and how consumers request features.
5. **Add feedback loops.** Treat repeated “how do I…” questions, failed builds, forks, and copy-paste as product feedback for the reusable asset.
6. **Make exceptions visible.** When a team builds instead of reuses, require a short decision record with reason, review date, and exit criteria.

## Metrics

Choose a few metrics tied to behavior, not vanity:

- Catalog coverage: percentage of reusable assets with owner, lifecycle, docs, examples, and consumers.
- Reuse adoption: imports/API calls/template use by consumer team/repo.
- Duplication burn-down: number of exact/near duplicates resolved or documented as exceptions.
- Time-to-first-success: how long a new consumer needs to adopt a recommended asset.
- Support load: repeated questions, failed self-service attempts, and platform escalation themes.
- Decision hygiene: material build-vs-reuse choices with accepted ADR/RFC and review date.
- Staleness: assets with no maintainer activity, no consumers, or outdated dependencies.

## Anti-patterns

- **Common-utils dumping ground:** unrelated helpers in one package with no domain owner.
- **Forced DRY:** abstracting before stable requirements reveal shared knowledge.
- **Shelfware catalog:** inventory exists but is stale, ownerless, or disconnected from developer workflow.
- **Golden path without feedback:** platform path hides complexity but does not expose actionable errors or collect user pain.
- **Shadow fork:** a local copy of a shared asset diverges without versioning, ownership, or ADR.
- **Build-vs-buy theater:** alternatives are listed, but decision criteria and consequences are not recorded.
