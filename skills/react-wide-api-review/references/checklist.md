# Review checklist

Use this checklist before writing findings.

## Entry inventory

- [ ] Which component, hook, context, type, provider, form, table, or directory is in scope?
- [ ] Is the baseline explicit?
- [ ] Did the user request working tree, staged diff, branch diff, PR, named component, or named module?
- [ ] Are generated files, external libraries, or third-party adapters in scope?
- [ ] Are there design docs, schema files, issue notes, or migration notes that define ownership?

## Field inventory

Create or infer this table:

```text
field | source | direct consumer(s) | propagation path | semantic group | change frequency | render-relevant? | action? | proposed owner | status
```

Questions:

1. Which fields are truly used by this boundary?
2. Which fields are only passed through?
3. Which fields are spread into children?
4. Which fields are used in effects or memo dependencies?
5. Which fields are actions/callbacks?
6. Which fields are stable config?
7. Which fields are volatile render state?
8. Which fields belong in refs/cache/non-render state?
9. Which fields are unused or unverified?
10. Which existing selector/model/schema owns each concern?

## Boundary decision table

| Boundary | Accepts broad object? | Preferred API |
| --- | ---: | --- |
| Page/container | Yes | domain objects, ids, store hooks, full feature state |
| View/panel | Sometimes | grouped view model + local actions |
| Section | Rarely | local group model + local actions |
| Leaf/field | No | primitive props, field hook, selector result |
| Context provider | No for unrelated domains | split by domain/update frequency |
| Context consumer | No | narrow context or selector |
| Hook options | Yes if grouped | `{ id, initialValue, config, callbacks }` |
| Hook return | Yes if grouped | `{ value, meta, status, permissions, actions }` |
| Form field | No | `useField(name)` or field model |
| Table row/cell | No | row/cell data, id, or selector |

## Smell -> transformation

| Smell | Transformation |
| --- | --- |
| 30 flat props | Group by domain, consumer area, and change frequency |
| Entire entity passed to leaf | Pass rendered fields only |
| Hook has many positional args | Convert to grouped options object |
| Options object used as effect dependency | Depend on concrete fields or create object inside effect |
| Hook returns a flat bag | Return `value/meta/status/actions` groups |
| Hook return passed whole downstream | Pass only owned groups or use local selectors |
| Many `onXChange` handlers | Use typed `onFieldChange` or reducer dispatch |
| Huge form controller passed to every field | Use field-level hook or selector |
| Global context contains many domains | Split contexts and provider values |
| Memo not helping | Check unstable object/function props and over-wide boundary |
| Custom deep comparator | Prefer narrower props or stable structural groups |
| `{...props}` tunnel | Replace with named, owned props at the boundary |

## Severity questions

- Does the surface force consumers to know fields they do not own?
- Does it make unrelated updates re-render or re-run effects?
- Does it hide the real field owner behind spreads or pass-through?
- Does it duplicate an existing selector, schema, store slice, or model?
- Does it make future changes likely to land in the wrong layer?
- Is the risk bounded by a documented migration, schema adapter, or design-system boundary?

## Completion checks

- [ ] Every reached implementation-relevant boundary is in the `Recursive Coverage Ledger`.
- [ ] Every relevant field or field group is in the `Field-Flow Ledger`.
- [ ] Every `Finding F#` row has a matching card.
- [ ] Every `Intentional Exception I#` has owner/exit evidence.
- [ ] Every `Not covered` row has a reason and concrete next step.
- [ ] The recommendation matches the highest unresolved severity and coverage state.
