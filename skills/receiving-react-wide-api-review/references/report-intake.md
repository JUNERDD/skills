# Report intake consistency checks

Before editing code, verify that the report is internally consistent and still matches the current scope.

## Required sections

A complete `react-wide-api-review` report should contain:

- `Scope`
- `Gate Snapshot`
- `Complete Wide-API Index`
- `Block`
- `Discuss`
- `Watch`
- `Intentional Exceptions`
- `Field-Flow Ledger`
- `Recursive Coverage Ledger`
- `Evidence Appendix`

Missing sections do not automatically invalidate the report, but they reduce confidence and may require regeneration.

## Enumeration checks

- Every `F#` in `Complete Wide-API Index` should have one card in `Block`, `Discuss`, or `Watch`.
- Every finding card should appear in `Complete Wide-API Index`.
- Every `Finding F#` ledger row should map to an existing finding.
- Every `Intentional Exception I#` ledger row should map to an intentional exception.
- Every `Not covered` implementation-relevant or unknown row should have a reason and next step.

## Scope checks

- Does the scope reviewed match the user's current requested scope?
- Does the baseline still exist or match the current checkout?
- Was the report generated from staged diff while fixes will be made in the working tree?
- Were generated or external files included/excluded intentionally?
- Did the report mark coverage incomplete?

## Staleness checks

Regenerate or clarify the report when:

- the report refers to files that no longer exist
- finding line numbers or code paths no longer match
- the current branch has changed materially
- a finding was already fixed before intake
- the report's recommendation contradicts its findings or coverage state
- the ledgers and index disagree

## Disposition requirements

Do not close the report until every item is one of:

- fixed
- disproved
- narrowed
- downgraded with evidence
- confirmed as intentional exception
- closed as a coverage gap
- carried forward with a concrete next action
- blocked pending clarification
