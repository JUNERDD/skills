# Cursor Internal Subagents

Use this reference when a Cursor task packet allows Cursor to launch `Task()` / `taskToolCall` subagents. Cursor internal subagents are downstream helpers inside one Cursor run; they are not upstream support, planning, or workstream orchestrator subagents.

## Policy Block

Include this block in every Cursor packet:

```markdown
## Cursor Internal Subagent Policy
- Allowed: <disabled | read-only-analysis | verification | bounded-implementation>
- Default model: composer-2.5-fast
- Model override authority: none unless an explicit user Cursor-model instruction is quoted here
- Max concurrent internal subagents: <0-4>
- Allowed purposes:
  - <repo survey | test triage | independent review | scoped implementation | none>
- Write policy: <forbidden | parent-only | owned-files-only>
- Background mode: <forbidden | allowed with joined completion report>
- Required evidence: description, model requested, scope, files read or touched, result, risks
```

## Selection

- `disabled`: trivial tasks, single-file edits, high file overlap, unclear scope, or sensitive context.
- `read-only-analysis`: codebase survey, API discovery, test triage, compatibility review, security/privacy/a11y review.
- `verification`: independent diff review, targeted test analysis, acceptance-criteria checking after implementation.
- `bounded-implementation`: only when the packet defines owned files or globs and forbids shared-file edits.

Prefer 1-3 internal subagents. Use 4 only for clearly independent read-only or verification tasks. Avoid double fan-out: when outer hierarchical workstreams already run in parallel, keep internal subagents narrow and local to each workstream.

## Prompt Requirements

Every internal subagent prompt must be self-contained and include:

- exact task and non-goals;
- model requirement: `composer-2.5-fast` unless explicitly overridden by the user;
- read/write limits;
- relevant file paths, globs, or interfaces;
- required output format;
- stop conditions for scope expansion, credentials, destructive commands, migrations, dependencies, or shared files.

Do not pass secrets, credentials, unrelated proprietary context, or full task history unless required. The parent Cursor agent must wait for foreground subagent results before reporting completion. If background mode is allowed, the parent must join completed results or report exactly what is still pending.

## Review Evidence

Cursor's completion report must include:

```markdown
## Internal Subagents
- <description>: <model requested>, <mode>, <scope>, <result>, <files read/touched>, <risk or none>
```

The upstream reviewer must compare this report with `status.json` when available. Treat internal subagent output as evidence, not authority.
