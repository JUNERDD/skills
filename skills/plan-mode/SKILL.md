---
name: plan-mode
description: Cursor-style Plan Mode for complex, ambiguous, risky, or multi-file work before editing or executing. Use when the user asks for a plan, says to stay in plan mode, asks to design an implementation, asks to write or save a project-local plan file, needs architecture or tradeoff analysis, or when a task requires clarification, codebase research, route/data-flow tracing, broad exploration, or approval before changes. This skill creates or updates a disk-backed editable Markdown plan file by default, researches the codebase, asks clarifying questions, records file/code references and todos, invokes `$grill-me` for non-trivial pressure-testing, then builds only from the approved plan.
---

# Plan Mode

## Overview

Use this skill to mirror Cursor's Plan Mode core loop: create a disk-backed editable Markdown plan, research the codebase into that plan, ask clarifying questions, update the plan's file references and todos, then build only from the approved plan. The plan file is the source of truth; chat is only a summary and control surface.

Read `references/architecture.md` only for complex planning cases involving tool policy, read-only subagent exploration, diagrams, multi-system data flow, or non-trivial handoff from an approved plan to execution.

## Core Contract

Start with a plan document, not implementation.

- Do not edit implementation files, delete files, change settings, stage commits, install packages, start write-oriented scripts, or run commands with side effects while in plan mode.
- Use read-only inspection: read files, search code, inspect diagnostics, check existing terminal state, review documentation, and ask focused questions.
- Create and update planning artifacts only: the required Markdown plan file and `$grill-me`'s Q&A log and planning-ready outcome files when `$grill-me` is invoked.
- Treat the plan as an editable file. If the user edits it directly, reread it before changing the plan or building from it.
- Treat user changes and dirty working trees as user-owned. Plan around them; do not revert or normalize them.
- If the request is clear and narrow enough that no plan is useful, answer directly or propose switching to execution instead of manufacturing ceremony.

## Planning Workflow

1. Create or reuse the Markdown plan file immediately, then cite its path.
2. Research the codebase, docs, diagnostics, and relevant conventions with read-only tools.
3. Update the plan with concrete file paths, code references, discovered constraints, and unresolved questions.
4. Ask focused clarifying questions when requirements would change the plan. After each answer, update the plan file before moving on.
5. Maintain `Plan Todos` as editable checklist items. Include dependencies, selected todos, and enough detail for another agent to build from the plan.
6. Invoke `$grill-me` before approval when the plan is non-trivial enough to have meaningful assumptions, tradeoffs, failure modes, rollout/rollback concerns, or scope edges. Store pointers to the finalized transcript and outcome in the plan.
7. Mark the plan ready only when questions are resolved or explicitly blocking, the todos are concrete, and validation is named.
8. Run the artifact check and fix any missing section or placeholder before asking for approval.
9. Ask the user to approve building from the plan. Chat or platform-plan output must only summarize the plan and point to the file.
10. After approval, switch to execution and build from the plan file. If the user approves only selected todos, execute only those items.

## Grill-Me Pressure Test

Use `$grill-me` the way `$split-commits` uses `$git-commit`: delegate the specialized step instead of recreating it.

- Invoke `$grill-me` for architecture plans, broad implementation plans, migration plans, risky operational changes, product behavior decisions, and any plan where hidden assumptions could materially change execution.
- Skip `$grill-me` only when the task is narrow, already decided, or purely mechanical and a pressure-test would not change the plan.
- Let `$grill-me` ask one logged question at a time and follow its logging/finalization rules. Do not ask ad hoc pressure-test questions and then log them later.
- Treat `$grill-me`'s transcript and planning-ready outcome as planning artifacts allowed before implementation approval.
- After `$grill-me` finalizes, write links to the transcript and outcome paths in the plan. Include only a terse status or one-line summary in the plan; do not paste the full outcome content because it may be large.

## Plan Artifact Rules

The Markdown plan file is mandatory and behaves like Cursor's editable plan document.

