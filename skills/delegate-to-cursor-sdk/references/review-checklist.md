# Review Checklist

Use this reference whenever downstream output returns from Cursor, a support subagent, a planning subagent, or a workstream orchestrator.

## Routing Review

- The selected mode is the lightest safe route.
- The routing decision includes risk level, risk gates, workspace strategy, Cursor SDK runtime, Cursor mode, SDK conversation mode, Cursor model, internal subagent policy, authorization state, and live monitor choice.
- Any subagent used has a bounded scope and cannot approve quality.
- Cursor model is `composer-2.5 fast=true` unless an explicit user Cursor-model instruction is recorded.
- Authorization was handled through `CURSOR_API_KEY`, a named env var, or the wrapper's hidden prompt; the key was not copied into chat, task packets, prompts, or logs.

## Task Packet Review

- The task packet has exactly one authority heading:
  - `## Master Direct Implementation Instructions`
  - `## Approved Upstream Plan`
  - `## Approved Local Plan`
  - `## User-Provided Approved Plan`
  - `# Cursor Follow-up Task Packet`
- The packet contains no unresolved template placeholders.
- In-scope and out-of-scope items are explicit.
- Stop conditions cover dependencies, migrations, destructive commands, credentials, public APIs, billing, deployment, and scope expansion.
- Verification commands are stated.
- Cursor internal subagent policy is present and bounded.

## Cursor SDK Output Review

- Compare output against the authority section, not Cursor's interpretation.
- Inspect the diff; do not rely only on summaries.
- Confirm no unrelated files, generated artifacts, lockfiles, or formatting churn were introduced without authorization.
- Confirm no secrets, credentials, production data, or external service changes were used.
- Confirm no commits, pushes, deployments, billing changes, or destructive commands occurred.
- Confirm status metadata agrees with routing: implementation `@cursor/sdk`, runtime, mode, SDK conversation mode, model, sandbox state, authorization state, and unsafe override reasons.
- For cloud runs, inspect any branch/PR metadata before claiming implementation is ready.

## Verification Review

- Run or inspect required verification.
- If verification was not run, require a concrete reason.
- Treat passing tests as evidence, not complete proof.
- For failures, classify whether the issue is in scope, out of scope, environmental, authorization-related, or blocking.

## Workstream Review

- Owned files and locked files were respected.
- Interface contracts across workstreams still match.
- Local completion reports include Cursor run paths, internal subagent evidence, files touched, verification, deviations, and risks.
- Integration order is clear before combining workstreams.

## Follow-up Gate

Use a bounded follow-up packet only when all are true:

- the finding is specific and evidence-backed;
- allowed files or behaviors are narrow;
- no new product scope or architecture is introduced;
- the follow-up packet has `# Cursor Follow-up Task Packet` as its sole authority heading;
- maximum loop count has not been exceeded;
- Cursor SDK authorization remains available.

## Verdict Template

```markdown
## Upstream Review Verdict
Verdict: <accepted | accepted with notes | needs bounded follow-up | blocked>
Reason: <one paragraph>
Authorization: <authorized | blocked pending user authorization | not needed>
Verification: <commands and results>
Remaining risks: <none or list>
User decisions needed: <none or list>
```
