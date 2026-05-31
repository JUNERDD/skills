---
name: reduce-reinvention
description: Identify, prevent, and remediate 重复造轮子 across code, libraries, services, templates, docs, platform workflows, and architecture decisions. Use when asked to audit duplicated implementations, search for existing reusable assets before building, decide build-vs-reuse/buy, consolidate similar components/tools/APIs, create reuse catalogs, write ADR/RFC/migration plans, establish golden paths/paved roads, or improve discoverability, ownership, and governance for reusable assets.
---
# Reduce Reinvention

Reduce duplicated effort by making existing assets discoverable, assessing whether reuse is justified, and turning repeated work into maintained shared capabilities without forcing premature abstraction.

## Core workflow

1. **Frame the scope.** Identify the capability being duplicated, the affected repos/teams/domains, target outcome, constraints, and whether the user wants a quick audit, a refactor plan, a governance model, or an implementation patch.
2. **Search before building.** Inspect local code, docs, package manifests, design systems, service catalogs, ADRs/RFCs, tickets, and team conventions before proposing new work. When external alternatives, current package health, pricing, licenses, or APIs matter, research current sources before deciding.
3. **Classify the duplicate.** Label each finding as exact copy, near clone, same business rule, same platform workflow, overlapping service/API, duplicated template/docs, abandoned fork, or justified divergence. Treat similarity as a clue, not proof.
4. **Decide reuse strategy.** Prefer reuse when the existing asset is fit, owned, maintained, secure, compatible, and cheaper to adopt than to rebuild. Prefer local divergence when domains are likely to evolve separately or abstraction cost exceeds duplication cost.
5. **Choose an intervention.** Recommend one of: adopt as-is, adapt through extension points, wrap behind a stable façade, extract a shared module, merge services, publish a template/golden path, deprecate a duplicate, archive dead assets, or document a justified exception.
6. **Make reuse obvious.** Add or update catalog metadata, owner, lifecycle, examples, getting-started path, decision record, migration guide, tests, and feedback channel. A reusable asset without owner and examples is usually just hidden maintenance debt.
7. **Plan safe migration.** Move in small behavior-preserving steps with tests, rollback points, compatibility notes, and a deprecation schedule. Keep user-facing behavior stable unless explicitly changing product semantics.
8. **Measure the loop.** Track catalog coverage, duplicate candidates resolved, reuse adoption, consumers migrated, build-vs-reuse ADRs, support load, lead time, and stale/ownerless assets.

## Use bundled resources

- For the end-to-end practice model, read [references/reuse-playbook.md](references/reuse-playbook.md).
- For repo/org audit tactics, search queries, and evidence gathering, read [references/audit-checklist.md](references/audit-checklist.md).
- For build-vs-reuse scoring and recommendation rules, read [references/decision-matrix.md](references/decision-matrix.md).
- For ready-to-fill outputs, read [references/templates.md](references/templates.md).
- To scan a repository for duplicate-code and reinvention signals, run:
  ```bash
  python3 scripts/reinvention_audit.py <repo-path> --output reinvention-audit.md
  ```
- To produce a lightweight reusable-asset inventory, run:
  ```bash
  python3 scripts/reuse_catalog.py <repo-path> --output reuse-catalog.md
  ```
- Treat script output as candidate evidence. Confirm semantics, ownership, consumers, and change cadence before recommending consolidation.

## Output expectations

When delivering an audit, decision, or plan, include:

- Evidence: file paths, symbols, repo/package names, docs, search terms, owners, and known consumers.
- Confidence: high/medium/low plus why the evidence supports or weakens the duplicate hypothesis.
- Recommendation: adopt, adapt, wrap, extract, consolidate, sunset, or justify divergence.
- Cost/risk: migration effort, test surface, security/license concerns, owner load, and compatibility risk.
- Next actions: minimal PRs/tasks, owners, acceptance criteria, and the metric that proves reinvention decreased.

## Guardrails

- Do not eliminate duplication solely because code looks alike; first verify shared domain knowledge, change cadence, and future evolution.
- Do not create a shared library, platform service, or golden path without an accountable owner, examples, versioning/deprecation policy, and support expectations.
- Do not centralize every variation; sometimes duplication is cheaper than an unstable abstraction.
- Do not rely only on automated clone detection. Combine script output with code review, domain context, ownership data, and usage evidence.
- Do not leave decisions implicit. For material choices, create or update an ADR/RFC that records context, alternatives, consequences, and status.
