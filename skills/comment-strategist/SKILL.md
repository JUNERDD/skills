---
name: comment-strategist
description: Add or rewrite code comments with calibrated granularity so they explain intent, constraints, data meaning, contracts, and control-flow decisions instead of translating syntax. Use when Codex is asked to document existing code, improve low-value comments, add structured comments to functions, interfaces, classes, types, fields, exported constants, configuration objects, state transitions, or complex internal logic while preserving the repository's existing comment language and style.
---

# Comment Strategist

Add durable, high-value comments that help a reader understand what the code is responsible for, why a branch exists, what a field means, and where misuse or misunderstanding is likely.

Prefer TypeScript and JavaScript conventions when the target code is TS/JS. Apply the same semantic rules to other languages while matching the local documentation style.

## Workflow

1. Read the target file and identify the top-level definitions first.
2. Detect the prevailing comment language, style, and density from the current file and nearby files.
3. Rank comment candidates by value:
   - top-level functions, classes, interfaces, types, exported constants, and core configuration objects
   - complex public helpers and reusable internal utilities
   - fields, options, state variants, and config entries whose meaning is part of the contract
   - non-obvious control-flow blocks inside complex functions
4. Choose a comment granularity level for each candidate before writing, using the rules below.
5. Replace or remove low-value comments before adding new ones so the file keeps one clear documentation voice.
6. Add comments wherever they improve comprehension of intent, boundaries, semantics, or sequencing.
7. Re-read the edited file and verify the comments still hold if small implementation details change.
8. Stop after finishing the requested comment edits and any explicitly requested verification. Do not stage, commit, amend, push, or otherwise advance Git state unless the user explicitly asked for that Git action in the current request.

## Priorities

### Top-level definitions first

Prioritize comments for top-level definitions before touching smaller internal details. This is an ordering rule, not a stopping rule. After the top-level pass, keep going into fields, options, and internal stages when the code contains semantics a maintainer cannot safely infer from names and types alone.

In most files, start with:

- exported functions
- public or shared classes
- interfaces and type aliases
- exported constants with business meaning
- configuration objects or maps whose keys are not self-evident

If the file is only partially documented and the user did not request a narrow slice, spend the budget on these definitions first, then add finer-grained comments for the highest-risk details.

### Preserve signal

Do not add comments just because a definition exists. Skip comments when the name, signature, and surrounding code already make the intent obvious and there are no hidden constraints.

### Calibrate granularity

Use the smallest comment that removes a real ambiguity. Do not stop at a file-level or function-level overview when the risk is inside a field, option, branch, state transition, or loop invariant.

Apply these levels deliberately:

- **Level 0: no comment** for obvious code with no hidden contract.
- **Level 1: definition comment** for the purpose, ownership boundary, side effects, preconditions, and return semantics of a function, class, type, or constant.
- **Level 2: member or field comment** for fields, options, enum values, map entries, reducer actions, and config properties whose domain meaning, units, default behavior, external coupling, or valid combinations matter.
- **Level 3: block guide comment** for phases inside complex logic, especially normalization, validation, branching policy, fallback, retries, ordering-sensitive transformations, and state transitions.
- **Level 4: local note** for a single surprising condition, invariant, regular expression, workaround, concurrency constraint, or integration quirk. Use this sparingly, but use it when the local detail is the actual source of likely mistakes.

When a user asks to "comment this file", "document this code", or similar without limiting scope, aim for complete semantic coverage of the requested artifact: each public contract, important data shape, and non-obvious internal phase should either be documented or be obviously self-explanatory.

### Expand beyond summaries

A high-level summary is insufficient when the code exposes a detailed contract. Add finer comments in these cases:

- an options object has booleans, callbacks, thresholds, feature flags, units, or ordering requirements
- a type/interface represents serialized data, API payloads, persisted state, generated output, or cross-module input
- a map or config object encodes policy, precedence, lookup fallback, labels, or business categories
- a function has multiple stages, nested branches, retries, fallbacks, cache behavior, mutation, or cleanup
- a reducer, parser, scheduler, workflow, or state machine has allowed transitions or impossible states
- a loop depends on an invariant, deduplication rule, short-circuit condition, or stable ordering
- a compact expression, regex, bitmask, date/time conversion, or numeric threshold would be easy to "simplify" incorrectly

## Comment Standards

### Explain semantics, not syntax

Write comments that explain one or more of the following:

- the responsibility of a definition
- the business or domain meaning of a value
- required preconditions or assumptions
- important side effects
- failure behavior or edge-case handling
- why a branch, transformation, or ordering requirement exists

Do not restate the code in prose. Avoid comments such as "Increment count" or "Check whether user exists" unless there is a deeper semantic reason worth explaining.

### Follow project language and style

Follow the repository's existing comment language. Infer it from the current file first, then nearby files of the same area. If the project mixes languages, follow the dominant style of the current file.

Preserve the local comment format when one already exists:

- JSDoc or TSDoc blocks for documented definitions
- line comments for short contextual notes
- block comments only when the surrounding codebase already uses them for that purpose

Default to JSDoc-compatible block comments for documented TS/JS top-level definitions when no stronger local pattern exists.

### Prefer durable wording

Write comments that survive small refactors. Prefer explaining intent and contract over implementation detail. Avoid documenting temporary mechanics unless that mechanic is the whole reason the code is hard to understand.

