# Recursive audit guide

## Contents

- [AST-first recursive tracing](#ast-first-recursive-tracing)
- [Recursive audit mechanics](#recursive-audit-mechanics)
- [1. Choose entry surfaces](#1-choose-entry-surfaces)
- [2. Build a boundary graph](#2-build-a-boundary-graph)
- [3. Trace field use at each node](#3-trace-field-use-at-each-node)
- [4. Detect pass-through depth](#4-detect-pass-through-depth)
- [5. Detect subscription width](#5-detect-subscription-width)
- [6. Detect ownership drift](#6-detect-ownership-drift)
- [7. Stop conditions](#7-stop-conditions)
- [8. Report the graph compactly](#8-report-the-graph-compactly)
- [9. Prefer minimal refactors](#9-prefer-minimal-refactors)

## AST-first recursive tracing

When AST capability is available, use it as the primary mechanism for recursion. Resolve declarations and symbols before following field-flow edges. Prefer a type-aware TypeScript program; use syntax-only AST when type information is unavailable. Use regex or the bundled Python scripts only to discover candidate entry points or to cover paths AST cannot parse.

An AST recursive pass should map:

```txt
entry declaration
→ prop/options/return/context shape
→ local bindings and aliases
→ direct field reads and destructures
→ outbound JSX props, spreads, hook calls, provider values, dependency arrays
→ downstream declaration
→ repeat until stop condition
```

Record parser mode, files parsed, unresolved symbols, computed properties, `any` boundaries, generated-code gaps, and fallback evidence in the report.

## Recursive audit mechanics

Use this reference when the user asks for a deep, recursive, repo-level, or dependency-chain review of wide React APIs. When AST, language-server, parser, or project code-intelligence capabilities are available, run this recursive method through AST-derived symbols and edges first; use text search only as fallback or cross-check.

## 1. Choose entry surfaces

Entry surfaces can be explicit or discovered.

Explicit entries:

- a component name
- a custom hook name
- a context name
- a props/options/return type
- a form controller
- a table/grid config
- a directory or feature module

Discovered entries:

- large `Props`, `Options`, `Config`, `Return`, `Context`, `ViewModel`, `Model`, `Value`, or `State` types
- JSX calls with many attributes or spreads
- custom hooks with many positional parameters
- custom hooks returning large flat objects
- provider values containing many top-level fields or domains
- form/table/list controllers passed into leaves

## 2. Build a boundary graph

Prefer AST-derived graph edges when possible. Resolve imports, exports, aliases, JSX attributes, spreads, destructuring, property reads, hook calls, provider values, dependency arrays, and memo/forwardRef wrappers using AST or language-server evidence before relying on string matches.

Represent the graph with nodes and edges.

Node kinds:

- `Container`
- `View`
- `Section`
- `Leaf`
- `Hook`
- `Hook Return Consumer`
- `Context Provider`
- `Context Consumer`
- `Form Controller`
- `Field Component`
- `Table/Grid Controller`
- `Row/Cell Component`
- `Store Selector`
- `Third-party Adapter`
- `Unknown`

Edge kinds:

- `prop`
- `spread`
- `hook-argument`
- `hook-return`
- `context-value`
- `context-read`
- `field-selector`
- `derived-value`
- `effect-dependency`
- `memo-dependency`
- `callback`
- `command/dispatch`

## 3. Trace field use at each node

For each node, classify each field or field group:

- directly rendered
- directly used in a conditional
- used to build a derived value
- used in an effect dependency
- passed to a child as a named prop
- passed to a child as a group prop
- spread into a child
- used to configure a hook
- returned by a hook
- placed into context
- read from context
- converted into an action/command
- unused within the inspected scope

When a field is passed to another component, hook, provider, or adapter, descend into that target unless a stop condition applies.

## 4. Detect pass-through depth

A pass-through path is a chain where a boundary receives a field or group and forwards it without materially owning it.

Examples:

```text
UserEditorContainer -> UserEditorView -> ContactSection -> EmailField
```

If `UserEditorView` and `ContactSection` do not read most of `form`, but pass it through, the field owner is probably too high or the leaf needs a field-level selector.

Record pass-through depth as:

- `0`: direct consumer
- `1`: one intermediary
- `2+`: multi-layer tunnel
- `unknown`: spread or dynamic path hides the target

## 5. Detect subscription width

A wide subscription exists when a consumer can re-render, recompute, or re-run an effect because a large object changes even though the consumer only needs a small slice.

Common cases:

- `useContext(AppContext)` then read one field
- `const editor = useEditor()` then pass `editor` to a leaf
- `useEffect(..., [options])` where `options` has many fields
- `React.memo(Component)` receiving a large unstable group
- form field receives whole `form` object
- table cell receives whole `table` instance

Record whether the risk is verified, inferred from React semantics, or unknown.

## 6. Detect ownership drift

Ownership drift exists when a field's creation, validation, update, and consumption are split across layers that no longer have a clear boundary.

Ask:

- Who creates the field?
- Who validates it?
- Who updates it?
- Who renders it?
- Who stores it?
- Who decides whether it is optional or derived?
- Is there another model or selector that already owns the same concern?

## 7. Stop conditions

Stop recursion when:

- the callee is a third-party library or generated API outside scope
- the child receives only narrow primitive or local group props
- the boundary uses a selector or field-level hook that narrows subscription
- the field is stable config that is not mutated or used as a volatile dependency
- the user scope explicitly excludes the subtree
- files are unavailable
- the budget is exhausted

Every stop must be reflected in the `Recursive Coverage Ledger`.

## 8. Report the graph compactly

Use a tree for the high-risk path and ledgers for exhaustive accounting.

Example:

```text
ProductPage
└─ ProductEditor(value, actions, permissions, status)
   ├─ PricingSection(value.pricing, actions.changeField) [Reviewed]
   ├─ InventorySection(productEditorVm) [F1 pass-through]
   │  └─ StockField(productEditorVm) [F1 leaf over-subscription]
   └─ Toolbar(status, permissions, actions) [Reviewed]
```

## 9. Prefer minimal refactors

A deep review should identify the smallest boundary change that reduces field awareness:

- pass `ProductPricingModel` instead of `ProductEditorViewModel`
- use `useField('email')` instead of passing `form`
- split `StateContext` and `ActionsContext`
- replace many `onXChange` props with typed `changeField`
- introduce a selector for `nodes[nodeId]`
- move object construction inside `useEffect`
- split stable config from volatile state

Do not propose whole-module rewrites unless the ledgers show that no narrower migration can close the high-risk findings.
