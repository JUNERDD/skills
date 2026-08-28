# Composition and house rules

Apply these rules after classifying the API as primitive or product. They are
the complete composition contract for this skill.

## React baseline

Read `react` in the nearest `package.json`.

| Version | Components | Context |
| --- | --- | --- |
| **19+** | `ref` is a normal prop. No `forwardRef`. | `use(Context)`. `<Context value={...}>` |
| **18** | `forwardRef` for forwarded refs | `useContext`. `<Context.Provider value={...}>` |

If the file already uses the other style, match the file. Do not churn a
folder to “upgrade” APIs unless asked.

## Quality is not caller-counted

The number of current production call sites is not a public-API quality gate.
One caller may still justify a compound component when the unit owns meaningful
interaction, accessibility, state coordination, repeated-data rendering, or
independently replaceable regions. Do not use “only one caller” to justify:

- hardcoded public markup or content
- dropped native props, refs, styles, or event handlers
- exported parts that a consumer cannot actually substitute
- state coupled to a visual layout when those responsibilities are distinct
- a monolith whose known variation axes already cross ownership boundaries

Caller count does constrain evidence for speculative generality. Do not invent
configuration for imagined products. Derive the narrowest complete seams from
the responsibilities already present: state ownership, data iteration, host
semantics, content, styling, interaction, and external integration. File
extraction and API quality are separate decisions; a one-off component can stay
feature-local or even colocated while still honoring a strong contract.

## Shared public-part contract

### Host transparency

Every public part that renders a host element or public project component must:

- extend that host's or component's supported props, omitting only deliberate
  name conflicts
- forward the consumer ref to the behavior-owning element
- pass through remaining native, `aria-*`, and `data-*` props
- preserve consumer `className` and `style` while adding internal styling
- compose consumer and internal event handlers with an intentional,
  documented cancellation rule

Do not expose only `className` when a real host exists. Do not spread props in a
way that accidentally removes required semantics, state attributes, or internal
behavior. Use an existing event/ref/class/style merge helper when available;
otherwise implement the small merge once and reuse it instead of applying
inconsistent precedence in each part.

One public part should control one consumer-relevant host. Private decorative
nodes are fine; if a nested node needs independent semantics, replacement,
styling, or event ownership, make it a real part or expose a focused content
boundary.

### Public-part reachability

For every exported part, trace how a consumer can use it. A public part is
honest only when either:

1. the consumer places it explicitly in the compound tree, or
2. a convenience owner exposes an explicit slot, child, or render boundary
   through which that part can be replaced.

A convenience facade may compose opinionated defaults, but its fixed internals
do not become configurable merely because those component names are also
exported. Make the facade's default nature explicit, or expose the lower-level
composition beneath it. Do not add public parts that are merely decorative
exports.

Do not discover semantic parts with `Children` traversal plus `child.type`
identity checks, choose only the first matching child, or silently drop unknown
children. Wrappers, memoization, and alternate components break identity-based
discovery. Prefer natural render order and context. If an underlying integration
requires named placements, model those placements as explicit slots or props
with a documented cardinality instead of pretending arbitrary children work.

### Repeated-data rendering

Choose one owner for iteration:

- **Consumer-owned:** the consumer maps data into explicit `Item` parts. The
  compound component coordinates behavior but does not accept the collection
  merely to recreate fixed item markup.
- **Component-owned:** the component owns filtering, grouping, virtualization,
  or collection registration, so `List` or `Results` supplies each item through
  function children or one render callback.

For component-owned iteration, expose the domain item plus stable public state
such as `selected`, `active` or `highlighted`, `disabled`, and `expanded`. If
the callback replaces a behavior-owning host, also provide a merged props/ref
bag that the renderer must apply. If it only replaces contents inside an owned
host, keep keyboard, focus, and ARIA behavior in the part and pass only the data
needed to render contents.

Prefer one rendering boundary over a growing set of `renderIcon`, `renderLabel`,
and `renderIndicator` props. Granular content parts are also valid when the
consumer owns the tree. Default item and empty-state compositions are useful,
but consumers must be able to bypass them when the surrounding API advertises
custom composition.

## Shared context rule

Create context with `null`, not a value that silently no-ops. Expose one local
hook that reads it and throws with the public owner name when the provider is
missing:

```ts
function useDialog() {
  const ctx = use(DialogContext) // or useContext on React 18
  if (!ctx) {
    throw new Error("Dialog.* must be used within <Dialog.Root>")
  }
  return ctx
}
```

For a product API, name the actual owner in the error, for example
`Composer.* must be used within <Composer.Provider>` or `<Selector.Root>`.

Do not use `createContext` defaults like `{ open: false, setOpen: () => {} }`.

A provider instance owns one state scope. Nested instances of the same API must
receive distinct provider values so an inner tree does not read or mutate the
outer tree.

## Primitive contract

A primitive packages reusable behavior and accessibility while consumers own
its structure and styling. This contract applies even when the primitive is
currently used once. Split responsibilities into semantic parts rather than one
component with render switches:

- `Root` coordinates shared state and relationships.
- Host-rendering parts such as `Trigger`, `Content`, `Item`, `Title`, and
  `Description` own their element semantics and forward native props and refs.
- Overlay primitives may add `Portal`, `Overlay`, and `Close` when those are
  real behavioral parts; do not add names merely to imitate another API.
- Preserve the widget's native or ARIA contract, keyboard behavior, focus
  movement/restoration, labeling, and unique element relationships. Styling
  hooks do not substitute for any of these behaviors.

