# Owned Delegation Artifacts

Read this reference before creating a task packet and again before reporting a terminal result. It defines which temporary files this skill owns, when they must survive, and how they are removed safely.

## Ownership Boundary

Direct CLI usage and skill-managed usage have different defaults:

| Owner | Artifacts | Lifecycle |
| --- | --- | --- |
| This skill's current invocation | Copied direct/planned/local/user-plan/follow-up packets and CLI logs explicitly placed below the invocation's private session root | Keep through authorization, review, resume, and follow-up; delete after the final cleanup gate |
| `cursor-delegate` | Read-only workspace copy, packaged frontend child, listener, tickets, sessions, and IPC state | The CLI closes/removes these; the skill verifies the outcome and never races the CLI |
| Caller or user | A pre-existing plan/task file, an explicitly retained audit directory, repository changes, branches/worktrees, or a copy kept with `--keep-workspace-copy` | Never delete automatically |

The CLI accepts an arbitrary `--task-file`, so it cannot infer whether that file is disposable. Its direct-use default `<workspace>/.agent/delegations` is durable audit storage. This skill must make ownership explicit instead of asking the CLI to delete caller inputs.

## Create One Private Session

Before copying the first task template, run the bundled standard-library helper from this skill's actual installation directory:

```bash
python3 <skill-root>/scripts/delegation_session.py start \
  --workspace /absolute/path/to/repo
```

Record the returned `sessionFile`, `sessionRoot`, `packetsDir`, `logsDir`, and `leasesDir` in the upstream continuation or hierarchical ledger. The helper creates an OS-temporary `0700` root with a mode-`0600` ownership marker. Do not discover or reuse sessions by scanning the temporary directory.

- Materialize and fill only the fenced packet body from each task-template reference below `packetsDir`; use ordinary `.md` files only and never copy the reference's explanatory wrapper.
- Copy a user-provided plan before adapting it. The original is caller-owned and must remain untouched.
- Give every CLI invocation a unique, single-level `--log-name` such as `root-01` or `<workstream-id>-01`, then dispatch it only through the helper's `run` command. Do not pass `--log-dir` inside the trailing `cursor-delegate` command; the helper supplies the effective log base and foreground lease.
- Keep all retries, authorization reruns, resumes, and bounded follow-ups for the same delegation inside this one session root.
- In hierarchical mode, root owns the marker and cleanup for the entire session lifetime. A non-root workstream records its packet/status paths and process disposition but must not clean the session. At an authorization barrier, it hands those facts to root before interruption; cleanup ownership never transfers because it never leaves root.

## Run Every Dispatch Through The Lease Wrapper

For ordinary ephemeral skill-managed logs:

```bash
python3 <skill-root>/scripts/delegation_session.py run \
  --session-file /exact/path/from-start/.cursor-delegate-skill-session.json \
  --log-name root-01 \
  -- cursor-delegate \
  --workspace /absolute/path/to/repo \
  --task-file /exact/session/packets/task.md \
  --inspect-only
```

The wrapper maps `root-01` to a log base below the marker-owned `logsDir`, records a lease below `leasesDir`, forwards `SIGINT`, `SIGTERM`, and `SIGHUP` where available to `cursor-delegate`, waits for and reaps the child, and releases the lease only after the child is reconciled. Cleanup must refuse while any lease is live or unresolved.

If the user explicitly asks to retain full CLI audit evidence, pass an absolute caller-owned log base with `--retained-log-dir` before the delimiter:

```bash
python3 <skill-root>/scripts/delegation_session.py run \
  --session-file /exact/path/from-start/.cursor-delegate-skill-session.json \
  --log-name retained-root-01 \
  --retained-log-dir /absolute/caller-owned/cursor-audit/root-01 \
  -- cursor-delegate \
  --workspace /absolute/path/to/repo \
  --task-file /exact/session/packets/task.md \
  --apply
```

Keep `--log-name` unique even when retaining logs; it identifies the session lease and dispatch correlation. The retained path must be absolute, outside the session root, caller-owned, and not already exist; the wrapper creates it, and session cleanup never deletes it. Do not pass raw `--log-dir` to the trailing CLI or place a retained path below the private session. Task packets may still remain ephemeral.

## Cleanup Gate

Cleanup is allowed only after all of these are true:

1. Every owning CLI foreground process has exited, including exceptional dashboard retention.
2. The packaged frontend child/listener has closed; no recorded frontend PID remains live.
3. Upstream captured bounded evidence needed after deletion: task hash, dispatch/agent/run/request identifiers, runtime/mode, model verification, terminal and Stop outcomes, diff summary, verification, and review verdict.
4. Upstream review is `accepted` or `accepted with notes`, with no pending retry, resume, authorization handoff, follow-up, or unreviewed workstream.
5. Hierarchical integration review is complete and every required ledger node has a terminal cleanup disposition.

