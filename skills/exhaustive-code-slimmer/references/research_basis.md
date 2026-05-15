# Research and community basis

Use this file only when the task calls for justification, prioritization, or explaining why the workflow is strict.

## Distilled principles

1. **Behavior preservation is the boundary.** Refactoring is useful only when it changes internal structure without changing external behavior. Therefore the shrink workflow must start with an oracle and must run it after every accepted change.

2. **Code health is cumulative.** Review standards from large engineering organizations emphasize improving overall code health over time, not chasing personal taste. Deletion is justified by maintainability, readability, understandability, and measurable simplification.

3. **Exact search needs a predicate.** Delta-debugging-style reducers work because they repeatedly test whether a candidate still preserves the chosen property. For code slimming, the property is “the repository still satisfies the behavior oracle.”

4. **Structured reductions beat raw text reductions.** Program code is structured input. Prefer AST-, module-, dependency-, and symbol-boundary candidates over arbitrary character or line deletion. This reduces invalid candidates and improves shrink quality.

5. **Use both static and dynamic evidence.** Static analysis finds unreachable and unreferenced code; dynamic analysis/coverage catches runtime-flow-specific dead paths. Neither alone is enough for public APIs, reflection, generated code, feature flags, or dependency injection.

6. **Maximal is frontier-relative unless the full powerset was tested.** A globally maximal deletion set requires testing all combinations of all candidates against a complete oracle. In real repositories, be precise: exact within a candidate set or partition, fixed-point across regenerated frontiers, not mathematically global unless proven.

## Source notes for the skill author

- OpenAI skill-creator guidance: skills require `SKILL.md` with `name` and `description`; scripts are appropriate for deterministic repeated operations; references keep the main skill lean; avoid clutter files.
- Martin Fowler’s refactoring definition: behavior-preserving restructuring, done as small transformations while keeping the system working.
- Google engineering practices: code review optimizes for improving overall code health, consistency, maintainability, readability, and understandability; facts and data outrank preference.
- Delta Debugging / Fuzzing Book: reduction depends on a deterministic test predicate; it is robust and easy to deploy when tests are deterministic and fast.
- Hierarchical Delta Debugging: structured/tree-aware reduction produces syntactically valid configurations, fewer inconclusive cases, and often simpler outputs than flat reduction.
- C-Reduce lineage: source-to-source transformation portfolios can dramatically reduce code while preserving the interesting property; validity checks matter to avoid invalid or undefined reduced programs.

## Practical consequence

When using this skill, never stop at “I removed obvious dead code.” The intended loop is:

1. Define oracle.
2. Enumerate every plausible candidate in the current frontier.
3. Test combinations exhaustively where feasible.
4. Accept only oracle-preserving candidates.
5. Re-enumerate because new deletions expose new dead code.
6. Stop only at fixed point or an explicit, reported resource boundary.

## Architecture and DX extension

The skill treats architecture changes as a separate gate because structural refactors carry more risk than local deletions. A repository can be locally slimmed without reshaping architecture, but when architecture itself creates code bloat, the correct sequence is diagnosis → options → user approval → small verified refactors → renewed deletion search.

Practical consequences:

- Architecture ideas are allowed only when they improve developer experience and create a credible path to less maintained code.
- The assistant must present alternatives rather than silently imposing a preferred architecture.
- User approval is required before moving boundaries, changing dependency direction, replacing infrastructure patterns, or collapsing large abstraction layers.
- Code cleanliness is a constraint on every slimming step: brevity is not enough; the resulting code must be easier to understand, test, and change.
