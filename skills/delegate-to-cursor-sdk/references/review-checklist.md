# Review Checklist

Use this reference whenever downstream output returns from Cursor, a support subagent, a planning subagent, or a workstream orchestrator.

## Routing Review

- The selected mode is the lightest safe route.
- The routing decision includes risk level, risk gates, workspace strategy, Cursor SDK runtime, Cursor mode, SDK conversation mode, Cursor model, internal subagent policy, authorization state, live monitor choice, dashboard lifecycle, temporary-artifact ownership, and audit-retention policy.
- Any subagent used has a bounded scope and cannot approve quality.
- Cursor model is the catalog-resolved Grok 4.5 High non-Fast preset unless an explicit user Cursor-model instruction is recorded.
- The CLI sends the preset's complete catalog-defined selection. Any structured model evidence returned by the SDK must match it exactly; absent optional evidence must be reported as unreported, not silently presented as verified.
- Authorization was handled through `CURSOR_API_KEY`, a named env var, or the packaged Next.js authorization route; the key was not copied into chat, task packets, prompts, URLs, continuation records, or logs.
- Any `needs_authorization` state established a global barrier: all live child agents were recorded and paused/interrupted, new scheduling stopped, and only the root waited for the authorization result.
- The barrier recursively covered every descendant, including agents without workstream rows; owned subprocesses were stopped or their disposition was accounted for, and a second enumeration confirmed no descendant remained running. Otherwise the barrier was reported failed, not waiting.
- Browser mode was root-owned. Non-root wrapper invocations used trailing `cursor-delegate ... --auth-mode fail`, waited for their CLI-owned packaged frontend to close, and handed the same packet/status plus process disposition back without enabling an authorization capability or changing cleanup ownership. Root read `authorization.local_url` and `authorization.dashboard_url` from status and presented both in the same handoff; neither the CLI nor the agent opened those authorization links automatically.
- The frontend started without opening a URL. While the key was missing or rejected, neither authorization link nor the local dashboard auto-opened. After key and model preflight both succeeded, the normal live dispatch auto-opened the local dashboard unless the current user explicitly requested `--no-open-dashboard`; CI, headless, background, parallel, or browser-tool-free context was not treated as opt-out authority.
- Dashboard opener failure was non-fatal, reported, and followed by a protected manual handoff. After confirmed auto-open, the original one-time status URL was treated as spent rather than presented again as fresh.
- The authorization and dashboard routes came from the same packaged production Next.js app on an isolated `127.0.0.1:0` listener. The installed CLI did not build frontend source or start a development server/package manager.
- One-time tickets, target-bound HttpOnly sessions, SameSite `strict`, exact Host/Origin checks, CSRF, bounded bodies, no-store responses, and restrictive browser headers protected the local capabilities. No API key or parent control credential appeared in a URL, client bundle/response, child environment, status, metadata, journal, or log.
- Terminal frontend cleanup stayed at the default `0` seconds, or the invoking upstream agent recorded a concrete exceptional reason and an explicit `--dashboard-retention-seconds 1..300`. No Cursor/workstream agent selected retention and no frontend was detached.
- Skill-managed packets and ordinary log bases live below one marker-owned private session outside the target repository. Every dispatch uses `delegation_session.py run` with the exact marker and a unique `--log-name`; the trailing command never passes raw `--log-dir`. Any absolute caller-owned `--retained-log-dir` is explicitly identified and excluded from cleanup forever.

## Task Packet Review

- The task packet has exactly one authority heading:
  - `## Master Direct Implementation Instructions`
  - `## Approved Upstream Plan`
  - `## Approved Local Plan`
  - `## User-Provided Approved Plan`
  - `# Cursor Follow-up Task Packet`
- The packet contains no unresolved template placeholders.
- The packet identifies the upstream lease wrapper without embedding its command, exact session marker, packet/log/status paths, retained-log absolute path, or local capability URL. It exposes only a non-sensitive `--log-name`/correlation value and classifies retention as `none` or `caller-owned-retained` with the exact path withheld.
- In-scope and out-of-scope items are explicit.
- Stop conditions cover dependencies, migrations, destructive commands, credentials, public APIs, billing, deployment, and scope expansion.
- Verification commands are stated.
- Cursor internal subagent policy is present and bounded.
- The `## Cursor Model` section contains exactly one `CLI profile`, `Model`, and `Model params` field matching the CLI selection.

