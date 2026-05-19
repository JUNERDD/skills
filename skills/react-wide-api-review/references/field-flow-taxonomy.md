# Field-flow taxonomy

Use these categories in the `Field-Flow Ledger` and in finding evidence.

## Contents

- [Flow categories](#flow-categories)
- [Boundary kinds](#boundary-kinds)

## Flow categories

### Directly consumed

The boundary reads or renders the field itself.

Examples:

```tsx
<UserName name={user.name} />
if (status.saving) return <Spinner />
```

Direct consumption is not automatically safe. The question is whether the boundary owns the field.

### Passed through

The boundary receives a field or group and forwards it without meaningful ownership.

```tsx
function ContactSection({ form }) {
  return <EmailField form={form} />;
}
```

Pass-through becomes risky when it is deep, broad, or hides the real owner.

### Spread propagated

A spread hides which fields cross the boundary.

```tsx
<Child {...props} />
<Column {...columnConfig} />
```

Spreads are not always wrong, but they require extra tracing and often reduce reviewability.

### Derived

The field participates in a computed value.

```tsx
const canSave = permissions.canEdit && meta.valid && !status.saving;
```

Check whether the derived value belongs closer to the source or closer to the consumer.

### Effect-bound

The field or group appears in an effect dependency or drives side effects.

```tsx
useEffect(() => sync(options), [options]);
```

Whole-object effect dependencies are high-risk when object identity is unstable or when unrelated fields re-run the effect.

### Memo-bound

The field or group appears in `useMemo`, `useCallback`, or a memoized component boundary.

```tsx
const rows = useMemo(() => buildRows(table), [table]);
```

Check whether a narrower dependency would be more accurate.

### Context-propagated

The field enters a context provider or is read from context.

```tsx
<AppContext.Provider value={{ user, theme, cart, actions }} />
const { theme } = useContext(AppContext);
```

Risk rises with unrelated domains, volatile fields, or many consumers.

### Hook-return propagated

A custom hook returns a wide object and callers pass it through or consume only small slices.

```tsx
const editor = useUserEditor();
return <EditorView editor={editor} />;
```

Prefer grouped returns or local selectors when consumers diverge.

### Hook-options propagated

A custom hook receives a wide options/config object.

```tsx
useDataGrid({ rows, columns, filters, sorting, pagination, selection, callbacks });
```

Options are reasonable when grouped by concern and not treated as a single effect dependency.

### Callback/action

The field is a function prop, action bag, command, or dispatch.

```tsx
onNameChange(value)
dispatch({ type: 'field/change', field, value })
```

Many callbacks may indicate a missing command boundary, but a stable action group can be appropriate.

### Selector candidate

The consumer only needs a slice that could be selected at the point of use.

```tsx
const node = useEditorStore(s => s.nodes[id]);
```

Use for external store, context selector, form field, table row/cell, and entity lookup patterns.

### Ref/cache/non-render state

The field is not render-relevant and may belong in a ref, cache, or external instance.

```tsx
const cacheRef = useRef(new Map());
```

Do not put non-render fields into wide props or context unless consumers must render from them.

### Unused or unverified

The field appears in the API but no direct read was found in the reviewed scope, or the analysis could not verify usage.

Unused fields may be compatibility surface, dead API, or an untraced dynamic path.

### Out of scope

The field crosses into code not included in the user-specified scope.

Out-of-scope items should still be documented when they limit the gate.

## Boundary kinds

### Container

May hold broad domain objects, ids, store handles, and full feature state. It should adapt wide data into narrower boundaries.

### View / panel

May receive a grouped view model if the group matches the panel's responsibility. It should not pass broad objects unchanged into leaves.

### Section

Should receive local groups such as `contact`, `pricing`, or `toolbarState`. It should not know unrelated domains.

### Leaf / field

Should receive primitives, a narrow local model, or a field-level selector result. Whole form/table/page/domain objects are suspect.

### Hook

Should accept grouped options and return grouped state/actions. It should not force callers to depend on a flat bag when consumers only need slices.

### Context provider

Should usually be split by domain and update frequency. Stable actions often belong in a separate context from volatile state.

### Context consumer

Should not read a broad context when a narrower context or selector is available.

### Form field

Should subscribe to one field or a small group. Passing the whole controller to every field is a common broadcast problem.

### Table row/cell

Should receive row/cell data, ids, or selectors. Passing the whole grid/table instance to every cell is suspect unless it is a stable adapter.
