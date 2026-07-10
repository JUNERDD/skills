---
name: code-review
description: Perform a deep, scoped review of a working tree, staged diff, commit range, branch diff, pull request, focused file set, or pasted code. Use for `/code-review`, PR or diff review, merge-safety assessment, and refreshed review reports. Begin with a read-only orchestration-assessment subagent that decides whether one reviewer or multiple specialist subagents are justified by the change scope and risk. Prioritize correctness, regressions, security, privacy, contracts, data, concurrency, migrations, and tests. Persist a versioned Markdown report and do not edit code or Git state unless the user separately requests fixes.
---

# Code Review

## Mission

Produce the deepest review that is practical for the requested scope. Findings and coverage evidence are the primary output. Praise, style preferences, and broad refactor suggestions are secondary.

The coordinating agent owns scope, final judgment, de-duplication, severity, and the persisted report. Subagents provide bounded analysis; never copy their conclusions into the report without independent synthesis.

## Required Resources

- Read [references/subagent-orchestration.md](references/subagent-orchestration.md) before delegating review work.
- Write the report from [references/report-template.md](references/report-template.md).
- Validate the completed report with `python scripts/validate_review_report.py <report-path>`.

## Hard Gates

- Before substantive review, launch exactly one read-only orchestration-assessment subagent.
- Before launching that assessor, inspect only enough Git and request metadata to identify the scope, baseline, changed-file inventory, diff size, and obvious constraints. Do not form findings first.
- Let the assessor decide whether specialist subagents add material value. Do not equate depth with agent count.
- If the environment has no subagent primitive, record `Subagent unavailable` and execute the same assessment protocol in the coordinator. Never claim a subagent ran when it did not.
- Keep every review subagent read-only. Do not edit files, stage, commit, push, reset, checkout, rebase, or mutate Git state.
- Do not make code changes during this skill unless the user explicitly changes the task from review to implementation.

## Scope and Identity

1. Resolve the requested scope: working tree, staged diff, commit range, branch diff, pull request, file set, or pasted code.
2. Choose the narrowest reasonable scope when none is explicit. Prefer staged changes when present; otherwise compare the working tree with `HEAD`.
3. Record the baseline and target precisely. Use commit SHAs when available.
4. Compute a scope fingerprint when practical from the baseline, target, changed paths, and normalized diff hash. Record why a fingerprint is unavailable.
5. Read requirements, issue text, PR description, design notes, migrations, and relevant contracts before judging intent.
6. Do not silently widen scope. Mark unrelated context as supporting evidence rather than reviewed change.

## Orchestration

1. Give the assessment subagent the scope identity, diff inventory, change statistics, touched subsystems, known requirements, and environment limitations.
2. Require a structured decision: `Single reviewer` or `Parallel specialists`, with rationale, risk dimensions, proposed partitions, overlap plan, and verification needs.
3. Follow the decision unless concrete new evidence invalidates it. Record any override and reason.
4. For parallel review, assign bounded, non-identical ownership. Typical angles include:
   - correctness, state, data flow, and API contracts
   - security, privacy, auth, permissions, and trust boundaries
   - tests, regressions, error paths, concurrency, and reliability
   - migrations, persistence, compatibility, integrations, performance, and operations
   - framework- or domain-specific semantics
5. Require each specialist to return candidate findings, covered areas, dismissed candidates, uncertainty, and evidence pointers.
6. Re-read the relevant code and evidence for every candidate that could enter the final report. Resolve conflicts explicitly and assign final `F#`, `T#`, and `A#` IDs only in the coordinator.

## Deep Review Contract

Review beyond changed lines whenever risk can propagate. Trace far enough to evaluate:

- callers, callees, shared utilities, adapters, and alternate entry points
- input validation, authorization, trust boundaries, secrets, privacy, and unsafe external effects
- state transitions, persistence, migrations, serialization, compatibility, rollback, and data loss
- retries, idempotency, ordering, caching, concurrency, races, timeouts, partial failure, and cleanup
- public API, CLI, UI, generated output, configuration, dependency, and deployment contracts
- positive, negative, boundary, regression, integration, and migration test coverage
- runtime behavior through focused, non-destructive commands when it materially changes confidence
- requirements and intentional behavior changes so intended changes are not misreported as defects

Use search, history, blame, runtime checks, or targeted tests only when they strengthen evidence. Passing lint, typecheck, or unrelated tests is hygiene evidence, not proof of behavioral safety.

