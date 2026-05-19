# AST-first analysis protocol

Use this reference whenever an agent, editor integration, code intelligence tool, parser, language server, or repository utility can inspect TypeScript/JavaScript ASTs.

## Contents

- [Core rule](#core-rule)
- [Acceptable AST sources](#acceptable-ast-sources)
- [What AST evidence should answer](#what-ast-evidence-should-answer)
- [Recursive AST trace algorithm](#recursive-ast-trace-algorithm)
- [Evidence labels](#evidence-labels)
- [Fallback rules](#fallback-rules)
- [Common AST pitfalls](#common-ast-pitfalls)

## Core rule

Prefer AST or language-server evidence over regular-expression evidence for structural claims.

Use text search and the bundled Python scripts as candidate generators, fallback tools, and sanity checks. Do not use them as final authority when AST evidence is available for the same question.

## Acceptable AST sources

Use any available non-mutating source of syntax or semantic structure:

- TypeScript Compiler API
- `ts-morph`
- Babel parser
- SWC parser
- tree-sitter
- ESLint parser services
- IDE or language-server references
- repository-owned AST/codegen utilities
- existing static-analysis tooling in the project

Do not install new dependencies, rewrite project configuration, or mutate generated files just to obtain AST access unless the user explicitly asked for that setup work.

## What AST evidence should answer

For React wide-API review, AST is most valuable for:

- resolving a component, hook, context, or type symbol to its definition
- following imports, exports, aliases, re-exports, `memo`, `forwardRef`, and simple HOCs
- counting top-level fields of `interface` and `type` literals
- identifying JSX attributes, JSX spreads, and the expression being spread
- finding prop destructuring in function parameters and local bindings
- finding property reads such as `props.user.name`, `user.name`, `editor.actions.save`, and `form.values.email`
- distinguishing object rest/spread from named field consumption
- identifying hook calls and arguments
- identifying hook return object literals and tuple returns
- identifying `createContext`, provider `value`, `useContext`, and context consumer flows
- identifying `useEffect`, `useMemo`, `useCallback`, `memo`, and dependency arrays
- identifying reducer action shapes and dispatch boundaries
- identifying dynamic access that cannot be fully proven statically, such as `obj[key]`, computed spreads, and schema-driven renderers

## Recursive AST trace algorithm

1. Resolve the entry symbol.
   - Find its definition file, export name, local aliases, and wrappers such as `memo(Component)` or `forwardRef(Component)`.
   - Record whether resolution is AST-verified, language-server verified, text-fallback, or unknown.

2. Extract the boundary shape.
   - For components, find props type, parameter destructuring, `PropsWithChildren`, `Pick`, `Omit`, intersections, and generics where practical.
   - For hooks, find positional parameters, object options, and return shape.
   - For contexts, find `createContext` type/value and provider `value` shape.
   - For forms/tables/view models, identify the top-level public surface and grouped fields.

3. Find call sites and consumers.
   - Use symbol references or import-aware lookup when available.
   - Record JSX attributes, spreads, hook calls, provider values, context consumers, and downstream object propagation.
   - Treat unresolved references as coverage gaps, not proof of safety.

4. Classify local field use.
   - `Directly consumed`: property access or destructured field read used locally.
   - `Passed through`: field/group passed as a named prop or hook argument.
   - `Spread propagated`: object spread into JSX/object literal where target fields are hidden.
   - `Effect-bound` / `Memo-bound`: object or field appears in a dependency array or callback closure.
   - `Context-propagated`: object or field enters a provider value or is read from context.
   - `Hook-return propagated`: hook return object is passed onward or used as one dependency.
   - `Dynamic/unknown`: computed access, rest binding, schema renderer, or alias prevents proof.

5. Descend recursively.
   - Follow project-local components, hooks, context consumers, field components, table row/cell renderers, and adapters that receive a wide field group.
   - Stop at documented stop conditions only.
   - Write every stop into the Recursive Coverage Ledger.

6. Compare AST evidence with text evidence.
   - Use `rg` or bundled scripts to catch files the AST source missed, generated code, dynamic references, or import aliases.
   - If AST and text evidence disagree, prefer AST for syntax-level facts and record the disagreement as a blind spot or verification command.

## Evidence labels

Use explicit evidence labels in reports:

- `AST-verified`: parsed or language-server evidence directly proves the relationship.
- `AST-inferred`: AST proves nearby facts, but type expansion, alias resolution, or dynamic access requires inference.
- `Text-fallback`: based on search or heuristic scripts because AST access was unavailable or insufficient.
- `Runtime-observed`: based on profiler, interaction trace, render counter, or targeted instrumentation.
- `Unknown / not covered`: no reliable evidence available within scope or budget.

## Fallback rules

When AST access is unavailable:

- use `react_wide_api_inventory.py`, `react_wide_api_trace.py`, and targeted text search as candidate generators
- lower confidence where aliasing, spreads, re-exports, HOCs, computed keys, or generated schemas affect the result
- mark parser limitations in `Gate Snapshot`, `Evidence Appendix`, and `Recursive Coverage Ledger`
- do not claim complete field-flow proof for paths that require AST resolution but were only text-searched

## Common AST pitfalls

- A field declared in a type is not necessarily consumed.
- A destructured rest binding, such as `const { id, ...rest } = props`, may hide wide propagation.
- `Pick`, `Omit`, intersections, generics, and imported aliases can hide field count unless semantic type expansion is available.
- `React.memo` does not remove context fan-out or wide prop ownership risk.
- Schema-driven renderers may intentionally use dynamic keys; classify them as intentional exceptions or coverage gaps only with evidence.
- Generated files may be wide by contract; record owner and exit condition before treating them as findings.
