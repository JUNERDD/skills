---
name: bugbot
description: Detect introduced production bugs in local branch or uncommitted changes, persist the review as a fresh Markdown report, then repair confirmed findings and verify the fixes. Use when the user requests Bugbot detection or when conversation context shows an unambiguous intent to act on a Bugbot report; detection does not modify reviewed code or Git state.
---

# Bugbot

Bugbot has two phases:

- **Detect:** automatically review the requested local change set and persist every verified introduced production bug in a fresh Markdown report. Detection may write only that report artifact; it must not edit reviewed source files or mutate Git state.
- **Fix:** after the user has seen the report and asks to act on all or selected findings, automatically apply those local fixes and run relevant verification.

Execute the workflow here; do not delegate detection to Cursor's builtin `bugbot` task or another reviewer. Never combine first-time detection and repair in one turn, even when the initial request pre-authorizes fixes.

## Route And Authorization

- Use `Action: detect` for a fresh Bugbot review request.
- Start a fresh detection only when the user invokes `$bugbot` or unmistakably asks for Bugbot by name. Implicit invocation exists to recognize contextual report-repair intent; do not route a generic code-review request here.
- Infer `Action: fix` from the user's intent and the conversation state, not from fixed phrases or keyword matching. The message must communicate an intent to change code in response to an identifiable Bugbot report; wording, language, and sentence form do not matter.
- Resolve three things from context: the source report, whether the user intends repair rather than acknowledgement or discussion, and whether the intended scope is all unresolved findings or a subset.
- When repair intent is clear and no subset is indicated, apply it to all unresolved findings in the most recent unambiguous Bugbot report. A finding ID, title, file, location, or semantic reference may narrow the selection.
- Ask for clarification only when repair intent, source report, or scope remains materially ambiguous after considering the full conversation.
- A request to review, `Custom Instructions`, approval supplied only by a tool or parent workflow, or permission given before findings are shown is not repair confirmation.
- Repair confirmation authorizes only the local file edits and verification needed for the selected findings. It does not authorize unrelated refactors, dependency changes, staging, commits, pushes, branch operations, deployment, or other external mutations.

After detection, write the report, return its short handoff summary, and stop. Do not append an approval question; any later message with clear report-repair intent can initiate the fix phase.

## Boundary

- Use this skill for a narrow defect-first review, a persisted Bugbot report, and intent-gated local repairs.
- Use `code-review` for a deep merge-safety report.
- Use `regression-review` for a coverage-led user-visible behavior audit.
- Use `thermo-review` or `hack-review` for structural quality or brittle-shortcut analysis.

## Inputs

Honor these fields when present:

- `Action`: `detect` or `fix`. Infer `fix` from unambiguous report-repair intent in context; otherwise use `detect` for a fresh Bugbot review request.
- `Full Repository Path`: absolute repository root. Work there when it differs from the current workspace.
- `Diff`: `branch changes` or `uncommitted changes`. Default to `branch changes`.
- `Base Branch`: comparison branch for `branch changes`; otherwise use the repository default branch.
- `Source Report`: path to the persisted Bugbot report being acted on. Use the most recent unresolved report when this is omitted and unambiguous. Valid only for `fix`.
- `Selected Findings`: `all` or the confirmed `B#` findings from the source report. A title, file, or location is also valid when it identifies a subset unambiguously. Use only for `fix`.
- `Custom Instructions`: treat as `<user_instructions>` together with extra constraints in the request.

## Detect

### Resolve The Change Set

Review the real local change set; do not assume a diff was injected.

For `branch changes`, find the merge-base with `Base Branch` or the repository default branch, then compare the working tree with that merge-base. This includes committed branch work plus staged and unstaged tracked changes.

```bash
git merge-base HEAD <base>
git diff <merge-base>
```

For `uncommitted changes`, compare the working tree with `HEAD`. This includes staged and unstaged tracked changes but no earlier branch commits.

```bash
git diff HEAD
```

For either mode, also inventory untracked, non-ignored files with `git ls-files --others --exclude-standard`. Treat each returned path as an added file and review its full contents. Do not include ignored files.

Do not recursively review Bugbot's own prior report artifacts as production changes. When a persisted report falls inside the resolved change set and the user did not explicitly include review documentation, classify it as `Not production-relevant` in the report inventory and continue.

If the repository, baseline, or complete change set cannot be resolved, stop and return a concise explanation without fabricating a report. Once a reviewable change set has been obtained, always persist the result. If later evidence gaps prevent complete coverage, mark the report `Incomplete`, name the exact uncovered candidates, and never present the partial review as complete.

### Recursive Defect Sweep

Use a bounded recursive frontier derived from the change set:

