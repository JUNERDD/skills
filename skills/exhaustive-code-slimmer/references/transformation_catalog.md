# Transformation catalog

Generate candidates broadly, but accept only candidates that pass the oracle.

## Deletion candidates

- Empty files and placeholder files that are not package markers.
- Duplicate files with byte-identical content.
- Generated artifacts committed alongside source when the build regenerates them.
- Vendor/build/cache outputs mistakenly committed to source.
- Unused dependencies, devDependencies, lockfile-only packages, unused plugins.
- Unused imports, exports, constants, variables, type aliases, functions, classes, methods.
- Unreachable branches after `return`, `throw`, `continue`, impossible conditions, or constant feature flags.
- Deprecated feature-flag branches that the user confirms are permanently off/on.
- Dead routes, handlers, commands, migrations, jobs, scripts, and test fixtures.
- Duplicate test helpers, stale mocks, snapshots for deleted behavior.

## Simplification candidates

- Inline single-use wrappers, pass-through functions, pass-through classes, and needless adapters.
- Collapse abstraction layers that add no branching, validation, caching, IO, or polymorphism.
- Replace custom helper code with already-used standard-library or framework features.
- Combine duplicate branches with identical bodies.
- Fold constant conditions and remove impossible else branches.
- Remove unused parameters together with call-site updates.
- Reduce config indirection: one value, one source of truth.
- Merge near-duplicate functions only when the merged version is shorter and clearer.
- Remove defensive code only when the oracle or contracts prove the state cannot occur.

## Candidate ordering

1. Whole repository hygiene: committed artifacts, caches, duplicate files.
2. Dependency pruning: packages, plugins, build tools.
3. Module-level deletion: unreachable files, unused exports, dead routes.
4. Symbol-level deletion: functions/classes/methods/types/constants.
5. Statement-level deletion: branches, parameters, temporary variables.
6. Refactor-for-deletion: consolidate duplicates, inline wrappers, collapse layers.
7. Re-audit: accepted changes may expose new dead imports, new unused symbols, and new dependency cuts.

## Rejection rules

Reject or defer a candidate if it relies on any of these without evidence:

- “Looks unused” but could be public API.
- Covered only by naming convention, not tests or references.
- Breaks readability by creating dense, clever, or minified code.
- Removes logging/metrics/audit logic that is operationally required.
- Deletes migration, compatibility, fallback, or security code without user confirmation.

## Approval-gated architecture candidates

Generate these only as proposals until the user approves an architecture scope. Mark them with `requires_user_approval: true` in candidate JSONL.

- Collapse pass-through service/manager/adapter layers.
- Move code from technical folders into feature/domain slices.
- Break circular dependencies by moving contracts or reversing dependency direction.
- Replace custom framework glue with framework-native routes, validation, loading, or dependency wiring.
- Split god modules into cohesive modules when the split enables deletion of duplicate helpers, config, tests, or adapters.
- Consolidate duplicated clients, repositories, DTO mappers, feature-flag plumbing, or config loaders across modules.
- Remove or reshape package/workspace boundaries.

## Architecture candidate acceptance rules

Accept an approved architecture candidate only if:

- The user approved the exact option or scope.
- The oracle covers the affected public behavior and boundary contracts.
- The resulting structure improves at least one DX metric: fewer layers per change, fewer import cycles, clearer ownership, faster tests, less config, fewer dependencies, or fewer files touched for common changes.
- Net maintained code decreases immediately or the step is part of an approved bounded sequence that will decrease maintained code.
- The result satisfies `references/code_cleanliness_guide.md`.

Reject or defer it if:

- It is merely aesthetic file movement.
- It introduces a new abstraction before deleting an old one.
- It improves theoretical architecture while increasing maintained code and cognitive load.
- It breaks searchability, typeability, test isolation, or framework conventions.