## Top-level Rules by Definition

### Functions

Document top-level functions and any non-trivial reusable helper whose misuse would be costly.

For documented functions, include:

- a one- or two-sentence summary of the function's responsibility
- `@param` entries for each meaningful parameter
- `@returns` only when the function has a meaningful return value

Use `@returns` to explain the meaning of the returned value, not just its type. Omit `@returns` for procedures that only produce side effects.

Capture important contracts when relevant:

- required parameter relationships
- mutation or side effects
- ordering guarantees
- fallback behavior
- failure or nullability semantics

For long or multi-stage functions, do not rely on the function summary alone. Add internal guide comments at the boundaries between phases when a reader must understand sequencing to make safe edits. A practical trigger is any function with several branches, loops, early returns, cleanup paths, or external calls whose order matters.

### Interfaces and types

Add an interface-level summary for every documented interface. Then document each top-level field unless the name, type, and nearby usage make the semantics completely obvious.

Field comments should explain:

- what the field represents
- whether it is required for a specific behavior
- special units, formats, or constraints
- coupling to external systems or business rules
- default behavior when omitted or empty
- valid combinations with sibling fields

For nested object types owned by the same file, document nested fields too when they form part of the public API, persisted shape, config surface, or cross-module contract. Do not hide meaningful field-level contracts inside a broad parent summary.

For simple aliases or literal unions, add a top-level comment only when the type has domain meaning that is not evident from its shape. For literal unions with non-obvious values, document each value or use nearby comments to explain the categories.

### Classes

Document the role of the class, especially its lifecycle, ownership boundary, and collaboration with other components. Document methods when their behavior is non-obvious or part of the external contract.

### Exported constants and config objects

Comment constants and object properties when they encode policy, thresholds, feature gates, lookup semantics, or business categories that a reader would not safely infer from names alone.

For lookup tables, route maps, registry objects, and config arrays, comment the object-level responsibility and then add property or entry comments for values whose meaning, precedence, fallback behavior, or downstream effect is not self-evident.

## Internal Guide Comments

Add internal guide comments only when they materially help a reader navigate complex logic. Good candidates include:

- multi-stage normalization or validation flows
- branching with business-specific rules
- state transitions
- retry, fallback, or recovery logic
- ordering-sensitive transformations
- loops with invariants, deduplication, batching, or early termination
- parser, scheduler, reducer, or workflow phases

When internal guide comments are needed, use numbered headings in ascending order:

- `1.`
- `1.1`
- `2.`
- `2.1`
- `2.2`

Use these comments to describe the intent of each stage, not every statement inside the stage.

Example pattern:

```ts
// 1. Normalize external input into a shape that downstream validation can reason about.
// 1.1 Preserve the caller's explicit overrides before applying defaults.
// 2. Reject combinations that would produce conflicting scheduling behavior.
```

Do not use numbered comments in simple functions, single-branch helpers, or straightforward CRUD wrappers.

Inside complex functions, place guide comments immediately before the block they explain. Keep each one narrow enough that moving or deleting the associated block would make it clearly stale.

## Rewrite and Removal Rules

Replace existing comments when they are:

- literal translations of syntax
- outdated after refactors
- redundant with strong naming
- inconsistent with the current file's terminology

Remove comments instead of rewriting them when the code is already fully clear and the comment adds no durable meaning.

Never stack a better comment under a bad one. Clean the old one first.

## TS and JS Defaults

For TypeScript and JavaScript, prefer:

- JSDoc-style comments for top-level functions, classes, interfaces, and exported constants
- property comments for interface fields
- short line comments for internal numbered guide steps

When documenting params and returns, keep type information in the type system and use the comment to explain semantic meaning, constraints, or caller expectations.

## Guardrails

- Do not comment every line.
- Do not invent business meaning that the code and nearby context do not support.
- Do not add `@returns` to void procedures.
- Do not document internal implementation trivia unless it prevents likely misunderstanding.
- Do not add field comments to nested inline object literals unless they are part of a meaningful API, config, serialized shape, or the request explicitly calls for that depth.
- Do not let comments drift into a second source of truth for obvious type information.
- Do not use one broad comment to cover several details that have different constraints, defaults, or failure modes.
- Do not run `git add`, `git commit`, `git commit --amend`, `git push`, create tags, or open PRs unless the user explicitly requested that Git action in the current request.
- Do not treat "comment the code", "document this file", or similar requests as permission to prepare a commit.
- If the user only asked for comments, leave version-control state untouched apart from the edited working-tree files themselves.

## Completion Check

Before finishing, verify all of the following:

- Top-level definitions were considered first.
- The top-level pass did not prematurely stop finer-grained comments where fields, options, transitions, or internal phases carry semantics.
- Function comments include `@param` and only include `@returns` when warranted.
- Interfaces have an overview and comments for each top-level field that needs semantic clarification.
- Meaningful nested API/config/serialized fields are documented when they are not self-explanatory.
- Config maps, registries, and lookup tables have entry-level comments when individual entries encode policy or precedence.
- Internal numbered comments appear only where staged guidance materially helps.
- Complex functions have comments at phase boundaries when sequencing or branching is part of the maintenance risk.
- New comments explain intent, constraints, and meaning rather than rephrasing code.
- Comment language and style match the surrounding project.
- No Git state-changing command was run unless the user explicitly requested it.
