# Scoring model

Use this model to prioritize review attention. Do not treat the numeric score as the finding severity by itself. Severity still depends on evidence and ownership impact.

## Candidate score

Start at `0`.

### Width

- `+1` for 10-14 top-level fields
- `+2` for 15-24 top-level fields
- `+3` for 25-39 top-level fields
- `+4` for 40+ top-level fields

For generated schemas, count field groups instead of raw generated fields when the generated API is intentional.

### Consumer fan-out

- `+1` for 2-3 consumers
- `+2` for 4-7 consumers
- `+3` for 8+ consumers
- `+2` if consumers belong to different UI regions or feature domains

### Pass-through depth

- `+1` for one pass-through layer
- `+2` for two pass-through layers
- `+3` for three or more layers
- `+2` for spread propagation that hides fields

### Context fan-out

- `+2` for a provider value with unrelated domains
- `+2` for volatile state mixed with stable actions/config
- `+3` for many consumers that read small slices
- `+1` for provider value created inline without memoization

### Hook risk

- `+2` for hook with 5+ positional parameters
- `+2` for flat hook return with 10+ fields
- `+2` for callers passing the whole hook return downstream
- `+3` for `useEffect(..., [options])` or similar whole-object side-effect dependency

### Form/table/list risk

- `+3` for leaf field/cell receiving whole form/table/list controller
- `+2` for field/cell re-render path driven by unrelated fields
- `+2` for lack of field-level selector when the library supports one

### Callback/action explosion

- `+1` for 5-8 related callback props
- `+2` for 9+ related callback props
- `+2` if callbacks encode the same field-change command manually

### Existing abstraction duplication

- `+3` when the wide object duplicates an existing selector, schema, domain model, adapter, or store slice
- `+2` when the owner of validation/update/rendering becomes ambiguous

### Mitigating factors

Subtract points when there is strong evidence of a safe boundary:

- `-2` deliberate schema adapter, generated type, or design-system API with documented owner
- `-2` stable config object constructed once and not used as a volatile dependency
- `-2` component truly owns the full grouped view model and does not pass it through
- `-1` wide object is only used at a container boundary
- `-1` migration shim has owner and exit trigger

## Suggested attention bands

- `0-2`: likely no finding or `Watch`
- `3-5`: inspect for `Watch` or `Discuss`
- `6-8`: likely `Discuss`, possible `Block` with strong evidence
- `9+`: high-priority review path; likely `Block` if ownership or subscription risk is verified

## Severity calibration

Use `Block` only when the evidence shows a real engineering gate problem:

- bad owner cannot be fixed locally
- consumers are unavoidably over-subscribed
- future changes are likely to land in the wrong layer
- side effects can re-run because unrelated fields change
- context fan-out affects many consumers
- spread/pass-through makes the boundary unreviewable

Use `Discuss` when the risk is plausible but intent or impact is unclear.

Use `Watch` when the debt is bounded, local, or can be tracked without blocking approval.

Use `Intentional Exception` when the wide surface is deliberate, documented, and bounded.
