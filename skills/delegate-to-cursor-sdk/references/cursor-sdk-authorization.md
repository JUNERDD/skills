# Cursor SDK Authorization

Use this reference whenever a Cursor SDK dispatch has no valid API key, receives an authentication error, or needs to prepare credentials for an automated run.

## Authorization Order

1. Prefer `CURSOR_API_KEY` in the local process environment.
2. For non-default environments, use `--api-key-env <ENV_NAME>` and keep the secret in that environment variable.
3. If the wrapper runs in an interactive terminal and no key is present, allow `--auth-mode auto` to request a hidden key. The wrapper passes it directly to `Agent.create({ apiKey })`, does not save it, and does not include it in argv, prompt files, metadata, or `status.json`.
4. If the key is missing or rejected in a non-interactive run, stop and ask the user to authorize the environment. Do not continue with Cursor SDK dispatch.

## User Authorization Request

When authorization is missing, ask for authorization without collecting the secret in chat:

```markdown
Cursor SDK needs authorization before I can delegate this task. Please create a Cursor user API key from Cursor Dashboard → API Keys, then run the command in the target shell after setting:

export CURSOR_API_KEY="<your Cursor API key>"

For team automation, use a Cursor service account API key from Team settings instead. Do not paste the key here; keep it in your local shell or secret manager. After the environment is authorized, rerun the Cursor SDK wrapper.
```

If the user is operating locally and wants a one-off run, use the wrapper's hidden prompt instead of asking for the key in conversation:

```bash
node scripts/cursor_delegate.mjs --workspace /path/to/repo --task-file /path/to/task.md --auth-mode auto
```

## Invalid Key Handling

If the SDK reports an invalid, expired, unauthorized, or disabled key:

1. Mark the run as blocked or `needs_authorization`.
2. Surface any `helpUrl` emitted by the SDK.
3. Ask the user to create or rotate a user API key, or use a service account key for team automation.
4. Confirm the selected key has permission for the runtime: local SDK run, cloud agent creation, connected repository access, and any requested team resources.
5. Retry only after the user authorizes the environment.

## Secret Handling Rules

- Never place a Cursor API key in a task packet, prompt, raw event log, issue comment, commit, PR body, shell history snippet, or chat transcript.
- Do not pass API keys through command-line argv; process listings and logs can expose argv. Use environment variables or the wrapper's hidden prompt.
- Do not write API keys into `.env` files unless the user explicitly requests that storage and understands the repository/secret-management implications.
- Keep raw SDK events disabled unless debugging requires them. Raw events may include prompts, file excerpts, or tool payloads.
- Redact `authorization`, `api_key`, `token`, `secret`, `cookie`, `password`, `credential`, and private-key-like fields in status summaries.

## Automation Pattern

For CI or non-interactive automation:

```bash
CURSOR_API_KEY="$CURSOR_API_KEY" node scripts/cursor_delegate.mjs \
  --workspace "$GITHUB_WORKSPACE" \
  --task-file .agent/cursor-task.md \
  --apply \
  --auth-mode fail
```

Use a secret manager or CI secret store to inject `CURSOR_API_KEY`. Prefer a service account key for team-owned automation and a user key for user-owned local runs.
