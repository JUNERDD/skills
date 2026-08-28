# Report-Scoped Fix Workflow

Use this workflow only for the `fix` phase selected by `SKILL.md`.

## Validate Confirmation

Before editing:

1. Resolve the immutable source report from `Source Report` or the unambiguous report path in the preceding Bugbot handoff. Confirm that it exists, declares `Report type: bugbot`, and contains the selected findings.
2. Determine repair intent semantically from the full conversation. Do not use a phrase list, keyword whitelist, exact command shape, language assumption, or literal `$bugbot` mention as the gate. Confirmation exists when the user intends code changes that address findings in an identifiable Bugbot report; acknowledgement, questions, or discussion without change intent do not authorize repair.
3. Infer scope from the same context. When repair intent is clear and no subset is indicated, select all unresolved findings in the most recent unambiguous report. Resolve a subset by `B#`, title, file, location, or another semantic reference that identifies it confidently. Treat report ID, finding ID, file, and location together as the durable finding identity; do not infer a subset from severity alone.
4. Ask for clarification only when repair intent, source report, or selected scope is genuinely ambiguous after using the available conversation. Do not require the user to repeat the skill name, report path, or finding details already present.
5. If the relevant checkout changed enough that a selected finding can no longer be mapped confidently, do not reuse the old confirmation. Run a fresh detection, persist a new report, and require repair intent to be established against that new report.

Confirmation applies only to the selected findings. A newly discovered bug, an unrelated cleanup, or a materially broader behavior change requires separate user confirmation.

Treat the source report as fixed input. Never rewrite it to mark findings resolved or append repair notes.

## Reverify And Repair

1. Work in the confirmed repository and read its applicable instructions.
2. Inspect Git status and preserve unrelated user changes, staged state, and untracked files.
3. Reverify each selected finding against the current code and its causal path. Mark stale, already-fixed, or disproved findings without editing for them.
4. Apply the smallest cohesive repair that removes the verified root cause while preserving intended behavior and public contracts.
5. Include directly necessary tests when they are part of proving the confirmed repair. Do not turn a local fix into a broad refactor.
6. Run targeted tests, type checks, lint, builds, or non-destructive runtime checks in proportion to the affected behavior.
7. Inspect the resulting diff and confirm that each selected root cause is removed, no unrelated file changed, and the Git index, branches, and remotes were untouched.

Repair automatically after valid confirmation; do not ask for another approval for ordinary in-scope local edits or verification. Ask again before dependency changes, destructive actions, external mutations, or scope expansion.

If verification fails, diagnose and adjust only while new evidence supports another correction within the confirmed scope. Do not repeat a failed approach blindly. Stop and report the remaining failure when the next attempt would broaden behavior, require new authority, or lack an evidence-backed in-scope correction.

Do not stage, commit, push, rebase, switch branches, deploy, publish, or modify external systems unless the user separately requests that exact action.

## New Findings

Targeted verification may expose another defect. Do not repair it automatically unless it is the same root cause and an inseparable part of the confirmed repair. Report every distinct new finding as unconfirmed work. A later message whose contextual intent is to address that finding is sufficient; do not require special syntax.

Do not start an automatic detect-fix-detect loop. A fresh full Bugbot review is a separate user-requested phase.

## Output

Return a concise Markdown summary containing:

- source Bugbot report ID and path
- confirmed findings fixed, with affected files
- selected findings not fixed and why
- verification commands and outcomes
- distinct new or remaining issues that still require confirmation
- confirmation that Git staging, commits, branches, remotes, and external systems were left unchanged