## Cursor SDK Output Review

- Compare output against the authority section, not Cursor's interpretation.
- Inspect the diff; do not rely only on summaries.
- Confirm no unrelated files, generated artifacts, lockfiles, or formatting churn were introduced without authorization.
- Confirm no secrets, credentials, production data, or external service changes were used.
- Confirm no commits, pushes, deployments, billing changes, or destructive commands occurred.
- Confirm status metadata agrees with routing: implementation `@cursor/sdk`, runtime, mode, SDK conversation mode, model, sandbox state, authorization state, and unsafe override reasons.
- Confirm every structured model selection present in system events or `RunResult.model` exactly matches the catalog-resolved preset or explicit override. Treat a mismatch as blocking. When neither optional SDK surface reports a model, require the result to say `not_reported` and do not describe the observed model as verified. For a pure resume, require `sticky_resume_not_overridden` with `resume_sticky` scope and confirm the CLI did not inject a new model or mode.
- Treat every Cursor internal-subagent model label as requested or observed, not parameter-verified. If exact High execution is acceptance-critical, confirm the packet kept internal subagents `disabled`.
- Treat every internal task/Agent-tool descendant as `parent-only` unless the CLI separately retained a real top-level run. Confirm the dashboard did not fabricate an independent Stop from stream-only IDs or tool metadata.
- For cloud runs, inspect any branch/PR metadata before claiming implementation is ready.

## Dashboard And Control Review

- `frontend.dashboard_url` auto-opened only after successful key and model preflight, or was handed only to the current user after an explicit opt-out or opener failure. The capability itself was not repeated in a durable review report, and a confirmed auto-open URL was never re-handed as fresh.
- The browser received only sanitized schema-v2 events/snapshots through AI SDK v7 data parts. Raw `events.ndjson`, API keys, control credentials, and SDK handles did not enter the browser transport.
- Current shadcn chat primitives and AI Elements rendered assistant, reasoning, tool/code, usage, artifact, topology, replay, connection, and terminal states without turning presentation into acceptance evidence.
- The middle execution tape was ordered by `RunEvent.sequence`; step/turn/request/summary/task boundaries stayed in temporal context, and a tool's lifecycle updated one entry by `callId` instead of producing misleading duplicates.
- `stepId`, `modelCallId`, and `callId` correlated the rendered UI without being presented as wall-clock ordering. `requestId` remained a journal/status audit field and was not claimed as a rendered UI association.
- Assistant and thinking deltas accumulated. Empty, shorter, stale, or duplicate completion/conversation payloads did not erase or duplicate richer streamed text; completed thinking stayed available and expandable.
- Replay subscribed before backlog capture, the client cursor advanced only for received events, and animation-frame batching did not drop sequence values.
- The retained event window stayed bounded to 2,000. A server rollover or client-side trim/gap surfaced a sequence watermark and restored aggregate text/state from the authoritative snapshot; it did not silently claim an unlimited or gap-free historical timeline. A slow/disconnected client did not block SDK ingestion.
- Per-agent Stop targeted only a known `independent` active run in the same dispatch. `parent-only` internal agents pointed to the owning parent; terminal/`none` agents exposed no Stop.
- A Stop result was accepted only after correlated SDK cancellation or terminal evidence. Repeated command IDs were idempotent, conflicting reuse was rejected, and terminal races became `already-terminal` rather than false failure.
- Stop All closed admission before cancellation, drained/relisted active agents, and returned per-agent outcomes. Any active, unsupported, timed-out, or failed remainder was reported as `partially-failed`; global success was never inferred from button submission.
- Stop controls were not treated as authority to retry, replace, broaden scope, commit, push, deploy, rotate credentials, or run destructive actions.
- Parent disconnect, CLI signal, startup/authorization failure, normal terminal state, and optional bounded retention all ended with owned child/listener cleanup.