Stop only when every changed review-relevant or unknown-impact area is accounted for, meaningful candidates have been adjudicated, and remaining blind spots are explicit.

## Completeness Contract

- Enumerate every distinct finding reasonably discoverable within the reviewed scope, not only the top risks.
- Maintain a `Review Coverage Ledger` with stable `A#` area IDs. Map every changed review-relevant or unknown-impact area to:
  - `Finding F#`
  - `Reviewed - no issue found`
  - `Not review-relevant`
  - `Not covered`
- Give every standalone test gap a stable `T#` ID and severity.
- Record meaningful dismissed or merged candidates in `Subagent Candidate Adjudication` or the evidence appendix.
- Mark the report `Incomplete` and identify exact uncovered surfaces when context, credentials, runtime, diff size, or other limits prevent complete coverage.
- Never present a partial review as complete.

## Findings and Evidence

Count one finding per distinct failure mode, affected contract, security boundary, data risk, or approval decision. Merge repeated manifestations of the same defect; split materially different impacts.

Prioritize:

- crashes, incorrect results, stale or lost data, availability failures, and broken edge cases
- user-visible, API, CLI, persistence, auth, permission, retry, ordering, caching, and integration regressions
- injection, unsafe deserialization, auth bypass, secret exposure, SSRF, XSS, CSRF, overbroad access, and unsafe filesystem or dependency use
- missing tests for risky changed behavior, especially fixes, permissions, migrations, concurrency, and failures
- maintainability only when it creates a concrete review risk

For every accepted finding:

- tie the claim to a location, behavior path, output, missing test, or coverage gap
- separate verified facts from inference
- state assumptions and reduce confidence when proof is incomplete
- include exactly one or two primary code links in `Look here first`
- record which reviewer proposed it and how the coordinator verified it

Do not invent defects. A clean result still requires a full coverage ledger, strongest blind spot, and verification record.

## Severity and Recommendation

Use `Blocker`, `Major`, `Minor`, and `Question` as defined in the report template.

Map unresolved findings and standalone test gaps to the recommendation in this order:

1. Any `Blocker` -> `Block`.
2. Otherwise any `Major` -> `Changes requested`.
3. Otherwise any approval-affecting `Question` -> `Discuss`.
4. Otherwise any review-relevant or unknown-impact `Not covered` area -> `Discuss`.
5. Otherwise any `Minor` -> `Pass with caveat`.
6. Otherwise -> `Pass`.

Downgrade an unproven suspected blocker rather than retaining a hand-wavy `Blocker`. Do not use `Question` for curiosity that cannot affect approval.

## Persistence and Handoff

- Always write a fresh Markdown report with schema `code-review/v2`.
- Generate a unique report ID and filename. Follow an existing repository report convention; otherwise use `tmp/reviews/YYYY-MM-DD-code-review-report-<random-id>.md`.
- Never overwrite an existing report.
- Persist scope identity, scope fingerprint, orchestration decision, specialist assignments, candidate adjudication, findings, test gaps, coverage, evidence, and a `Receiving Handoff` section.
- Keep the source review immutable after publication. Later implementation or disputes belong in a companion `receiving-code-review/v2` resolution report.
- Run the validator and fix every error before claiming the report is complete.

## Workflow

1. Resolve scope, baseline, target, and minimal diff inventory.
2. Launch the orchestration-assessment subagent.
3. Record and execute the single-reviewer or specialist plan.
4. Build the semantic diff inventory and `A#` coverage areas.
5. Trace changed control, data, security, persistence, integration, and test paths.
6. Run focused verification where it materially improves confidence.
7. Collect candidate findings and specialist coverage results.
8. Independently verify, de-duplicate, challenge, and classify every candidate.
9. Assign final `F#`, `T#`, and `A#` IDs.
10. Derive the recommendation from unresolved items and coverage.
11. Write the versioned report from the template.
12. Run `scripts/validate_review_report.py` and correct all failures.
13. Return a short summary with report path, recommendation, completion, severity counts, orchestration mode, and top risks.

## Final Self-Check

- The assessment subagent ran, or the report honestly records the unavailable fallback.
- The orchestration decision is supported by scope and risk, not arbitrary agent count.
- Every specialist candidate was verified, rejected, merged, or retained with evidence.
- Every changed review-relevant or unknown-impact area has an `A#` row.
- Every indexed finding has one matching card and every `Finding F#` area references a real finding.
- Every `Not covered` row has a reason and concrete next step.
- Recommendation mapping is exact.
- The report validator passes.
- Git state is unchanged.