For consumer-observable state, support controlled and uncontrolled modes with
paired names:

- `open` / `defaultOpen` / `onOpenChange`
- `value` / `defaultValue` / `onValueChange`

Use an existing project controllable-state helper or
`@radix-ui/react-use-controllable-state`. Do not expose both `setValue` and
`onValueChange`, and do not mirror a controlled prop into independent local
state.

### `asChild`

Use Slot. Do not `cloneElement`.

```ts
import { Slot } from "@radix-ui/react-slot"

function Trigger({ asChild, ...props }: { asChild?: boolean } & ComponentProps<"button">) {
  const Comp = asChild ? Slot : "button"
  return <Comp {...props} />
}
```

`asChild` accepts exactly one element child, not a fragment, not an array.
Document `asChild?: boolean` on the part that supports it.

The child component must spread received props and forward the received ref.
The resulting element must still satisfy the part's semantics; changing a
button trigger to a non-interactive `div` is not made accessible by `Slot`.

Add `asChild` only to a part that otherwise owns a host element. A state-only
provider has no element to replace.

Use one element-substitution protocol consistently. `asChild` is appropriate
when the consumer only needs to supply the host element. When custom output must
react to live part or item state, use a narrowly scoped render function as
described under repeated-data rendering. Do not add both protocols to every part
or build an ad hoc element-merging system.

### Styling hooks

Expose visual state with `data-state` and stable part ids with `data-slot`.
Do not add `openClassName` / `closedClassName`.

```tsx
<div data-slot="dialog-content" data-state={open ? "open" : "closed"} />
```

Keep `data-state` values finite and documented. Name `data-slot` values by
purpose in kebab-case, not by tag or appearance. Continue to emit native state
and ARIA attributes such as `disabled`, `aria-expanded`, and `aria-controls`;
`data-*` exists for styling and inspection.

When CSS is insufficient and consumers need state-aware markup, expose stable
state through the relevant render boundary or a narrow public hook. Do not make
consumers infer state by querying `data-*` attributes from the DOM.

## Product contract

A product compound component packages domain-specific UI. Choose the state
boundary from ownership, not from how many adapters or callers exist:

- Use `Root` when the state scope and primary visual owner naturally coincide.
- Use `Provider` plus `Frame` when state must serve siblings outside the visual
  frame or when a local, store-backed, URL-backed, or synchronized provider is
  injected independently.

In either shape, separate state implementation from visual parts:

- `Root` or `Provider` publishes a typed context contract.
- `Frame`, when present, owns the primary host element, such as a form.
- Domain parts consume the contract and render focused UI responsibilities.
- The state owner or provider adapter is the only module that may know whether
  state comes from `useState`, a project store, URL state, or synchronization.

Use a context value with three deliberate groups:

```ts
interface ComposerContextValue {
  state: ComposerState
  actions: ComposerActions
  meta: ComposerMeta
}
```

- `state` contains reactive values that affect rendering.
- `actions` exposes semantic operations parts may invoke.
- `meta` carries refs, ids, and non-reactive integration handles. If changing a
  value should re-render consumers, it belongs in `state`, not `meta`.

Parts depend only on this interface. They do not import a concrete store hook,
fetcher, or synchronization client. When provider adapters exist,
`_providers/` translates those implementations into the shared interface.

The provider boundary, not `Frame`, defines access. A preview or action outside
the visual frame may consume the same context when it remains inside the
provider.

Prefer `children` for structural composition. Use a render prop only when the
owner must supply item data or behavior to consumer-rendered content.

Do not add product-mode booleans such as `isThread`, `isEditing`, or `showX` to
a monolithic root. Create named variants such as `ThreadComposer` or
`EditComposer` that choose a provider and visibly compose the required parts.
This rule does not ban real binary state such as `disabled`, `required`, or a
controlled `open` value.

## Types

- Each part owns **one consumer-relevant** host element (or Slot); private
  decorative nodes do not invalidate this rule.
- Public props extend that host or underlying public project component:
  `ComponentProps<"button">` plus `asChild`, for example.
- Export prop types from `_types` (or the part file if the component is tiny).
- Do not collide native props (`onChange` vs `onValueChange` — pick the
  primitive convention above and keep it).

Do not implement a context-scope abstraction unless the project already uses
one and ordinary nested provider instances cannot express the required
isolation.

## Contract verification

Before declaring the component complete, prove the seams the API advertises.
Use the repository's proportionate mechanism: a focused test, story, fixture,
typechecked example, or direct usage audit. At minimum verify applicable cases:

- consumer host props, class/style, event handlers, and refs reach the intended
  element without removing internal behavior
- an advertised item, empty state, trigger, content region, or renderer can be
  replaced without copying the component's state or accessibility logic
- alternate wrapping does not depend on exact `child.type` identity
- controlled and uncontrolled state follow the same observable contract
- required semantics, keyboard behavior, focus, and ARIA survive customization

This proof does not require a second production caller. A small alternate
composition is enough to validate a seam; do not create a fake generalized API
merely to make the example look different.

## Public barrel

```ts
export const Name = {
  Root, // or Provider + Frame for product
  Trigger,
  Content,
}
```

Hooks stay internal by default. Export a narrow `useName` only when consumers
must author behavior-aware parts that cannot be expressed through public parts,
children, or render boundaries. Return a stable public contract, not the raw
mutable context implementation.