## Verification Review

- Run or inspect required verification.
- If verification was not run, require a concrete reason.
- Treat passing tests as evidence, not complete proof.
- For failures, classify whether the issue is in scope, out of scope, environmental, authorization-related, or blocking.

## Workstream Review

- Every hierarchical workstream has a ledger row with dependencies, ready conditions, ownership, validation, state, and a concrete status path.
- No dependent workstream was unlocked by SDK completion alone; upstream accepted the dependency first.
- Owned files and locked files were respected.
- Interface contracts across workstreams still match.
- Local completion reports include Cursor run paths, internal subagent evidence, files touched, verification, deviations, and risks.
- Integration order is clear before combining workstreams.
- Integrated verification covers cross-workstream behavior, and no ready or required ledger node remains unreviewed.
- If an authorization barrier occurred, every descendant record carries the same barrier generation, `paused_from`, canonical agent task, owned-process disposition, and at most one resume disposition. Cancellation, failure, an unconfirmed pause, or fail-closed reconciliation after a verified key resumed none of them.

## Follow-up Gate

Use a bounded follow-up packet only when all are true:

- the finding is specific and evidence-backed;
- allowed files or behaviors are narrow;
- no new product scope or architecture is introduced;
- the follow-up packet has `# Cursor Follow-up Task Packet` as its sole authority heading;
- maximum loop count has not been exceeded;
- Cursor SDK authorization remains available.

## Owned Artifact Cleanup Gate

Before cleanup:

- Every CLI foreground process has exited, terminal dashboard retention has ended, and no recorded frontend PID remains live.
- Upstream captured the task hash, dispatch/agent/run/request identifiers, runtime/mode, model verification, terminal/Stop outcomes, diff summary, verification results, and verdict without persisting capability URLs or raw sensitive payloads.
- No authorization rerun, resume, bounded follow-up, unreviewed workstream, or ambiguous remote cancellation remains.
- Root holds the exact marker returned by `delegation_session.py start` and has remained cleanup owner throughout; non-root workstreams handed over cleanup evidence and process disposition only, and did not delete local fragments.
- Caller-owned task/plan files, retained audit directories, repository changes, branches/worktrees, and `--keep-workspace-copy` results are outside the deletion set.
- Any `--allow-status`, `--allow-incomplete-run`, `--allow-lease`, or `--allow-temp-artifact` names one exact reconciled in-session path and carries a non-empty `--override-reason`. Temp residue matches only `status.json|metadata.json|snapshot.v2.json` plus `.<positive-pid>.<lowercase-canonical-uuid>.tmp`; no live PID/lease or `starting`/`running` status was overridden.

Run the helper only for `accepted`, `accepted-with-notes`, or an explicitly reconciled/user-authorized abandonment. Accept cleanup only when it reports `cleaned` and the exact session root is absent. If an identity-pinned cleanup manifest remains in the live marker after partial deletion, fix only the reported filesystem obstruction and retry with the same marker and verdict; reject any new or identity-changed entry. A repeated call after successful deletion must be refused because the missing marker cannot re-prove ownership; never treat that refusal as success. On symlink, unknown artifact, active lease/status/PID, containment, or ownership failure, preserve the residue and report `cleanup_blocked`; never widen the target or substitute a recursive delete.

## Verdict Template

```markdown
## Upstream Review Verdict

Verdict: <accepted | accepted with notes | needs bounded follow-up | blocked>
Reason: <one paragraph>
Authorization: <authorized | waiting for user | cancelled | failed | not needed>
Authorization barrier: <not used | paused N, resumed N | paused N, resumed 0 and reason>
Dashboard: <not handed off | handed off without durable URL | unavailable and impact>
Dashboard lifecycle: <terminal-close-default | retained N seconds for recorded exceptional reason>
Control: <none | per-agent outcomes | Stop All outcomes and remaining agents>
Verification: <commands and results>
Temporary artifacts: <cleaned | retained and reason | cleanup blocked/refused and reason>
Audit evidence: <ephemeral session cleaned | caller-owned retained directory>
Remaining risks: <none or list>
User decisions needed: <none or list>
```
