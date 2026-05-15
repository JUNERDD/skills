# DX architecture gate

Use this reference when slimming is blocked by architecture rather than by isolated dead code. The purpose is to improve developer experience while still honoring the primary goal: less maintained code, behavior preserved.

## What counts as unreasonable architecture

Treat these as signals, not automatic conclusions:

- **Circular dependencies:** modules require each other directly or through short cycles, making deletion and testing hard.
- **God modules:** one file or package owns unrelated responsibilities and absorbs every change.
- **Pass-through layering:** controllers call services call managers call adapters with little or no branching, validation, IO, transaction control, or policy.
- **Ambiguous boundaries:** domain logic is mixed with UI, persistence, transport, auth, validation, and framework glue.
- **Scattered configuration:** one behavior is controlled by multiple config files, env names, feature flags, and default layers.
- **Duplicate abstractions:** multiple helpers, clients, mappers, DTOs, or repositories model the same concept differently.
- **Framework-fighting code:** custom routing, loading, validation, dependency injection, or build glue duplicates what the framework already provides.
- **Poor test ergonomics:** small behavior changes require integration-heavy setup because units cannot be constructed or observed directly.
- **Unclear ownership:** files are grouped by vague technical labels (`utils`, `common`, `services`, `managers`) rather than domain or feature responsibility.

## Approval requirement

If a candidate touches architecture-level boundaries, it is approval-gated. Examples:

- Moving modules across directories or packages.
- Changing dependency direction.
- Collapsing service/adapter/repository layers.
- Replacing a custom architecture pattern with a framework-native one.
- Splitting a god module into feature/domain modules.
- Introducing, removing, or replacing a public boundary, package, route group, or module contract.
- Changing project layout, build graph, workspace structure, or test architecture.

Before implementation, present 2-4 options and wait for explicit user selection or scope approval.

## Option patterns

### Option A: Prune in place

- **DX improvement:** minimal disruption; faster path to remove dead code.
- **Code-slimming payoff:** low to medium; best for repositories with reasonable boundaries.
- **What changes:** unused files, imports, dependencies, branches, wrappers, and duplicate local helpers are deleted in current layout.
- **Risk:** lowest; does not solve structural coupling.
- **Recommended when:** architecture issues are mild or the user wants a conservative first pass.

### Option B: Flatten pass-through layers

- **DX improvement:** fewer files to inspect per behavior; simpler call chains.
- **Code-slimming payoff:** medium to high when services/managers/adapters are pure forwarding layers.
- **What changes:** inline or delete wrappers, point call sites to the real domain operation, remove obsolete interfaces.
- **Risk:** medium; public API and test mocks may depend on the old layers.
- **Recommended when:** trace shows repeated one-line wrappers or mechanical delegation.

### Option C: Feature/domain slice

- **DX improvement:** developers can change a feature in one local area; fewer cross-directory edits.
- **Code-slimming payoff:** medium; reveals duplicate mappers, config, validators, and test fixtures.
- **What changes:** move related UI/API/domain/data/test code into feature or domain modules with explicit boundaries.
- **Risk:** medium to high; import paths and build/test wiring change.
- **Recommended when:** logic for one behavior is scattered across many technical folders.

### Option D: Dependency-direction cleanup

- **DX improvement:** lower coupling, easier unit tests, easier deletion of adapters and optional features.
- **Code-slimming payoff:** medium; cycles often hide dead adapters and duplicated DTO conversion.
- **What changes:** introduce or restore one-way dependency rules; isolate framework/persistence/transport adapters from domain code.
- **Risk:** medium; requires careful migration and contract tests.
- **Recommended when:** circular dependencies, side-effect imports, or framework glue block safe deletion.

### Option E: Framework-native simplification

- **DX improvement:** less custom glue; easier onboarding for developers who know the framework.
- **Code-slimming payoff:** high when custom routing, validation, DI, state, or build machinery duplicates framework features.
- **What changes:** replace bespoke infrastructure with standard framework primitives already present in the project.
- **Risk:** medium to high; framework contracts must be covered by smoke tests.
- **Recommended when:** custom infrastructure exists mainly from historical drift, not product requirements.

## Required option format

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

## Execution after approval

Once the user approves an option:

1. Create a branch/checkpoint.
2. Strengthen the oracle around affected public behavior.
3. Convert the chosen architecture option into small candidates.
4. Mark candidates as approved in the plan; only then run them with `--allow-approval-gated` when using `scripts/exhaustive_shrink.py`.
5. Apply changes in the smallest behavior-preserving steps.
6. Re-run audit after each accepted group because architecture cleanup often exposes new dead code.
7. Report net code reduction and DX effects separately.

## How to keep architecture slimming honest

- Do not introduce a new architecture pattern unless it deletes code or unlocks a bounded deletion sequence.
- Do not replace one abstraction stack with another abstraction stack.
- Do not move files just to make the tree look tidy; moves must improve locality, dependency direction, or deletion potential.
- Do not claim DX improvement without concrete evidence: fewer touch points, fewer imports, fewer layers, faster tests, clearer ownership, less config, or fewer dependencies.
