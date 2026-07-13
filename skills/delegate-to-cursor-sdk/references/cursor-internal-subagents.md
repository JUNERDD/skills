# Cursor Internal Subagents

Use this reference when a Cursor task packet allows Cursor to launch internal task/tool subagents inside one Cursor SDK run. Cursor internal subagents are downstream helpers; they are not upstream support, planning, or workstream orchestrator subagents.

## Policy Block

Include this block in every Cursor packet:

```markdown
## Cursor Internal Subagent Policy
- Allowed: <disabled | read-only-analysis | verification | bounded-implementation>
- Default requested model: Grok 4.5 High
- Model verification: requested label only; exact High parameters are unverified, so use `disabled` when exact pinning is required
- Model override authority: none unless an explicit user Cursor-model instruction is quoted here
- Max concurrent internal subagents: <0-4>
- Allowed purposes:
  - <repo survey | test triage | independent review | scoped implementation | none>
- Write policy: <forbidden | parent-only | owned-files-only>
- Background mode: <forbidden | allowed with joined completion report>
- Required evidence: description, model requested, scope, files read or touched, result, risks
```

`@cursor/sdk` 1.0.23 exposes the internal task/Agent-tool model field as a string. It does not expose the top-level structured `{ id, params }` selection for these child calls. Therefore the requested label is useful routing intent, but it is not proof that High reasoning was honored. Never report that internal selection as verified without independent structured SDK evidence.

## Selection

- `disabled`: trivial tasks, single-file edits, high file overlap, unclear scope, or sensitive context.
- `read-only-analysis`: codebase survey, API discovery, test triage, compatibility review, security/privacy/a11y review.
- `verification`: independent diff review, targeted test analysis, acceptance-criteria checking after implementation.
- `bounded-implementation`: only when the packet defines owned files or globs and forbids shared-file edits.

Prefer 1-3 internal subagents. Use 4 only for clearly independent read-only or verification tasks. Avoid double fan-out: when outer hierarchical workstreams already run in parallel, keep internal subagents narrow and local to each workstream.

## Prompt Requirements

Every internal subagent prompt must be self-contained and include:

- exact task and non-goals;
- requested model label: Grok 4.5 High unless explicitly overridden by the user;
- model-verification limit: report the label as requested or observed, never as exact parameter verification;
- read/write limits;
- relevant file paths, globs, or interfaces;
- required output format;
- stop conditions for scope expansion, credentials, destructive commands, migrations, dependencies, external services, billing, deployment, or shared files.

Do not pass secrets, credentials, unrelated proprietary context, or full task history unless required. The parent Cursor agent must wait for foreground subagent results before reporting completion. If background mode is allowed, the parent must join completed results or report exactly what is still pending.

## Review Evidence

Cursor's completion report must include:

```markdown
## Internal Subagents
- <description>: <model requested>, <model observed if the SDK supplies one, otherwise unverified>, <mode>, <scope>, <result>, <files read/touched>, <risk or none>
```

The upstream reviewer must compare this report with `status.json` when available. A `recent_subagents` requested-model value is not independent proof of parameters. Treat internal subagent output as evidence, not authority.
