# Fix patterns for receiving React wide API reviews

Use the smallest fix that closes the reported field-flow or ownership problem.

## Contents

- [1. Narrow a leaf component](#1-narrow-a-leaf-component)
- [2. Replace pass-through with an adapter at the owner boundary](#2-replace-pass-through-with-an-adapter-at-the-owner-boundary)
- [3. Split a hook return bag](#3-split-a-hook-return-bag)
- [4. Fix a hook options dependency](#4-fix-a-hook-options-dependency)
- [5. Split context state and actions](#5-split-context-state-and-actions)
- [6. Collapse callback explosion into a typed command](#6-collapse-callback-explosion-into-a-typed-command)
- [7. Replace context reads with selectors where available](#7-replace-context-reads-with-selectors-where-available)
- [8. Preserve intentional adapters](#8-preserve-intentional-adapters)

## 1. Narrow a leaf component

Before:

```tsx
function EmailField({ form }: { form: UserFormController }) {
  return (
    <Input
      value={form.values.email}
      error={form.errors.email}
      onChange={value => form.setValue('email', value)}
    />
  );
}
```

After:

```tsx
type EmailFieldProps = {
  value: string;
  error?: string;
  onChange(value: string): void;
};

function EmailField({ value, error, onChange }: EmailFieldProps) {
  return <Input value={value} error={error} onChange={onChange} />;
}
```

Or use a field subscription:

```tsx
function EmailField() {
  const email = useField('email');
  return <Input value={email.value} error={email.error} onChange={email.setValue} />;
}
```

## 2. Replace pass-through with an adapter at the owner boundary

```tsx
function ContactSection({ value, meta, actions }: ContactSectionProps) {
  return (
    <EmailField
      value={value.email}
      error={meta.errors.email}
      onChange={next => actions.changeField('email', next)}
    />
  );
}
```

## 3. Split a hook return bag

Before:

```tsx
const editor = useUserEditor();
return <UserEditorView editor={editor} />;
```

After:

```tsx
const { value, meta, status, permissions, actions } = useUserEditor();
return (
  <UserEditorView
    value={value}
    meta={meta}
    status={status}
    permissions={permissions}
    actions={actions}
  />
);
```

## 4. Fix a hook options dependency

Before:

```tsx
function useGrid(options: GridOptions) {
  useEffect(() => {
    syncGrid(options);
  }, [options]);
}
```

After:

```tsx
function useGrid(options: GridOptions) {
  const { endpoint, pagination, sorting } = options;

  useEffect(() => {
    syncGrid({ endpoint, pagination, sorting });
  }, [endpoint, pagination.page, pagination.pageSize, sorting.key, sorting.direction]);
}
```

## 5. Split context state and actions

```tsx
const actions = useMemo(() => ({ save, cancel, changeField }), [save, cancel, changeField]);

return (
  <EditorStateContext.Provider value={state}>
    <EditorActionsContext.Provider value={actions}>
      {children}
    </EditorActionsContext.Provider>
  </EditorStateContext.Provider>
);
```

## 6. Collapse callback explosion into a typed command

```tsx
type EditorAction =
  | { type: 'field/change'; field: keyof EditorValue; value: EditorValue[keyof EditorValue] }
  | { type: 'save' }
  | { type: 'cancel' };
```

Prefer a generic field helper when possible:

```tsx
function changeField<K extends keyof EditorValue>(field: K, value: EditorValue[K]) {
  dispatch({ type: 'field/change', field, value });
}
```

## 7. Replace context reads with selectors where available

```tsx
const selectedNode = useEditorStore(state => state.nodes[nodeId]);
const isSelected = useEditorStore(state => state.selectedIds.has(nodeId));
```

## 8. Preserve intentional adapters

Do not split wide generated/schema adapters unless they leak into consumers that should not know the full schema.

A safer fix is often:

```tsx
function ProductFormAdapter({ product }: { product: ProductApiSchema }) {
  const value = toProductFormValue(product);
  return <ProductForm value={value} />;
}
```

The wide external schema stays at the adapter; the UI receives a local model.
