---
name: receiving-code-review
description: Consume a code-review Markdown report, PR feedback, or equivalent review comments; reconstruct each problem's complete execution chain before judging it; re-verify findings, intent, test gaps, and uncovered areas; challenge incorrect or stale claims; and implement only confirmed actions through a coding subagent. Use after code review to produce a lineage-aware disposition ledger, preserve settled product decisions, run at most one terminal post-implementation review for an initial review chain, and keep the user's Git index unchanged unless staging or publishing is explicitly requested.
---

# Receiving Code Review

## Mission

Treat the source review as a set of evidence-backed claims, not an unquestionable instruction list. Reconstruct each claim's complete execution chain before local judgment, account for every item, challenge errors with proof, then delegate only chain-verified implementation work to a coding subagent.

The coordinating agent owns intake integrity, final dispositions, implementation boundaries, patch acceptance, verification, and the persisted resolution report.

## Required Resources

- Read [references/re-review-orchestration.md](references/re-review-orchestration.md) before delegating re-review or coding.
- Write the resolution report from [references/disposition-template.md](references/disposition-template.md).
- Validate it with `python3 scripts/validate_disposition_report.py <resolution-report> --source-report <source-report>` when a canonical generation `0` report is available. For an explicitly requested generation `1` source, also pass `--parent-resolution <parent-resolution>`.

## Hard Gates

- Before substantive re-review or code edits, launch exactly one read-only re-review assessment subagent.
- Give the assessor both the current change scope and the complete source review results. It decides whether one verifier or multiple specialist subagents are justified.
- Allocate the resolution ID and path during intake so a generation `1` post-review can link the in-progress parent resolution.
- Before assigning any final disposition, reconstruct the complete execution chain for every `F#`, `T#`, and review-relevant or uncovered `A#`. Do not infer the whole failure mode from the reported line alone.
- Do not edit code until intake, scope identity, item enumeration, execution-chain reconstruction, and preliminary dispositions are complete.
- When at least one item requires code or test changes, launch at least one coding subagent. Do not implement those changes only in the coordinator.
- Keep re-review agents read-only. Give coding agents explicit file ownership, accepted item IDs, verification duties, and a no-staging constraint.
- If no subagent primitive is available, disclose the fallback and execute the same protocol in the coordinator. Never claim delegation that did not occur.
- Preserve staged changes exactly unless the user's current request explicitly asks to stage, commit, amend, push, or publish.
- Allow at most one automatic post-implementation `code-review` in a review chain. A source generation `1` is terminal and may be consumed only after an explicit current user request; it has no automatic post-review budget.
- Never automatically consume the report produced by post-implementation review. Return its remaining findings to the user or product owner.

## Source Artifact and Scope Integrity

Use the canonical `code-review` report when available. Treat the supplied review artifact as fixed input evidence during receiving.

1. Read the complete report, including contract, scope, orchestration, index, severity cards, test gaps, coverage ledger, candidate adjudication, evidence, handoff, and self-check.
2. Recompute or inspect the current scope fingerprint, baseline, target, changed paths, and Git state.
3. Build the source item universe:
   - every `F#` finding or approval-affecting question
   - every standalone `T#` test gap
   - every `A#` area marked `Not covered`
   - every intake mismatch as a new `I#` integrity item
4. Verify that the index, cards, test gaps, coverage rows, and handoff agree.
5. Capture the source review chain ID and generation. Preserve every source `F#`/`T#` issue key and fingerprint; generate the same canonical identity for unstructured feedback.
6. If the source generation is `1`, read its parent resolution and inherit matching `Intentional`, `Disproved`, `Stale`, and `Duplicate` decisions. Reopen only for changed code, governing contract, or material evidence, recorded as `kind:<code|contract|evidence>; ref:<concrete source>; change:<concrete delta>`. Placeholder references or changes do not reopen a settled decision.
7. If the source is stale or inconsistent, do not blindly implement it. Re-review the affected surfaces and create `I#` items. Do not start another code-review merely to replace a missing product decision.
8. For PR feedback or review notes that are not already in the canonical report structure, normalize each material claim into stable IDs and record the actual source type.

## Execution-Chain Reconstruction Gate

Prioritize the problem's whole execution chain before item-local reasoning. Build one reusable `EC#` record per distinct behavior path; multiple review items may reference the same chain.

Trace, in order:

1. real trigger, input, and semantic entry point
2. validation, authorization, feature/config gates, and alternate entries
3. control, data, and state propagation through callers, callees, adapters, queues, caches, and async boundaries
4. persistence, external calls, retries, ordering, idempotency, concurrency, timeout, partial failure, and cleanup
5. terminal user, API, CLI, data, security, operational, or test effect
6. authoritative expected-behavior basis and any settled parent-resolution decision

