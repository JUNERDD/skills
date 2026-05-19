---
name: exhaustive-code-slimmer
description: Exhaustive code slimming, AST-first code-pruning, and approval-gated architecture cleanup workflow for maximizing removable code while preserving behavior and improving developer experience. Use when the user asks for code cleanup, ruthless simplification, dead-code removal, dependency pruning, refactoring for less code, DX architecture review, exhaustive shrinking, maximal code reduction, redundancy removal, AST-informed unused-code discovery, or aggressive but behavior-preserving simplification.
---

# Exhaustive Code Slimmer

Goal: remove the maximum amount of maintained code that can be removed without changing externally observable behavior. Prefer deletion over abstraction, simple code over clever code, good DX over theoretical purity, and measured evidence over taste.

## Non-negotiables

- Establish a behavior-preservation oracle before changing code: build, typecheck, tests, lint if relevant, smoke commands, snapshots, API contracts, and migration checks.
- For structural claims, use AST, language-server, parser, or repository-native static-analysis evidence before regex or text-search evidence when available. Use text search and bundled scripts as candidate generators, cross-checks, or fallback only; the oracle remains the final acceptance authority.
- Apply the code-cleanliness guide in `references/code_cleanliness_guide.md`. Slim code must remain readable, explicit, locally understandable, and easy to change; do not create dense, clever, minified, or “golfed” code.
- Never count minification, obfuscation, whitespace-only deletion, or comment deletion as code slimming unless the user explicitly asks for artifact-size minification.
- Do not delete public API, migrations, generated files, feature-flag branches, compatibility shims, security checks, operational logging, or configuration without evidence that the oracle covers them or the user has declared them removable.
- When architecture appears unreasonable, pause structural changes and propose 2-4 DX-improving architecture options. Do not perform architecture-level refactoring, boundary moves, framework migration, module reshaping, or abstraction collapse until the user explicitly approves one option or scope.
- Work from version control or a clean checkpoint. Keep every accepted deletion attributable to a candidate and oracle result.
- Continue until a fixed point: no untested candidate remains in the current search frontier and no accepted deletion enables new candidates.

## Workflow

1. **Baseline**
   - Record files, LOC, nonblank LOC, bytes, dependency count, top large files, duplicate blocks, and generated/vendor directories.
   - Run `scripts/code_slim_audit.py --repo . --json-output /tmp/slim-audit.json --markdown-output /tmp/slim-audit.md --candidates-output /tmp/slim-candidates.jsonl` when a repository is available.

2. **Architecture and DX gate**
   - Inspect whether the current architecture blocks effective slimming: circular dependencies, god modules, deep pass-through layers, scattered config, duplicated boundaries, framework-fighting patterns, unclear ownership, over-abstracted services/managers/adapters, or brittle build/test ergonomics.
   - Run `scripts/architecture_dx_scan.py --repo . --json-output /tmp/architecture-dx.json --markdown-output /tmp/architecture-dx.md` for heuristic signals when a repository is available.
   - If the architecture is reasonable, continue with deletion-first shrinking.
   - If the architecture is unreasonable, produce an approval-gated architecture note with 2-4 options. Each option must include DX benefit, expected code-slimming payoff, migration shape, risk, oracle requirements, and whether net maintained code should decrease.
   - Until the user approves an option, only perform reversible audit, candidate enumeration, and non-structural deletion planning. Do not execute structural refactor candidates.

3. **Oracle**
   - Build the strongest available oracle. If absent, create minimal smoke tests before deletion.
   - Read `references/oracle_design.md` for oracle composition and blind spots.

