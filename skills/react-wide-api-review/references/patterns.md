# React wide-field API refactor patterns

Use these patterns after the review identifies a structural liability.

## Contents

- [1. Container broad, leaf narrow](#1-container-broad-leaf-narrow)
- [2. Flat props -> grouped view model](#2-flat-props---grouped-view-model)
- [3. Group by domain and change frequency](#3-group-by-domain-and-change-frequency)
- [4. Hook options object, but not a flat bag](#4-hook-options-object-but-not-a-flat-bag)
- [5. Hook return as state/meta/status/actions](#5-hook-return-as-statemetastatusactions)
- [6. Field-level form subscription](#6-field-level-form-subscription)
- [7. Selector-based store consumption](#7-selector-based-store-consumption)
- [8. Split context by domain and update frequency](#8-split-context-by-domain-and-update-frequency)
- [9. Replace callback explosion with commands](#9-replace-callback-explosion-with-commands)
- [10. Move effect object construction inside the effect](#10-move-effect-object-construction-inside-the-effect)
- [11. Replace deep comparator with narrower props](#11-replace-deep-comparator-with-narrower-props)
- [12. Preserve intentional adapters](#12-preserve-intentional-adapters)

## 1. Container broad, leaf narrow

Container components may load broad data. Leaf components should not receive broad data.

```tsx
function UserPanel({ user, permissions, actions }: UserPanelProps) {
  return (
    <>
      <UserHeader
        name={user.name}
        avatarUrl={user.avatarUrl}
        title={user.title}
      />
      <UserToolbar
        canEdit={permissions.canEdit}
        canDelete={permissions.canDelete}
        onEdit={actions.edit}
        onDelete={actions.delete}
      />
    </>
  );
}
```

## 2. Flat props -> grouped view model

Use grouped props when the component truly owns a view-level concern.

```tsx
type ProductEditorProps = {
  value: ProductEditorValue;
  meta: ProductEditorMeta;
  status: ProductEditorStatus;
  permissions: ProductEditorPermissions;
  actions: ProductEditorActions;
};
```

Avoid anonymous groups named only `data`, `props`, or `options` unless the name is conventional and local.

## 3. Group by domain and change frequency

Separate fields that change for different reasons.

```tsx
type EditorProps = {
  value: EditorValue;          // volatile render data
  meta: EditorMeta;            // validation/touched/dirty
  status: EditorStatus;        // async/loading state
  config: EditorConfig;        // stable configuration
  actions: EditorActions;      // stable commands
};
```

## 4. Hook options object, but not a flat bag

```tsx
useUserEditor({
  userId,
  initialValue,
  validation,
  permissions,
  features,
  callbacks,
});
```

Inside the hook, effects should depend on concrete fields or stable groups, not the entire options object.

## 5. Hook return as state/meta/status/actions

```tsx
function useUserEditor() {
  return {
    value,
    meta,
    status,
    permissions,
    actions,
  };
}
```

Callers should pass only the groups a child owns.

## 6. Field-level form subscription

Bad:

```tsx
<EmailField form={form} />
```

Better:

```tsx
function EmailField() {
  const email = useField('email');
  return <Input value={email.value} onChange={email.setValue} />;
}
```

Or:

```tsx
<EmailField value={email.value} error={email.error} onChange={email.setValue} />
```

## 7. Selector-based store consumption

Bad:

```tsx
const editor = useEditorStore();
return <Node node={editor.nodes[id]} viewport={editor.viewport} />;
```

Better:

```tsx
const node = useEditorStore(state => state.nodes[id]);
const selected = useEditorStore(state => state.selectedIds.has(id));
```

## 8. Split context by domain and update frequency

Bad:

```tsx
<AppContext.Provider value={{ user, theme, cart, notifications, actions }} />
```

Better:

```tsx
<AuthContext.Provider value={authValue}>
  <ThemeContext.Provider value={themeValue}>
    <CartContext.Provider value={cartValue}>{children}</CartContext.Provider>
  </ThemeContext.Provider>
</AuthContext.Provider>
```

Often split state from actions:

```tsx
<EditorStateContext.Provider value={state}>
  <EditorActionsContext.Provider value={actions}>{children}</EditorActionsContext.Provider>
</EditorStateContext.Provider>
```

## 9. Replace callback explosion with commands

Bad:

```tsx
<UserEditor
  onNameChange={setName}
  onEmailChange={setEmail}
  onPhoneChange={setPhone}
/>
```

Better:

```tsx
<UserEditor onFieldChange={changeField} />
```

```tsx
function changeField<K extends keyof UserEditorValue>(
  field: K,
  value: UserEditorValue[K]
) {
  dispatch({ type: 'field/change', field, value });
}
```

## 10. Move effect object construction inside the effect

Bad:

```tsx
useEffect(() => {
  sync(config);
}, [config]);
```

Better:

```tsx
useEffect(() => {
  sync({ endpoint, timeout, retry });
}, [endpoint, timeout, retry]);
```

## 11. Replace deep comparator with narrower props

Bad:

```tsx
export default memo(UserPanel, deepEqual);
```

Better:

```tsx
const UserHeader = memo(function UserHeader({ name, avatarUrl }: Props) {
  // ...
});
```

## 12. Preserve intentional adapters

Some wide APIs are acceptable:

- generated GraphQL or OpenAPI types
- schema-driven forms
- table column definitions
- design-system wrappers
- backward compatibility adapters
- migration shims with owner and exit trigger

Do not split them unless consumers are forced to subscribe to unrelated runtime changes or the adapter leaks beyond its boundary.
