---
name: composable-components
description: >-
  Authors or refactors accessible primitive and product compound React
  components with genuinely configurable subparts, transparent host props and
  refs, data-rendering boundaries, state ownership, asChild/Slot behavior, and
  private underscore file-type folders. Use for compound component APIs,
  composable UI primitives, product composers, polymorphic parts, or their
  component-local _components/_types/_helpers/_utils layout.
---

# Composable Components

Design the public composition contract before arranging files. A namespace and
`Root` / `Trigger` / `Content` names do not make an API composable: consumers
must be able to use the advertised parts without the implementation silently
replacing, ignoring, or trapping them behind fixed defaults.

This skill is self-contained. Do not require another skill to make the API,
state, rendering, accessibility, or layout decisions described here.

## 1. Classify behavior and rendering ownership

| Kind | Signals | Public shape | Contract |
| --- | --- | --- | --- |
| **Primitive** | reusable behavior, `asChild`, dialog/select/accordion anatomy | `Root` plus semantic parts such as `Trigger`, `Content`, `Portal`, `Overlay`, `Title`, `Description`, `Close` | [Primitive contract](house-rules.md#primitive-contract) |
| **Product** | domain data, feature variants, mode-prop growth, local or synced state | `Provider` + `Frame` when the state scope differs from the visual frame; otherwise `Root` plus domain parts | [Product contract](house-rules.md#product-contract) |

Installing or merely assembling already-authored component packages is outside
scope. This skill is for **authoring or refactoring** component APIs.

A feature may contain **both**: a primitive in `components/ui/dialog/` and a
product composer in `features/composer/` that consumes it. Keep their ownership
boundaries distinct even when they live near each other.

Separately decide who owns repeated data:

- If the consumer owns iteration, it maps explicit `Item` parts.
- If the component must filter, group, virtualize, or otherwise supply each
  item, expose one render-function or function-children boundary with the item
  and stable public state. Do not hardcode a private `Item` beneath a public
  `Results` or `List` and then claim that exporting `Item` makes it replaceable.

## 2. House decisions (do not mix)

Read [house-rules.md](house-rules.md) before writing code. It contains the full
composition guidance needed by this skill. Defaults:

- Detect React from the project. 19+: `ref` is a prop, `use()`, no `forwardRef`. 18: `forwardRef` + `useContext`.
- One production caller is neither evidence for nor against a good abstraction.
  Derive seams from real responsibilities and known variation axes, and do not
  wait for a second caller before honoring a public component contract.
- Every public host-rendering part accepts its host's props, forwards its ref,
  and deliberately composes internal and consumer events, classes, and styles.
- Every exported part is reachable in normal composition or replaceable through
  an explicit render boundary. Do not export decorative customization points.
- Coordinate parts through context and explicit slots, not `child.type`
  inspection, first-match selection, or silent child dropping.
- When the API chooses `asChild`, use `@radix-ui/react-slot`, never an ad hoc
  `cloneElement` merger.
- Context has **no silent default**. Hooks throw outside the owner.
- No boolean props for layout or product mode. Compose explicit variants
  instead; intrinsic binary state such as `disabled`, `open`, and `asChild` is
  still valid.
- Prefer `children` over `renderX`. Render props only when the parent must pass item data back.
- Primitive state: `value` / `defaultValue` / `onValueChange` (or `open` / `onOpenChange`) via controllable state.
- Product state: only providers know the store implementation. Parts depend on
  a typed `state` / `actions` / `meta` context contract.
- Primitive behavior includes semantics, keyboard interaction, focus, and ARIA;
  `data-*` attributes expose styling hooks but never replace accessibility.

## 3. File-type folders

One kebab-case folder per component. Underscore directories are **private
implementation** (not a public import path; not an App Router route).

Create a `_` folder only when it has files. Never leave empties. Never invent
typos (`_ultils`). `index.ts` at the component root is the **only** public
barrel.

| Folder | Put here |
| --- | --- |
| `_components/` | React parts, one file per part |
| `_types/` | shared types and public prop types |
| `_constants/` | literals, keys, `data-state` unions, selectors |
| `_hooks/` | context hook and local behavior hooks |
| `_utils/` | pure generic helpers (no feature types) |
| `_helpers/` | feature-specific non-hook functions |
| `_lib/` | third-party / browser adapters only |
| `_styles/` | cva, recipes, CSS modules |
| `_providers/` | product state providers that implement the context contract |
| `_icons/` `_assets/` `_mocks/` `_tests/` `_stories/` | only when that artifact exists |

Full taxonomy, naming, and trees: [folder-layout.md](folder-layout.md).

## 4. Authoring workflow

```
Task progress:
- [ ] Kind is primitive or product (or split into two folders)
- [ ] Data iteration is consumer-owned or has an explicit render boundary
- [ ] Public seams follow responsibilities, not the number of current callers
- [ ] React baseline detected from package.json
- [ ] Folder exists; only needed _* directories created
- [ ] Types and constants extracted before parts grow
- [ ] Context hook throws outside owner
- [ ] Parts live in _components; barrel re-exports a namespace
- [ ] Every host part forwards native props/ref and composes events/class/style
- [ ] Every exported part is actually reachable, replaceable, or intentionally a default facade
- [ ] No child.type scanning, first-child-only selection, or silent child dropping
- [ ] Primitive semantics, asChild, data-state, focus, and keyboard behavior are covered
- [ ] Product parts know the context contract, not the store implementation
- [ ] No boolean mode props; explicit variants compose parts
- [ ] External imports go through index.ts only
```

**Done when:** the advertised composition works with at least one meaningful
alternative arrangement or renderer, public parts preserve their host contract,
internals are in the needed `_` folders, house rules hold, and unused `_`
folders do not exist. A namespace object by itself is not completion.

## 5. Scope boundaries

- Do not expand this into design tokens, npm publishing, registries,
  marketplaces, or component documentation workflows.
- Do not add generic React-version guidance beyond the local baseline rule.
- Do not recreate full Radix internals such as `DismissableLayer`, `Presence`,
  or `createContextScope`. If same-primitive nesting requires extra isolation,
  use an existing project primitive or a narrowly owned local scope instead of
  inventing another primitive library.