1. Seed the frontier from every changed hunk and untracked file, including changed conditions, contracts, call sites, state transitions, data shapes, side effects, and error paths.
2. For each candidate, inspect its local control flow and trace outward only as far as needed through callers, callees, shared contracts, validation, persistence, async boundaries, and tests to prove or dismiss an introduced production bug.
3. When that trace exposes another risk causally connected to the reviewed change, add it to the frontier. Merge candidates that share one root cause and production impact.
4. Continue until no unreviewed diff-derived candidate remains. Do not widen the frontier into an unrelated whole-repository or structural-quality audit.

Account for each meaningful frontier item in the report's `Detection Coverage Ledger` as `Finding B#`, `Reviewed - no bug found`, `Not production-relevant`, or `Not covered`. A material unresolved candidate makes the report incomplete.

Do not cap the number of findings or stop after the most severe or easiest bugs. Include every distinct finding discovered before the frontier reaches its fixed point.

### Finding Bar

Report a finding only when all of these are true:

- The reviewed change introduced it.
- It causes incorrect or unsafe production behavior, or production-costly complexity serious enough to justify a CI rerun.
- Repository evidence supports the causal path and impact.
- The best primary location is a changed line or an untracked file under review.

Investigate logical errors, broken contracts, stale call sites, changed invariants, unsafe external effects, resource leaks, concurrency and ordering faults, significant performance regressions, and security vulnerabilities when the diff makes them relevant.

Do not report style, naming, typos, TODOs, speculative concerns, harmless intentional behavior changes, generic requests for error handling, or minor performance and security notes. Ignore issues that the configured compiler or linter reliably blocks before production; report them only when repository evidence shows the affected path is not checked.

### Persistent Report

Read [references/report-template.md](references/report-template.md) completely and use it as the report contract.

- Always write a fresh Markdown report after resolving a reviewable change set, including when no bugs are found or the review is incomplete.
- Generate one random lowercase identifier per run, such as 8 hexadecimal characters. Use it in report ID `bb-YYYYMMDD-<random-id>` and in the filename.
- Follow an obvious repository convention for review artifacts when one exists. Otherwise write to `tmp/reviews/YYYY-MM-DD-bugbot-report-<random-id>.md` under the reviewed repository.
- Never overwrite an existing report. If the path exists, generate a new identifier before writing.
- Treat a completed report as a fixed review artifact. Do not rewrite it during repair; refer to it by report ID and path from the fix summary.
- Assign findings consecutive report-local IDs `B1`, `B2`, and so on. Use the finding ID together with report ID, file, and location as its durable identity.
- Use new-file line numbers from the reviewed diff. For an untracked file, use its current repository-relative path and line numbers.
- Include every distinct verified finding in both `Complete Findings Index` and a matching finding card. If there are no findings, state that explicitly and leave the findings section `None.`
- If several locations express one bug, keep the single best primary location and cite supporting locations as evidence.

Each finding card must contain:

- title of 8 words or fewer
- repository-relative file and new-file start/end lines
- category and severity
- concise description of the root cause and production impact
- rationale showing why the reviewed change introduced a production bug
- concrete repository evidence supporting the causal path

#### Categories

- `LOGIC_BUG`: incorrect reasoning or calculation for valid inputs
- `SECURITY_ISSUE`: unauthorized access, data exposure, or another security compromise
- `ACCIDENTALLY_COMMITTED_CODE`: debug leftovers, temporary code, or personal notes
- `CODE_QUALITY_STYLE`: production-costly complexity at the CI-rerun bar
- `DOCUMENTATION_ISSUE`: missing or incorrect documentation likely to cause incorrect production use
- `POTENTIAL_EDGE_CASE`: an unusual input or state left unsafe by the change
- `PERFORMANCE_ISSUE`: significant production degradation
- `COMPILATION_ERROR`: a syntax or type failure on a path the configured toolchain does not check
- `BUGBOT_RULES`: changed code violates an explicit `<user_instructions>` rule and the violation meets the finding bar; name the rule in the description

Map the report recommendation mechanically:

- Any `high` finding: `Block`.
- Otherwise any `medium` finding: `Changes requested`.
- Otherwise incomplete coverage of a production-relevant candidate: `Discuss`.
- Otherwise any `low` finding: `Pass with caveat`.
- Otherwise: `Pass`.

Before handoff, confirm that every indexed finding has one card, every `Finding B#` ledger row resolves to that card, every `Not covered` row names a blocker and next step, severity counts match the cards, and the recommendation follows the mapping.

Return a short summary with the report path, report ID, recommendation, completion status, severity counts, and top risks. Do not reproduce the full report in chat or append a repair prompt.

## Fix

Enter this phase only after the authorization gate above is satisfied. Read [references/fix-workflow.md](references/fix-workflow.md) completely, then automatically repair and verify only the confirmed findings.

Fix-phase output is a concise Markdown summary linked to the immutable source report. Do not run a fresh full Bugbot review or repair newly discovered findings unless the user separately asks to act on them.