Mark each chain `Complete` or `Blocked`. A `Complete` chain must contain concrete evidence for every stage; when a stage has no applicable branch or effect, write `Checked: none - <reason>` instead of leaving it empty. A `Blocked` chain may produce only `Open` or `Unverifiable` with an evidence, coverage, or carried-forward action; it must never enter `Fix required` or `Test required`. `Intentional` requires authoritative user, product-owner, requirement, approved design, or public-contract evidence; code and history alone are insufficient.

## Re-Review Orchestration

1. Give the assessment subagent the source item universe, severities, disputed claims, scope drift, touched subsystems, existing evidence, and environment limits.
2. Give it the reconstructed `EC#` map and require `Single verifier` or `Parallel specialists`, with risk-based rationale, assignments, intentional overlap, and required evidence.
3. Use multiple angles when findings span independent risk domains, a high-severity claim is disputed, source coverage is incomplete, or different evidence methods are needed.
4. In parallel mode, partition by claim cluster or risk angle rather than asking every agent to repeat the full report.
5. Require an independent adversarial verifier for a challenged `Blocker` or security-critical `Major` when the environment supports it.
6. The coordinator must re-check every final disposition and resolve conflicts through stronger evidence, not voting.
7. When a verifier finds a materially distinct issue outside the frozen source-item universe, label it provisionally as `V#-N#` and return it in `Residual Risks`. Do not silently drop it, add it to the actionable set, or launch another review. Merge it into an existing item only when the semantic issue key is genuinely the same.

## Disposition Model

Give every `F#`, `T#`, `A#`, and `I#` exactly one final re-review verdict:

- `Confirmed` - the source claim still applies as written.
- `Narrowed` - a smaller failure mode or impact is proven.
- `Reclassified` - the claim applies but severity or item type changes.
- `Disproved` - stronger current evidence contradicts the claim.
- `Stale` - the source scope or code path no longer matches.
- `Duplicate` - another item fully represents the same failure mode.
- `Intentional` - evidence proves an intended product or contract change rather than a defect.
- `Unverifiable` - required evidence is unavailable; keep the approval risk explicit.
- `Open` - a material question or coverage gap remains unresolved.

Then assign an action state:

- `No change needed`
- `Fix required`
- `Test required`
- `Evidence/answer required`
- `Coverage verification required`
- `Carried forward`

Do not dismiss a blocker without evidence stronger than the source report. Do not use passing lint, typecheck, or unrelated tests as counter-evidence.

Enforce these compatibility rules:

- `Disproved`, `Stale`, `Duplicate`, or `Intentional` -> `No change needed` + `Not needed`.
- `Open` or `Unverifiable` -> `Evidence/answer required`, `Coverage verification required`, or `Carried forward`; never fix or test automatically.
- Only `Confirmed`, `Narrowed`, or `Reclassified` may enter `Fix required` or `Test required`, and only from a `Complete` execution chain.

## Formal Challenge Protocol

A challenge is allowed and expected when current evidence undermines the source review. Persist every material challenge as a `C#` card containing:

- source claim and source evidence
- counterclaim
- argument linking evidence to the counterclaim
- concrete code, runtime, test, contract, or history evidence
- limits and residual uncertainty
- settlement criterion that would decide the dispute
- final verdict and exact action-state effect, matching the disposition ledger verbatim

Distinguish disagreement from disproof. When evidence is incomplete, use `Narrowed`, `Unverifiable`, `Open`, or a lower confidence rather than declaring the source wrong.

## Implementation Delegation

After final dispositions are stable:

1. Build the actionable set from items marked `Fix required` or `Test required`.
2. State the intended changes, affected surfaces, regression/security/contract risks, verification plan, file ownership, and no-staging rule.
3. Launch one coding subagent by default. Use multiple coding agents only for disjoint file ownership or isolated worktrees with no shared generated artifacts or migration ordering.
4. Give the coding subagent only confirmed or explicitly accepted actionable items. Do not pass disproved, stale, duplicate, or intentional items as tasks.
5. Give it the complete referenced `EC#` records and the expected terminal behavior; preserve guards, alternate entries, persistence, failure handling, and external effects across the patch.
6. Require a focused patch, changed-file list, per-item mapping, tests run, residual risks, and any newly discovered issue.
7. Inspect the patch in the coordinator, reject unrelated churn, and independently run the most important verification.
8. Keep all new changes unstaged unless the current request explicitly authorizes staging or publication.
9. If no actionable item exists, record `Coding stage not required` and the evidence supporting that decision.
10. Make `Coding Assignments` exactly cover the actionable ID set. Make `Code Changes` exactly cover every item marked `Implemented` or `Verified`; each row must name the responsible agent, concrete files, focused change, and unrelated-churn check.

