# Ephemeral Shared Memory

## Contents

[When To Use](#when-to-use) · [Placement](#placement) · [Layout](#layout) · [Ownership](#ownership) · [Content Rules](#content-rules) · [Lifecycle](#lifecycle) · [Cleanup](#cleanup)

Use this reference before creating disk-backed shared memory for a coordinated run. Treat the memory as an owned temporary coordination artifact, not as durable repository documentation or an authority above system, user, or repository instructions.

## When To Use

Create physical shared memory only when at least one condition applies:

- A root planner delegates to one or more subplanners.
- Work spans context compaction, user handoffs, or multiple scheduling turns.
- Several workers need the same accepted decision, contract version, discovery, or validation reference.
- Repeated rediscovery or large handoffs would otherwise pollute planner context.

Skip it for trivial work, a single self-contained worker, or a run whose state already has an authoritative host-provided ledger.

## Placement

Choose one unique run root in this order:

1. Use an exact user- or host-provided shared session directory when its ownership and cleanup policy are explicit.
2. Use an established repository-local temporary convention when it is shared by all participating workers and is already ignored or expected by the repository.
3. Otherwise create a unique directory below the operating system's temporary root when every participating worker can access the same host filesystem.
4. Use `<workspace-root>/tmp/multitask-coordinator/<run-id>/` only when workers share the workspace but cannot share the operating-system temporary root. Do not edit ignore rules automatically; record the transient dirty-state impact and clean it before closeout.

Use a unique, non-sensitive run ID and refuse to reuse an existing directory. Record and pass the exact absolute path; never recover a session by scanning a temp directory or selecting the latest match.

Do not place ephemeral memory in:

- the installed skill directory;
- source, generated, or package directories;
- `docs/plans`, `.codex/plans`, or another durable documentation path unless the user requests retention;
- a caller-owned artifact directory whose contents the coordinator does not exclusively own.

If workers do not share a filesystem, do not create disk-backed shared memory. Use bounded handoffs or runtime-native messages instead.

## Layout

Use this minimal layout and create only needed entries:

```text
<run-root>/
├── .multitask-coordinator-session.json   # root-owned identity and cleanup marker
├── index.md                              # root-owned compact map
├── decisions/                            # one file per owned decision domain
├── subtrees/                             # one file per subplanner
└── handoffs/                             # one file per worker when a disk handoff is needed
```

The marker records the run ID, creator, workspace, creation time, cleanup owner, and retention mode. The root parent owns the marker and `index.md` for the full run.

## Ownership

- Assign one writer to every memory file.
- Let the root parent update `index.md` and the session marker.
- Let each decision owner update only `decisions/<domain>.md` for its exclusive domain.
- Let each subplanner update only its `subtrees/<subtree-id>.md` and explicitly assigned descendant files.
- Give a worker a unique `handoffs/<node-id>.md` only when its output must survive context loss; otherwise return the handoff normally.
- Do not let multiple workers append to a shared log or ledger. Submit candidate memory entries to the owning planner instead.

Pass each worker only the exact memory files relevant to its contract, with read/write authority stated explicitly. Do not inject the whole run root by default.

## Content Rules

Store only compact coordination state:

- accepted decisions, owners, versions, and affected nodes;
- stable contract references and scope boundaries;
- confirmed discoveries with source paths or evidence references;
- blockers, dependency transitions, and accepted handoff summaries;
- validation commands and bounded result references.

Label proposals, inferences, and superseded entries explicitly. Prefer references to code, logs, or artifacts over copied content. Never store credentials, secrets, capability URLs, full private prompts, raw event streams, or unsupported claims.

Every material entry identifies its scope, owner, status, evidence, and last update. A worker reports the decision or memory version it consumed so the parent can detect stale work.

## Lifecycle

1. Create one run root and marker before the first shared-memory-dependent dispatch.
2. Initialize `index.md` with the root objective, active decision domains, subtree owners, and exact relevant file paths.
3. Pass exact paths in subplanner and worker contracts.
4. Read the owned file before updating it; preserve superseded decisions with their replacement evidence.
5. Update the index after accepted decisions, subtree handoffs, blockers, and contract revisions—not after every minor event.
6. Keep the run root through retries, bounded follow-ups, context compaction, and integrated verification.
7. Stop writing after terminal acceptance or reconciled abandonment, then apply the cleanup gate.

## Cleanup

Only the root cleanup owner may remove the run root. Clean up only when no worker, subplanner, retry, follow-up, or unresolved handoff still depends on it and all evidence needed after deletion has been copied into the final result or a user-approved durable artifact.

Before deletion, verify the exact marker, run ID, path containment, and expected owned entries. Refuse cleanup if the marker is missing, the root contains a symlink or unowned file, ownership is ambiguous, or the run is incomplete. Never use a broad recursive target, glob, shared directory, `latest` path, or unresolved environment variable.

Retain and report the exact path when the user requests retention, repository convention requires it, or safe cleanup cannot be proven. Never delete caller-owned or host-owned artifacts. After successful cleanup, report that the owned ephemeral memory was removed.
