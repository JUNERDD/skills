# Migration guidance

Use this when a finding needs a realistic migration path.

## Contents

- [1. Start with the smallest safe boundary](#1-start-with-the-smallest-safe-boundary)
- [2. Introduce named local types](#2-introduce-named-local-types)
- [3. Add an adapter layer](#3-add-an-adapter-layer)
- [4. Migrate from leaf to section to view](#4-migrate-from-leaf-to-section-to-view)
- [5. Stabilize only necessary groups](#5-stabilize-only-necessary-groups)
- [6. Replace callback explosion carefully](#6-replace-callback-explosion-carefully)
- [7. Split context without breaking consumers](#7-split-context-without-breaking-consumers)
- [8. Close coverage gaps](#8-close-coverage-gaps)
- [9. Avoid churn traps](#9-avoid-churn-traps)

## 1. Start with the smallest safe boundary

Do not refactor the whole feature unless the recursive review shows that every layer is wrong. Start where the field-flow ledger shows pass-through or over-subscription.

Typical first targets:

- leaf component receiving whole domain model
- field component receiving whole form controller
- provider value mixing domains
- hook return passed as one object to multiple regions
- effect depending on a wide options object

## 2. Introduce named local types

Before moving code, name the boundary that should exist.

```tsx
type ContactSectionValue = {
  email: string;
  phone?: string;
};

type ContactSectionMeta = {
  errors: Pick<UserEditorErrors, 'email' | 'phone'>;
};
```

Named types make the migration reviewable.

## 3. Add an adapter layer

Keep old callers working while you narrow children.

```tsx
function UserEditorView(props: UserEditorViewProps) {
  const contactValue = pickContactValue(props.value);
  const contactMeta = pickContactMeta(props.meta);

  return <ContactSection value={contactValue} meta={contactMeta} actions={props.actions} />;
}
```

## 4. Migrate from leaf to section to view

The safest order is usually:

1. narrow leaf props
2. narrow section props
3. group view props
4. adjust hook return shape
5. split contexts
6. remove old pass-through props

## 5. Stabilize only necessary groups

Use `useMemo` and `useCallback` only where identity matters:

- provider values
- props to memoized expensive children
- hook return objects passed downstream
- effect/memo dependencies

Do not add memoization before narrowing the consumer boundary.

## 6. Replace callback explosion carefully

When collapsing callbacks, preserve type safety.

```tsx
function changeField<K extends keyof UserEditorValue>(
  field: K,
  value: UserEditorValue[K]
) {
  dispatch({ type: 'field/change', field, value });
}
```

Avoid `field: string, value: unknown` unless the source is truly dynamic.

## 7. Split context without breaking consumers

Migration pattern:

1. create new narrow contexts
2. populate them from the old provider
3. migrate consumers one group at a time
4. remove old broad context after all consumers move

```tsx
<EditorStateContext.Provider value={state}>
  <EditorActionsContext.Provider value={actions}>{children}</EditorActionsContext.Provider>
</EditorStateContext.Provider>
```

## 8. Close coverage gaps

After code changes:

- rerun the report or targeted recursive trace
- verify every former `Not covered` implementation boundary
- ensure findings are fixed, narrowed, disproven, or carried forward
- ensure intentional exceptions still have owner and exit trigger

## 9. Avoid churn traps

Do not:

- rename everything without narrowing field flow
- convert every prop to context
- split stable schema objects into dozens of primitives
- introduce deep comparators as the fix
- create a second view model that duplicates the existing store or schema
- remove defensive guards without verifying external/legacy boundaries