## Git State Hard Gate

Treat the index as user-owned state.

- Do not run `git add`, `git add -A`, `git add -p`, `git add -N`, `git commit`, `git commit --amend`, `git reset`, or equivalent index-mutating commands without explicit current-request authorization.
- If changes were already staged, preserve them exactly. Keep new fixes unstaged.
- If the source review covered the staged diff and code is changed, do not silently update the staged set. Record the working-tree fix and the scope drift.
- Avoid tools that stage as a side effect.
- If a coding subagent mutates the index, stop, inspect the before/after state, undo only its known changes without disturbing prior staged work, and disclose the incident.

## Persistence and Post-Implementation Review

- Write a fresh resolution report using the canonical `receiving-code-review` report contract; never overwrite the supplied review artifact.
- Follow a repository convention or use `tmp/reviews/YYYY-MM-DD-code-review-resolution-<source-report-id>-<random-id>.md`.
- Persist source identity, scope match, re-review orchestration, complete disposition ledger, challenge cards, coding delegation, patch mapping, verification, residual risk, and final Git state.
- Run the disposition validator and fix all structural errors.
- For a generation `0` source, run at most one generation `1` post-implementation `code-review` only when an independent review materially improves confidence. Limit it to the implementation delta plus the complete affected `EC#` chains, pass the generation `0` source report and in-progress resolution, and link the terminal report.
- Before using the post-review budget for initially unstructured feedback, persist the normalized claims as a canonical generation `0` code-review source artifact so generation `1` has verifiable ancestry.
- Queue material defects discovered by the coding agent as provisional `D#-N#` candidates for that single post-review. A distinct verifier discovery remains a provisional `V#-N#` residual unless it directly concerns the later implementation delta. Do not launch a separate immediate review. If no applicable post-review budget remains, record candidates as residual risks and return them to the user.
- Treat the generation `1` report as terminal. Do not invoke `receiving-code-review` again automatically, even when it contains findings.
- Do not claim resolution while any source item lacks a disposition or any implemented item lacks targeted verification.
- Keep the report-contract `Status` identical to final `Completion`; `Resolved` requires every actionable implementation to be `Verified` with matching assignment, change, and coordinator-verification evidence.

## Workflow

1. Locate and read the complete source review or normalize unstructured feedback.
2. Capture review-chain lineage, current Git state, and scope identity without mutating either; allocate the resolution ID/path.
3. Build the complete `F#`, `T#`, `A#`, and `I#` item universe with issue fingerprints.
4. Reconstruct and freeze the complete `EC#` execution chains.
5. Launch the re-review assessment subagent with the chain map.
6. Execute the single-verifier or specialist re-review plan, prioritizing end-to-end chain evidence.
7. Verify each item against its full chain, contracts, product intent, tests, runtime behavior, and relevant history.
8. Create formal `C#` challenges where source claims are contradicted or overstated.
9. Assign every item a compatible final verdict, action, and implementation state.
10. Derive the actionable implementation set.
11. Present the scoped implementation and verification plan.
12. Launch the coding subagent when code or tests must change.
13. Inspect the patch and run focused independent verification across the affected chains.
14. Use the one available post-review only when justified; then stop automatic review/receiving recursion.
15. Write and validate the canonical `receiving-code-review` resolution report.
16. Return a short summary with source report, resolution report, chain coverage, re-review mode, challenged items, implemented items, terminal post-review, residual risks, and unstaged Git status.

## Completion Gate

Do not claim completion until:

- every source `F#`, `T#`, and unresolved `A#` has exactly one disposition
- every source `F#`, `T#`, and unresolved `A#` references a complete or explicitly blocked `EC#` execution chain
- every intake inconsistency has an `I#` disposition
- every challenge has a claim, counterclaim, argument, evidence, limits, and settlement criterion
- every challenge's verdict and action effect exactly match its disposition row
- every actionable code/test item appears exactly once in `Coding Assignments`, and the coding subagent or unavailable fallback is disclosed
- every `Implemented` or `Verified` item appears exactly once in `Code Changes`
- every materially distinct verifier or coding discovery outside the source universe is returned as a provisional residual candidate, not silently dropped or made actionable
- every changed surface has targeted verification
- the verdict/action/implementation matrix is valid and blocked chains never become actionable
- post-review use is within budget, any generation `1` report is linked as terminal, and automatic follow-on receiving is `No`
- the resolution validator passes
- pre-existing staged work remains unchanged