- Do not use the platform plan or chat message as the only approval artifact. Those may summarize the plan, but they do not replace the file.
- Skip the plan file only when the user explicitly says not to write one or the environment cannot write files. In that case, say why no plan file was written.
- If the user provides a path, use it. Otherwise reuse the repository's existing plan location or template. If none exists, use `docs/plans/<YYYY-MM-DD>-<short-topic>.md`.
- Keep planning artifacts as the only allowed writes in plan mode. Creating parent directories for a requested plan file or `$grill-me` log/output is allowed only when needed for those artifacts.
- Include status, summary, clarifying questions, file/code references, plan todos, build instructions, validation, risks, and approval state.
- Use Markdown checkboxes for todos. Keep them editable and stable enough that selected todos can be handed to a new execution pass.
- Mark unfinished artifacts as `Draft - awaiting approval`. Do not ask for implementation approval until blocking questions are resolved or recorded as explicit blockers.
- If the plan changes after feedback, update the artifact before asking for approval again.
- In the chat response, summarize the plan briefly and provide the plan file path.

### Plan Artifact Helper

Use `scripts/plan_artifact.py` to lower the chance of forgetting the file.

Resolve the helper:

```bash
workspace_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
helper=""
for candidate in \
  "$workspace_root/skills/plan-mode/scripts/plan_artifact.py" \
  "$HOME/.agents/skills/plan-mode/scripts/plan_artifact.py" \
  "$HOME/.codex/skills/plan-mode/scripts/plan_artifact.py"
do
  if [ -f "$candidate" ]; then
    helper="$candidate"
    break
  fi
done
[ -n "$helper" ] || { echo "plan_artifact.py not found" >&2; exit 1; }
```

Create a draft plan file before final approval:

```bash
plan_file="$(python3 "$helper" init --workspace "$workspace_root" --title "<plan title>")"
```

If the user gave a path:

```bash
plan_file="$(python3 "$helper" init --workspace "$workspace_root" --title "<plan title>" --path "<path>" --reuse-existing)"
```

After filling the plan file, verify it before asking for approval:

```bash
python3 "$helper" check "$plan_file"
```

If the check fails because required sections or placeholders remain, update the plan file and rerun the check. Do not ask for implementation approval until the check passes or until you explicitly report why it cannot pass.

## Clarification Rules

Ask questions early when the answer changes the plan.

- Ask at most one or two critical questions at a time.
- Use structured choices when the environment provides a question or clarification tool.
- Offer a sensible default when one exists, but do not hide product, data, or safety assumptions inside the plan.
- Do not ask about trivia that can be answered by reading the codebase or existing docs.

## Research Rules

Keep research proportional to risk.

- For small tasks, read the directly relevant files and stop.
- For large codebases, use read-only subagents or semantic search to map ownership boundaries, routes, data contracts, and verification surfaces.
- If using subagents, give each one a bounded read-only objective and ask for paths, evidence, blockers, and residual risks.
- Avoid redoing a delegated investigation in the foreground unless the result is blocking and unavailable.

## Cursor-Style Plan Shape

Make the plan easy to accept or reject.

- Name the files or modules likely to change, with code references when useful.
- Keep a live todo checklist that can be edited, selected, and built from.
- Include build notes that say how to execute the plan after approval.
- Include validation commands and any expected non-goals.
- Call out tradeoffs only when they affect the chosen approach.
- Include concise code snippets only when they clarify a non-obvious target.
- Use Mermaid diagrams inside the plan when they reduce ambiguity.
- Never include unresolved questions inside the final plan; ask them before producing it.

## Handoff To Execution

After approval, build from the plan file.

- Re-read the latest user message and the plan file before acting, especially after a long pause or context transition.
- Execute only approved todos. If the user selected a subset, leave the other plan todos untouched.
- Keep edits scoped to the approved plan. If implementation discovers a materially different path, pause, update the plan, and ask again.
- Run the validation promised in the plan, or explain why it was skipped.
