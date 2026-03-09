# Runtime Debug Skill

Evidence-first runtime debugging skill for Codex-compatible agents.

This repository packages a reusable `debug` skill that forces the agent to prove a bug with runtime logs before changing behavior. It includes:

- A host-adaptive debugging workflow in [`SKILL.md`](./SKILL.md)
- A detailed operator reference in [`references/runtime-debugging.md`](./references/runtime-debugging.md)
- A bundled local NDJSON log collector with a same-origin dashboard under [`scripts/local_log_collector/`](./scripts/local_log_collector/)
- Agent metadata for OpenAI-compatible skill registries in [`agents/openai.yaml`](./agents/openai.yaml)

## Dashboard Preview

![Runtime Debug dashboard preview](./docs/images/dashboard-overview.png)

## Why This Exists

Most debugging prompts drift into speculative fixes. This skill pushes the agent toward a stricter loop:

1. Generate concrete hypotheses.
2. Start or attach to an authoritative logging session.
3. Add minimal temporary instrumentation.
4. Reproduce and inspect the recorded log file.
5. Apply a fix only after the root cause is proven.
6. Verify with post-fix logs before removing instrumentation.

The result is a debugging workflow that is easier to audit, easier to repeat, and less likely to ship guesswork.

## What The Skill Enforces

- Evidence-first debugging instead of code-inspection-only fixes
- Explicit `CONFIRMED` / `REJECTED` / `INCONCLUSIVE` hypothesis tracking
- Minimal temporary instrumentation with cleanup after verification
- A local collector service when the host does not already provide logging
- Clear reproduction requests and before/after verification runs
- Guardrails against speculative fallback code, stale logs, and leaked debug scaffolding

## Requirements

- A Codex-compatible local skill system that reads `SKILL.md`
- Python 3 available as `python3`, or `python` resolving to Python 3, when using the bundled collector
- A host runtime that can keep a long-lived process alive during the debugging session
- Optional browser access for the live dashboard; the collector APIs still work headlessly

## Repository Layout

```text
.
├── SKILL.md
├── README.md
├── LICENSE
├── agents/
│   └── openai.yaml
├── references/
│   └── runtime-debugging.md
└── scripts/
    └── local_log_collector/
        ├── main.py
        ├── collector_server.py
        ├── collector_state.py
        ├── collector_browser.py
        └── static/
```

## Installation

Install it as a local skill named `debug`.

### Codex-style skills

```bash
mkdir -p ~/.codex/skills/debug
rsync -a ./ ~/.codex/skills/debug/
```

### Agents-style skills

```bash
mkdir -p ~/.agents/skills/debug
rsync -a ./ ~/.agents/skills/debug/
```

If your runtime supports skill metadata discovery, keep [`agents/openai.yaml`](./agents/openai.yaml) together with the rest of the repository.

## Usage

Invoke the skill by asking the agent to use `$debug` for a bug, regression, flaky behavior, or unclear runtime failure.

Example:

```text
Use $debug to investigate why the checkout button sometimes stays disabled after the cart updates.
```

The skill will adapt to the current host, establish a logging session, request a reproduction run, and only propose a fix after the runtime evidence proves the root cause.

## Local Collector

The bundled collector is a zero-dependency Python app built on the standard library. It accepts JSON log events, appends them to an NDJSON file, and exposes:

- `POST /ingest`
- `GET /health`
- `GET /api/state`
- `GET /api/logs`
- `GET /api/logs/detail`
- `POST /api/clear`
- `POST /api/shutdown`

It also serves a same-origin dashboard for live log inspection.

Minimal smoke test:

```bash
mkdir -p .debug-logs
python3 scripts/local_log_collector/main.py \
  --log-file "$PWD/.debug-logs/demo.ndjson" \
  --ready-file "$PWD/.debug-logs/demo.json" \
  --session-id "demo-session"
```

The ready file contains the active endpoint, dashboard URL, log file path, and session metadata.

## Customization

- Edit [`SKILL.md`](./SKILL.md) to change workflow rules, guardrails, or required response shape.
- Edit [`references/runtime-debugging.md`](./references/runtime-debugging.md) to refine bootstrap commands and logging templates.
- Edit [`agents/openai.yaml`](./agents/openai.yaml) to tune discovery metadata for your host.

## License

This repository is released under the [MIT License](./LICENSE).