`starting`, `running`, `needs_input`, `needs_authorization`, a pending follow-up, a live retention window, or an unreconciled `interrupted`/partial Stop outcome is not a cleanup state. Retain the session and report why. A user-authorized abandonment may clean only after active or ambiguous remote execution has been reconciled.

Before deletion, place the bounded evidence in the final response or caller-owned ledger. Do not preserve capability URLs, full prompts, raw event bodies, or secrets merely to replace the temporary logs.

## Safe Cleanup

For an accepted session:

```bash
python3 <skill-root>/scripts/delegation_session.py cleanup \
  --session-file /exact/path/from-start/.cursor-delegate-skill-session.json \
  --verdict accepted
```

Use `accepted-with-notes` when that is the upstream verdict. For an explicitly abandoned session, pass `--verdict abandoned --override-reason <bounded-reason>` only after remote/process reconciliation.

An old `needs_input`, `needs_authorization`, or `interrupted` status can remain in the same session after a later reconciled run. Name each such exact in-session status with `--allow-status` and record the reconciliation in `--override-reason`. The helper never permits this override for `starting` or `running`.

### Exact Fault-Residue Reconciliation

Abrupt process failure can leave a small amount of allowlisted runtime residue. Cleanup remains fail-closed unless upstream first proves the owning process/remote run is terminal and names every exact path. Each of these repeatable flags requires a non-empty `--override-reason`:

- `--allow-incomplete-run /exact/in-session/run-directory`: only a specific run directory left before `status.json` was created.
- `--allow-lease /exact/in-session/leases/<log-name>.json`: only a specific stale lease whose recorded wrapper and child PIDs are both no longer alive.
- `--allow-temp-artifact /exact/in-session/run/<name>`: only a specific atomic JSON residue named `<base>.<pid>.<uuid>.tmp`, where `<base>` is exactly `status.json`, `metadata.json`, or `snapshot.v2.json`, `<pid>` is a positive decimal PID, and `<uuid>` is the lowercase canonical UUID form.

These flags reconcile evidence; they do not weaken ownership checks. A live wrapper/child/frontend PID, live lease, `starting`/`running` status, symlink, path outside the session, malformed name, changed identity, or unknown artifact can never be overridden. Do not glob, pass a directory in place of an exact residue file, or authorize residue merely because a process is difficult to inspect.

A stale lease in phase `starting-child`, or one without a recorded `childPid`, can come from the narrow crash window after process creation but before the wrapper persisted the child PID. The absent PID is not proof that no child started. Before allowing that lease, independently account for local `cursor-delegate` processes and any possible remote run; if either remains ambiguous, retain the session.

After validation and before unlinking, cleanup writes an identity-pinned manifest into the existing ownership marker. Most partial failures leave that marker and manifest in place; if final root removal fails after marker deletion, the helper attempts to restore the same manifest-bearing marker. Fix only the reported obstruction and retry with the same exact marker and verdict. Every manifest retry checks the surviving root against the recorded identities and rejects new or identity-changed entries. This recovery exists only while the marker still proves ownership; after successful cleanup removes it, another call is refused.

The helper:

- requires the exact live marker returned by `start`; after successful cleanup removes that marker, any repeated call is refused because ownership can no longer be re-proven;
- verifies the canonical root is the marker-recorded immediate child of the OS temporary directory and is outside the workspace and skill directory;
- rejects symlinks, protected roots, unknown top-level entries, unknown packet types, unknown run files, unapproved malformed/incomplete run residue, active frontend/wrapper/child PIDs, live leases, and active or unreconciled statuses;
- deletes only ordinary `.md` packet files and the documented CLI run artifacts below per-dispatch log bases;
- treats `latest` only as an owned file to unlink and never follows its contents as a deletion target;
- removes allowlisted files first, removes only empty directories, and verifies the exact session root no longer exists.

Never replace the helper with a broad recursive delete, a glob, a path discovered through `latest`, or an unresolved environment variable. Never point it at the workspace, skill directory, home directory, a shared log directory, a branch/worktree, or a user file.

## Cleanup Result

Record one terminal disposition:

- `cleaned`: the owned root is gone; include entry count/bytes from the helper without repeating sensitive paths.
- `retained`: continuation, follow-up, authorization, or ambiguous remote execution still needs the private session.
- `cleanup_blocked`: ownership/path/content/process validation failed; preserve the residue and report the exact reason instead of widening deletion scope.

A repeated cleanup attempt after `cleaned` is a refusal/`cleanup_blocked` outcome, not success: without the live marker, the helper cannot prove the former target's ownership.

Report caller-retained audit logs separately. Their existence never blocks deletion of an otherwise terminal private session, and session cleanup never deletes them.
