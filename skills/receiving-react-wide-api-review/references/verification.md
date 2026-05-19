# Verification guide

Use targeted verification that matches the item type. Prefer AST/language-server/parser evidence over regex/text evidence for structural claims when those capabilities are available. Do not rely only on lint or typecheck.

## AST-first verification

When AST tooling is available, use it before grep or regex. Prefer type-aware AST to resolve symbols, props types, hook return shapes, context value types, imports/re-exports, and utility types. Use syntax AST for destructuring, member expressions, JSX attributes/spreads, dependency arrays, provider values, and returned object literals.

Use grep and the bundled scripts to find candidates or sanity-check repeated strings, but do not use them as final counter-evidence when AST can resolve the field-flow path. Record AST mode and unresolved gaps in the disposition ledger.

## AST-first verification

When available, first resolve the relevant component, hook, context, provider, or type with AST or language-server tooling. Verify symbol definitions, imports/exports, JSX call sites, destructuring, property reads, object spreads, hook arguments, hook return consumption, provider values, context consumers, and dependency arrays. Then use text search as a cross-check.

## Field-flow verification

Search for remaining broad props or groups when AST evidence is unavailable, incomplete, or needs cross-checking:

```bash
rg "<EmailField|EmailField\(" src
rg "form=|editor=|table=|context=" src
rg "\.Provider" src
```

Trace whether the broad object still crosses the boundary:

```bash
python skills/react-wide-api-review/scripts/react_wide_api_trace.py ./src --symbol UserEditor --field form --field actions
```

## Context verification

- Search all provider values.
- Search all `useContext(SomeContext)` calls.
- For each consumer, list fields read.
- Verify state/actions/config are split only when consumers benefit.

## Hook verification

- Search all calls to the hook.
- Verify return destructuring or grouped usage.
- Verify hook internals do not depend on whole options objects for effects.
- Verify action identity only where it matters.

## Form/table/list verification

- Check leaf fields/cells receive local data, ids, selectors, or field hooks.
- Verify controller objects are not passed to every leaf unless they are stable adapters.
- Run interaction tests when field editing behavior is affected.

## User-visible UI regression verification

Treat UI behavior as externally observable behavior. For any fix that touches React rendering, state, routing, forms, permissions, accessibility, or persistence, verify the affected surface with the strongest available oracle:

- build, typecheck, and lint where available
- focused component, integration, or end-to-end tests around the touched flow
- interaction smoke tests for editing, selection, filtering, save/cancel, loading, empty, and error states
- visual or snapshot checks when layout, copy, ordering, or rendered data could change
- accessibility checks for labels, roles, focus order, keyboard navigation, and disabled states
- manual reproduction steps when automated coverage is unavailable

Do not treat a passing typecheck as proof that copy, visible data, focus behavior, validation, routing, or accessibility semantics are unchanged. Record the oracle used and any user-visible blind spots in the disposition ledger.

## TypeScript and tests

Run targeted checks when available:

```bash
npm run typecheck
npm test -- --runInBand path/to/test
pnpm test path/to/test
```

Record what each command proves and what it does not prove.

## Runtime/profiler evidence

Use when the report claimed performance risk:

- React Profiler commit counts
- interaction timing
- console instrumentation for renders
- targeted reproduction of effect reruns

If runtime evidence is unavailable, state that the conclusion is static or inferred from React data flow.

## Gate refresh

Rerun `react-wide-api-review` when:

- fixes materially changed the API shape
- pass-through graph changed
- context split changed consumers
- hook return/options changed
- multiple findings were fixed
- coverage gaps were closed

A small local fix with clear verification may only need a disposition update.
