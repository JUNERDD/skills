# Logged Grilling Reference

Use this reference when the grilling session needs exact command patterns or recovery steps.

## Table of contents

- Helper discovery
- Session setup
- Question logging
- Answer backfill
- Finalization
- Current transcript
- Recovery
- Repair mode

## Helper discovery

Resolve the workspace root first:

```bash
workspace_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
```

Resolve the helper path before running anything:

```bash
helper=""

for candidate in \
  "$workspace_root/skills/grill-me/scripts/grill_log.py" \
  "$HOME/.agents/skills/grill-me/scripts/grill_log.py" \
  "$HOME/.codex/skills/grill-me/scripts/grill_log.py"
do
  if [ -f "$candidate" ]; then
    helper="$candidate"
    break
  fi
done

[ -n "$helper" ] || { echo "grill_log.py not found" >&2; exit 1; }
```

## Session setup

Normal operation should not call `new` manually. The helper auto-creates or reuses the active session when you run `ask --workspace ...`.

If `CODEX_THREAD_ID` is unavailable, pass `--session-key "<stable-key>"` to every `ask`, `answer`, and `latest` command in the current grilling session.

## Question logging

Before sending a clarification question to the user, run:

```bash
python3 "$helper" ask \
  --workspace "$workspace_root" \
  --question "What is the single failure mode this design must prevent?" \
  --recommendation "Name the one failure that would make the design unacceptable."
```

This command returns the Markdown transcript path. Do not ask the question unless the command succeeds.

## Answer backfill

As soon as the user answers, run:

```bash
python3 "$helper" answer \
  --workspace "$workspace_root" \
  --answer "yes, that one" \
  --resolved-answer "Silent data loss is unacceptable, and the design must prioritize visible retry behavior and operator-friendly diagnostics."
```

Use `--answer` for the exact user reply. Use `--resolved-answer` for the standalone confirmed conclusion that should appear in the session `Answer` field and in the planning outcome. If the user accepts the recommendation with `yes`, `按推荐来`, or similar, `--resolved-answer` should be the recommendation itself, not the acknowledgement.

For a multi-line answer:

```bash
python3 "$helper" answer \
  --workspace "$workspace_root" \
  --resolved-answer "The core requirement is no silent data loss, visible retry behavior, and operator-friendly diagnostics." \
  --stdin <<'EOF'
The core requirement is:
- no silent data loss
- visible retry behavior
- operator-friendly diagnostics
EOF
```

Do not analyze the answer or ask a follow-up question until this command succeeds.

## Finalization

When the grilling pass is complete, run:

```bash
python3 "$helper" finalize --workspace "$workspace_root"
```

This command:

- writes a planning-ready outcome Markdown file next to the transcript
- updates the transcript header to `Status: finalized`
- records the outcome file path in the transcript header
- deletes the session's temporary `.active-*` pointer
- prints both `TRANSCRIPT=...` and `OUTCOME=...` so the assistant can report the final artifact locations directly

The outcome file is designed to help later AI passes write plans and design docs. It includes:

- normalized planning seeds grouped as goals, constraints, risks, decisions, scope boundaries, or uncategorized planning seeds
- a low-noise Q&A summary that keeps the resolved answer for each question
- raw user-answer context only when it differs from the resolved answer

The planning outcome must not require reopening the source transcript to interpret answers like `按推荐来`, `yes`, or `OK`. Those belong in `Raw user answer`; the session `Answer` and outcome `Resolved answer` must be standalone decisions.

`Uncategorized Planning Seeds` is a fallback planning bucket for confirmed answers that do not match a more specific planning category. It is not a second Q&A log; every confirmed answer still appears once in `Confirmed Q&A`.

The raw session transcript remains the full audit record for the assistant's original question-time recommendation and the exact turn-by-turn exchange. The planning-ready outcome should stay compact: keep only the context needed for a later planning pass to understand the confirmed decision without reopening the full transcript in common cases.

## Current transcript

To print the active transcript path for the current session:

```bash
python3 "$helper" current --workspace "$workspace_root"
```

## Recovery

To recover the active transcript path for the current session:

```bash
log_dir="$workspace_root/tmp/grill-me"
session_key="${CODEX_THREAD_ID:?CODEX_THREAD_ID is required for automatic recovery}"
log_file="$(python3 "$helper" latest --dir "$log_dir" --session-key "$session_key")"
```

Use `latest` when the current shell state is gone but the workspace-local active session still exists.

## Repair mode

Use these only when the normal workspace-mode flow cannot recover the session:

- `new --dir ... --workspace ... --session-key ...` to create a replacement transcript explicitly
- `latest --dir ... --session-key ...` to recover the most recent transcript for one stable session key
- `ask --file ...` or `answer --file ...` only when you already have the exact Markdown transcript path and need a direct repair
