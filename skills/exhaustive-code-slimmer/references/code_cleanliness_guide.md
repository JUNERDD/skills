# Code cleanliness guide for slimming

Use this guide as the mandatory quality bar for every deletion, simplification, and refactor. Code slimming is not code golf. The target is less maintained code with higher clarity and better change ergonomics.

## Core rules

1. **Behavior stays explicit.** A smaller diff is not acceptable if future readers must reverse-engineer hidden side effects, implicit contracts, or clever control flow.
2. **Delete before abstracting.** Prefer removing dead code, unused layers, duplicate paths, and speculative branches before introducing a new abstraction.
3. **Local understanding wins.** A reader should understand a function/module from nearby code and clear names, not from scattered conventions or hidden registries.
4. **One concept, one place.** Consolidate duplicate logic only when the new home is obvious and the resulting abstraction is shorter, clearer, and less coupled.
5. **No speculative generality.** Remove hooks, extension points, base classes, factories, adapters, and configuration knobs that serve no current behavior.
6. **Minimal public surface.** Keep public APIs, exports, commands, routes, and config keys as small as the product contract allows. Public surface is maintained code.
7. **Straight-line flow where possible.** Prefer guard clauses, direct returns, and simple branching over nested conditionals, flag plumbing, or callback mazes.
8. **Names carry domain meaning.** Do not shorten names merely to reduce characters. Rename only when it improves semantic precision.
9. **Dependencies must pay rent.** A dependency is justified only if it removes more code/risk than it adds and improves maintenance or correctness.
10. **Tests describe behavior.** Keep or add tests that protect public behavior. Delete tests only when the behavior itself is intentionally deleted or the test asserts obsolete implementation detail.

## Accept a slimming change only if all are true

- The oracle passes.
- Net maintained code decreases, or the change unlocks a clearly bounded deletion sequence that will decrease code.
- Readability is at least as good as before.
- The public contract is unchanged unless the user explicitly approves a contract reduction.
- The change reduces at least one real burden: duplicated logic, unused surface area, dependency weight, cognitive load, build/test friction, or change coupling.
- The diff can be explained with a concrete reason, not “cleaner” as an unsupported preference.

## Reject a slimming change if it does any of these

- Compresses code into denser expressions that are harder to inspect.
- Replaces clear duplication with a leaky abstraction or boolean-parameter multiplexer.
- Hides domain rules in framework magic, reflection, decorators, dynamic dispatch, or stringly typed registries without a strong reason.
- Deletes comments that document non-obvious contracts, historical constraints, security requirements, or operational behavior.
- Removes logging, metrics, audit trails, permissions, validation, migrations, backfills, compatibility paths, or fallbacks without explicit coverage and approval.
- Makes the code harder to test, harder to typecheck, harder to search, or harder to onboard into.

## Code-cleanliness checklist for reviews

Before accepting a candidate, answer:

- What exact behavior did the oracle protect?
- What exact code burden disappeared?
- Is the new code easier to read without extra context?
- Did public surface area shrink, stay stable, or expand?
- Did dependency count, import graph complexity, or configuration surface shrink?
- Did this create a new abstraction? If yes, what did it delete immediately?
- Is there a simpler deletion-only alternative?
- Are any risks outside the oracle listed in the report?

## Style guidance

- Prefer small cohesive modules over large god modules or deep pass-through layer stacks.
- Prefer domain-oriented names over generic names such as `Manager`, `Helper`, `Common`, `Util`, `Base`, or `Service` when they hide actual responsibility.
- Prefer explicit data flow over shared mutable state, global registries, monkey-patching, or ambient context.
- Prefer boring standard-library/framework idioms over custom utility code.
- Prefer a stable dependency direction: UI/entrypoints depend on domain/application code; domain code should not depend on adapters or presentation layers.
- Prefer type-level or schema-level guarantees over repeated runtime defensive branches, but only when the result is clearer and the oracle covers it.

## Reporting language

Use concrete claims:

- “Deleted 3 unused adapters after route map and tests showed no references.”
- “Collapsed two pass-through service layers; call sites now depend directly on the domain function.”
- “Rejected branch deletion because feature-flag state is not covered by the oracle.”

Avoid vague claims:

- “Looks cleaner.”
- “Probably unused.”
- “Architecture feels bad.”
- “This abstraction is nicer.”
