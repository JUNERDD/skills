# File-type folders

Underscore prefix means **private to this component folder**. Outside code
imports the public barrel only (`./index.ts`), never
`dialog/_hooks/use-dialog`.

In Next.js App Router, `_` folders are also non-routes. Use the same prefix
under `components/` and `features/` so “not public” is consistent.

## Root shape

```text
<component-name>/                 # kebab-case, one compound API
  index.ts                        # public barrel only
  _components/                    # React parts
  _types/                         # shared + public types
  _constants/                     # literals and keys
  _hooks/                         # hooks
  _helpers/                       # feature-specific functions
  _utils/                         # generic pure functions
  _lib/                           # adapters
  _styles/                        # visual recipes
  _providers/                     # product providers (product kind only)
  _icons/                         # local icons
  _assets/                        # local static files
  _mocks/                         # fixtures
  _tests/                         # tests if not colocated
  _stories/                       # storybook
  _server/                        # RSC-only modules
```

Create a directory **only when the first file needs it**. Delete it if the last
file leaves. Do not pre-scaffold the whole tree.

`index.ts` re-exports a namespace. It does not implement parts.

```ts
export { Root, Trigger, Content } from "./_components/root"
// or named files:
// export { Root } from "./_components/root"
// export { Trigger } from "./_components/trigger"
// export { Content } from "./_components/content"

export const Dialog = { Root, Trigger, Content }
export type { DialogRootProps, DialogTriggerProps, DialogContentProps }
```

Prefer one export line per part file. Re-export types from `_types`, not from
part files, when more than one part shares them.

## Folder contract

Use this table. Do not put the same file in two folders.

| Folder | Owns | Does not own |
| --- | --- | --- |
| `_components/` | One React part per file: `root.tsx`, `trigger.tsx`, `content.tsx`. Product: `frame.tsx`, `input.tsx`, `submit.tsx`. | hooks, types-only modules, providers that only inject state |
| `_types/` | Context value, public props, shared unions used by ≥2 files | runtime constants (those go in `_constants`) |
| `_constants/` | `DATA_STATE`, ids prefixes, query selectors, z-index, error strings | functions, React nodes |
| `_hooks/` | `use-<name>.ts` context hook; local `use-controllable-*` wrappers | generic `useDebounce` that belongs in a shared hooks package |
| `_utils/` | Pure, generic, no feature types: `compose-event.ts`, `compose-refs.ts`, `cx.ts` | functions that import `_types` or know accordion/dialog rules |
| `_helpers/` | Feature logic that **does** import this component’s types or constants: item matching, placement, collection, roving-id | generic string/array helpers (those are `_utils`) |
| `_lib/` | Wrap one third-party or browser API: focus trap adapter, `matchMedia`, resize observer | junk drawer; if it is pure, use `_utils` |
| `_styles/` | `cva` recipes, CSS modules, `data-slot` class maps | Tailwind strings inlined once on a single part (keep on the part) |
| `_providers/` | Product-only modules that implement `state` / `actions` / `meta` | visual parts (those stay in `_components`) |
| `_context/` | **Do not create.** Context object lives next to the hook in `_hooks` | — |
| `_icons/` | SVG components used only here | app-wide icon packs |
| `_assets/` | Images, lottie, fonts used only here | shared public assets |
| `_mocks/` | Fixtures and MSW handlers for this component | production code |
| `_tests/` | Tests when the repo does not colocate `*.test.tsx` | — |
| `_stories/` | Storybook / Histoire | — |
| `_server/` | Server-only helpers (`import "server-only"`) | client parts |
| `_client/` | **Avoid.** Mark the part with `"use client"` instead | — |

## `_utils` vs `_helpers` vs `_lib`

Pick **one** home per function. Never duplicate.

1. **No feature types, no I/O** → `_utils`
2. **Uses this component’s types, constants, or collection rules** → `_helpers`
3. **Talks to a library or the browser behind a stable interface** → `_lib`

If unsure and the function is pure, use `_utils`. Do not create `_helpers` and
`_utils` in the same component unless both rules actually fire.

Banned names: `_ultils`, `_helper`, `_util`, `_fns`, `_misc`, `_shared`.

## File names

- Folders: kebab-case (`_components`, not `_Components`)
- Part files: kebab-case matching the export (`trigger.tsx` → `Trigger`)
- Hooks: `use-<thing>.ts`
- Utils/helpers: verb-noun (`compose-refs.ts`, `get-open-item.ts`)
- Types: `props.ts`, `context.ts`, or `index.ts` when small
- Constants: `data-state.ts`, `keys.ts`, or `index.ts` when small

Keep `_components` **flat**. Do not nest `_components/_components`. If a part
needs a private sub-module, add a sibling file (`content-header.tsx`) or move
non-UI code to `_helpers`.

## Primitive tree

```text
dialog/
  index.ts
  _types/
    props.ts
    context.ts
  _constants/
    data-state.ts
  _hooks/
    use-dialog.ts
  _utils/
    compose-refs.ts
  _helpers/
    get-tabbable.ts
  _components/
    root.tsx
    trigger.tsx
    portal.tsx
    overlay.tsx
    content.tsx
    title.tsx
    close.tsx
```

`use-dialog.ts` creates context, throws if missing, and is the only reader
other parts use.

## Provider-backed product tree

```text
composer/
  index.ts
  _types/
    context.ts
  _constants/
    keys.ts
  _providers/
    channel-provider.tsx
    forward-provider.tsx
  _hooks/
    use-composer.ts
  _helpers/
    build-submit-payload.ts
  _components/
    frame.tsx
    header.tsx
    input.tsx
    footer.tsx
    submit.tsx
```

Variants (`ChannelComposer`, `EditComposer`) live **beside** this folder or in
a sibling `variants.ts` at the root — they compose parts, they are not a new
`_*` type.

A product whose state scope and visual root coincide may use `root.tsx` instead
of `_providers/` plus `frame.tsx`. Do not create a provider adapter directory
merely to satisfy the example tree.

## Import rules

```ts
// allowed — inside dialog/
import { useDialog } from "../_hooks/use-dialog"
import type { DialogContextValue } from "../_types/context"

// forbidden — from app code or another feature
import { useDialog } from "@/components/ui/dialog/_hooks/use-dialog"
```

App code:

```ts
import { Dialog } from "@/components/ui/dialog"
```

## Small-component escape hatch

When the implementation is genuinely small, a single `index.ts` plus one
`_components/` file is enough. Do not add `_types` / `_utils` / `_helpers`
until their contents have a distinct owner.

This escape hatch collapses files, not contracts. It never excuses opaque host
props, missing refs, fixed data rendering, unreachable public parts, or brittle
child discovery. A single production caller does not require extra files, but
it also does not lower the quality expected from an API that is exported as a
compound component.

## Anti-patterns

- Empty `_` folders “for later”
- Mixing primitive `Root` and product `Provider` in one `_components` without
  a kind decision
- Putting the barrel implementation in `index.ts` (re-export only)
- Deep trees: `_components/content/header/title.tsx`
- A catch-all `_lib` that contains utils, helpers, and components
- Exporting from every `_` folder as if it were public API
- Exporting `Item` or `Empty` while a public `List` or `Results` permanently
  hardcodes its own copies with no replacement boundary
