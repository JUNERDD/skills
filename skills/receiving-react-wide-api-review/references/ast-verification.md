# AST-First Verification for Received Reports

Use AST or language-server analysis first when verifying a `react-wide-api-review` report, if the environment provides it.

The receiving skill should not blindly trust a previous report. It should re-check whether each cited field-flow edge still exists in the current checkout.

## Verification priority

Use verification sources in this order:

1. AST or language-server evidence.
2. TypeScript compiler or project-aware symbol/reference data.
3. Heuristic scripts and repository search.
4. Manual inspection.
5. Runtime or profiler evidence when the finding is about render fan-out or subscriptions.

AST verification is especially important when the report mentions spreads, destructuring, aliases, context consumers, hook return objects, or dependency arrays.

## What to verify with AST

For every finding or coverage row, verify:

- the cited component, hook, context, type, or file still exists
- the cited props/options/return/context fields still exist
- direct reads still occur where reported
- pass-through edges still forward the same object or fields
- JSX spreads still resolve to the same source expression
- hook return destructuring or whole-object propagation still occurs
- context provider values still combine the reported domains
- consumers still read the reported context fields
- effect/memo/callback dependency arrays still contain the reported broad object or fields
- any proposed selector or field-level boundary now exists if the item was supposedly fixed

## Disposition impact

Use AST evidence to choose the disposition:

- `Fixed` when the field-flow edge is gone or narrowed in current code.
- `Disproved` when the original report's edge does not exist and likely never did.
- `Narrowed` when the edge remains but blast radius or ownership is smaller.
- `Still applies` when the edge remains materially unchanged.
- `Open coverage gap` when AST cannot resolve dynamic access, spreads, generated code, or out-of-scope boundaries.

Do not downgrade a finding based only on a broad search miss if AST or call-site analysis is available.

## Reporting fallback

If AST is unavailable, state the verification method and the unresolved risk:

```txt
Verification method: heuristic search + manual inspection; AST unavailable, so spread `props` in ContactSection remains an open coverage gap.
```