4. **Candidate enumeration**
   - Enumerate deletion and simplification candidates across every layer: files, directories, imports, exports, functions, classes, branches, duplicated blocks, dependencies, adapters, feature flags, config, tests, docs-only code paths.
   - For symbol, import/export, call-site, dependency-edge, branch-reachability, wrapper, or duplicate-structure claims, prefer type-aware AST, then syntax AST or language-server references, then repository-native static tools, then heuristic scripts and text search.
   - Label candidate evidence as `AST-verified`, `AST-inferred`, `Static-tool-verified`, `Inventory-verified`, `Text-fallback`, `Runtime/coverage-observed`, or `Unknown / not covered`. Record parser or language-server blind spots in candidate JSONL when they affect confidence.
   - Mark architecture-level transformations with `requires_user_approval: true` in candidate JSONL unless the user has already approved the scope.
   - Read `references/ast_first_candidate_generation.md` when the task depends on unused symbols, call graph reachability, import/export pruning, branch folding, duplicate function bodies, or other structural code claims.
   - Read `references/transformation_catalog.md` before proposing transformations.

5. **Exhaustive shrinking**
   - For small independent sets, perform exact subset search: test every subset and keep the highest deletion score that passes the oracle.
   - For large sets, partition by module/file/dependency class, run exact search inside each partition, then run global greedy/ddmin-style passes over survivors. Repeat inventory → exact/partitioned search → oracle until fixed point.
   - Use `scripts/exhaustive_shrink.py --repo . --candidates candidates.jsonl --oracle "<command>" --mode exact` for exact search, or `--mode partition-exact` when full powerset search is too large.
   - Approval-gated candidates are skipped by default. Include them only after explicit user approval with `--allow-approval-gated`.

6. **Refactor only when it deletes net code**
   - Consolidate duplicate logic, inline unnecessary wrappers, collapse indirection, simplify control flow, and remove abstractions only when the diff reduces maintained code and improves clarity.
   - Treat behavior-preserving refactoring as small, verified steps.
   - For architecture refactors, first show the chosen design, affected boundaries, migration sequence, and rollback plan; then proceed only within the approved scope.

7. **Report**
   - Summarize before/after metrics, accepted candidates, rejected high-risk candidates, approval-gated candidates, oracle commands, evidence modes used, residual blind spots, and next search frontier.
   - Include the shrink ratio: `(baseline nonblank LOC - final nonblank LOC) / baseline nonblank LOC`.
   - If an architecture option was proposed but not approved, report it as pending and keep the actual change set deletion-only or local-refactor-only.

## Search discipline

- Prefer structured candidates over raw text edits: AST nodes, symbols, import/export edges, dependency graph edges, module boundaries, branch bodies, and function/class spans.
- First test high-yield removals: whole files, unused dependencies, obsolete feature flags, unreachable branches, unused exports, duplicate modules.
- Then test local reductions: function/class deletion, parameter deletion, branch folding, wrapper inlining, loop/control-flow simplification, duplicate-block consolidation.
- Finally test cross-cutting reductions: dependency graph cuts, package splits, schema/config pruning, and generated-artifact removal.
- Architecture-level moves are not “free cleanup.” They require a DX rationale, a net-code-reduction rationale, and explicit user approval before execution.
- After every accepted candidate, regenerate candidates because new dead code can appear.
- If exact search is infeasible, state the candidate count, partitioning strategy, budget, and why the result is maximal within that frontier rather than globally proven minimal.

## Architecture option format

When architecture is the blocker, present options in this shape:

```text
Option <N>: <architecture idea>
- DX improvement:
- Code-slimming payoff:
- What changes:
- What does not change:
- Oracle needed:
- Risk / rollback:
- Recommended when:
```

Do not start implementation until the user chooses an option or narrows the scope.

## References

- `references/research_basis.md`: distilled community/research basis.
- `references/oracle_design.md`: behavior-preservation oracle checklist.
- `references/ast_first_candidate_generation.md`: AST-first candidate generation, evidence labels, and fallback rules.
- `references/transformation_catalog.md`: deletion/simplification candidate catalog.
- `references/language_tactics.md`: language-specific tools and tactics.
- `references/code_cleanliness_guide.md`: mandatory code-cleanliness rules for slimming.
- `references/dx_architecture_gate.md`: approval-gated architecture diagnosis and option design.
