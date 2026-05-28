---
name: plan-mode
description: Plan complex, ambiguous, risky, or multi-file work before editing or executing. Use when the user asks for a plan, says to stay in plan mode, asks to design an implementation, needs architecture or tradeoff analysis, or when a task requires clarification, read-only research, route/data-flow tracing, broad codebase exploration, or approval before changes. This skill keeps the agent in a no-mutation planning boundary until the user approves a concrete plan.
---

# Plan Mode

## Overview

Use this skill to hold a strict planning boundary: gather evidence with read-only tools, resolve blocking ambiguity, produce a concrete approval-gated plan, and only then move to implementation if the user approves.

Read `references/architecture.md` only for complex planning cases involving tool policy, read-only subagent exploration, diagrams, multi-system data flow, or non-trivial handoff from an approved plan to execution.

## Core Contract

Start in discovery, not implementation.

- Do not edit files, create files, delete files, change settings, stage commits, install packages, start write-oriented scripts, or run commands with side effects while in plan mode.
- Use read-only inspection: read files, search code, inspect diagnostics, check existing terminal state, review documentation, and ask focused questions.
- Treat user changes and dirty working trees as user-owned. Plan around them; do not revert or normalize them.
- If the request is clear and narrow enough that no plan is useful, answer directly or propose switching to execution instead of manufacturing ceremony.

## Planning Workflow

1. Restate the objective in one or two sentences.
2. Identify the planning boundary: what must not change yet, what evidence is needed, and what approval is required.
3. Research only what is needed to make the plan accurate. Prefer parallel read-only exploration when independent areas can be checked at the same time.
4. Ask the user for missing decisions before writing the final plan when ambiguity changes the implementation materially.
5. Present a concise, actionable plan through the platform's plan or approval mechanism when available; otherwise ask the user to approve a markdown plan explicitly.
6. Do not execute the plan until the user approves or clearly switches to implementation.

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

## Plan Shape

Make the plan easy to accept or reject.

- Name the files or modules likely to change.
- Include the implementation sequence, validation commands, and any expected non-goals.
- Call out tradeoffs only when they affect the chosen approach.
- Include concise code snippets only when they clarify a non-obvious target.
- Use diagrams for architecture or data-flow plans when they reduce ambiguity.
- Never include unresolved questions inside the final plan; ask them before producing it.

## Handoff To Execution

After approval, switch modes or state that execution is beginning.

- Re-check the latest user message before acting, especially after a long pause or context transition.
- Convert plan items into task tracking only after approval when task tracking is useful.
- Keep edits scoped to the approved plan. If implementation discovers a materially different path, pause and return to planning.
- Run the validation promised in the plan, or explain why it was skipped.
