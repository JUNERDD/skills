# JUNERDD Skills

<p align="center">
  <img src="./docs/images/readme-hero.png" alt="JUNERDD Skills hero" width="960">
</p>

Reusable AI agent skills published from a single repository.

Current collection version: [`0.2.3`](./VERSION). Release notes are tracked in [`CHANGELOG.md`](./CHANGELOG.md) and published through GitHub Releases.

This repository is a skill collection, not a single-skill package. Installable skills live under [`skills/`](./skills/), and each subfolder is meant to be independently installable and expanded over time. The root [`VERSION`](./VERSION) file tracks the published version of the collection as a whole using SemVer; Git tags and GitHub Releases use the `vX.Y.Z` form. Individual tools or subpackages may keep their own runtime versions when needed.

Stable production URL: [https://junerdd-skills.vercel.app](https://junerdd-skills.vercel.app)

## Website (Vercel)

The companion landing page is a Next.js app in [`web/`](./web/).
English is served from unprefixed paths such as `/` and `/skills/<slug>`;
Chinese is served from `/zh-CN` and `/zh-CN/skills/<slug>`.

1. In the [Vercel dashboard](https://vercel.com/new), import this GitHub repository.
2. Under **Configure Project**, set **Root Directory** to **`web`** (critical for this monorepo layout).
3. Add **Environment Variable** on **Production**: **`NEXT_PUBLIC_SITE_URL`** = your production domain (example: `https://skills.example.com`, no trailing slash). This should match the **primary Production domain** configured under **Project → Settings → Domains** so Open Graph, canonical URLs, `sitemap.xml`, and `robots.txt` stay consistent.
4. After the first successful Production deployment, open your GitHub repo **Settings → General** and set **Website** to that same production URL so the repository “About” box links to the live site.

## 🧭 Skills At A Glance

If you are deciding what to install, start here:

- [`comment-strategist`](#comment-strategist) - add high-value code comments without comment noise
- [`exhaustive-code-slimmer`](#exhaustive-code-slimmer) - exhaustively reduce maintained code while preserving behavior
- [`reduce-reinvention`](#reduce-reinvention) - find duplicated effort and guide reuse-first consolidation
- [`find-local-skill`](#find-local-skill) - decompose requests, then find relevant local skills
- [`git-commit`](#git-commit) - draft a Conventional Commit message from the staged diff
- [`mr`](#mr) - use and maintain the Git MR/PR helper CLI
- [`split-commits`](#split-commits) - split a mixed working tree into focused local commits
- [`multitask-coordinator`](#multitask-coordinator) - coordinate scoped subagent work with isolation and ownership boundaries
- [`plan-mode`](#plan-mode) - plan complex or risky work before editing
- [`debug`](#debug) - debug runtime issues with an evidence-first logging workflow
- [`hack-review`](#hack-review) - review whether an implementation relies on brittle hack-like shortcuts
- [`receiving-hack-review`](#receiving-hack-review) - consume a hack-review report and verify each finding before changing code
- [`regression-review`](#regression-review) - review code changes for user-visible behavioral regressions
- [`receiving-regression-review`](#receiving-regression-review) - consume a regression-review report and verify each finding before changing code

## 📦 Install

If you want an agent to install this repository for you without copying files, tell it:

```text
Fetch and follow instructions from https://raw.githubusercontent.com/JUNERDD/skills/refs/heads/main/docs/INSTALL.md
```

If the agent already has this repository open locally, it can read [`./docs/INSTALL.md`](./docs/INSTALL.md) directly instead of fetching the raw GitHub URL.

The CLI examples below intentionally use the latest `skills` tool version to avoid mismatches with older local installs.

List the skills currently published from this repository:

```bash
npx skills@latest add JUNERDD/skills --list
```

Install a specific skill:

```bash
npx skills@latest add JUNERDD/skills --skill <skill-name>
```

Install globally for Codex:

```bash
npx skills@latest add JUNERDD/skills --skill <skill-name> -g -a codex -y
```

Examples:

```bash
npx skills@latest add JUNERDD/skills --skill debug
npx skills@latest add JUNERDD/skills --skill git-commit
npx skills@latest add JUNERDD/skills --skill mr
npx skills@latest add JUNERDD/skills --skill split-commits
npx skills@latest add JUNERDD/skills --skill multitask-coordinator
npx skills@latest add JUNERDD/skills --skill plan-mode
npx skills@latest add JUNERDD/skills --skill comment-strategist
npx skills@latest add JUNERDD/skills --skill exhaustive-code-slimmer
npx skills@latest add JUNERDD/skills --skill reduce-reinvention
npx skills@latest add JUNERDD/skills --skill find-local-skill
npx skills@latest add JUNERDD/skills --skill hack-review
npx skills@latest add JUNERDD/skills --skill receiving-hack-review
npx skills@latest add JUNERDD/skills --skill regression-review
npx skills@latest add JUNERDD/skills --skill receiving-regression-review
```

Manual symlink install still works if you prefer not to use the agent prompt:

```bash
mkdir -p ~/.agents/skills
ln -s "$PWD/skills" ~/.agents/skills/junerdd-skill
```

## 🧱 Repository Model

- The collection version lives in the root [`VERSION`](./VERSION) file.
- Release notes live in [`CHANGELOG.md`](./CHANGELOG.md), and published GitHub releases should use matching `vX.Y.Z` tags.
- Use the release workflow to prepare a collection release. It opens a release PR that updates `VERSION`, the README version line, website version metadata, and `CHANGELOG.md` from one workflow input; merging that PR publishes the matching GitHub Release.
- Each installable skill lives under `skills/<skill-name>/`.
- Each skill owns its own `SKILL.md` plus any optional `agents/`, `references/`, `scripts/`, or `assets/` directories.
- Root-level files describe the repository as a collection. Skill-specific behavior and deep operational details stay inside the relevant skill folder.
- Shared repository assets such as screenshots can live outside `skills/` when they are not part of the installable package itself.

## 🗂️ Current Skills

Use the anchor list above for a quick jump, then read the section that matches your task.

### `comment-strategist`

[`skills/comment-strategist/`](./skills/comment-strategist/) is for documenting existing code without adding low-value comment noise. It focuses on intent, contracts, constraints, field meaning, and control-flow rationale instead of rewriting syntax in prose.

Install:

```bash
npx skills@latest add JUNERDD/skills --skill comment-strategist
```

Best for:

- documenting exported functions, interfaces, classes, and config objects
- replacing outdated or redundant comments with durable explanations
- adding guided comments inside complex logic while preserving the local comment style

Key entry points:

- Workflow and guardrails: [`skills/comment-strategist/SKILL.md`](./skills/comment-strategist/SKILL.md)
- Optional runtime metadata: [`skills/comment-strategist/agents/openai.yaml`](./skills/comment-strategist/agents/openai.yaml)

### `exhaustive-code-slimmer`

[`skills/exhaustive-code-slimmer/`](./skills/exhaustive-code-slimmer/) exhaustively searches for behavior-preserving code reductions. It combines audit scripts, deletion-first candidate search, oracle design, and an approval gate for architecture-level refactors so slimming improves maintainability instead of producing dense or risky code.

Install:

```bash
npx skills@latest add JUNERDD/skills --skill exhaustive-code-slimmer
```

Best for:

- finding removable files, branches, exports, dependencies, wrappers, and duplicate logic
- running deletion candidates against a build/test/lint/smoke oracle before accepting changes
- identifying architecture problems that block safe code reduction and presenting DX-oriented options before refactoring

Key entry points:

- Workflow and guardrails: [`skills/exhaustive-code-slimmer/SKILL.md`](./skills/exhaustive-code-slimmer/SKILL.md)
- Code-slim audit script: [`skills/exhaustive-code-slimmer/scripts/code_slim_audit.py`](./skills/exhaustive-code-slimmer/scripts/code_slim_audit.py)
- Exhaustive shrink script: [`skills/exhaustive-code-slimmer/scripts/exhaustive_shrink.py`](./skills/exhaustive-code-slimmer/scripts/exhaustive_shrink.py)
- Optional runtime metadata: [`skills/exhaustive-code-slimmer/agents/openai.yaml`](./skills/exhaustive-code-slimmer/agents/openai.yaml)

### `reduce-reinvention`

[`skills/reduce-reinvention/`](./skills/reduce-reinvention/) identifies and reduces duplicated effort across code, libraries, services, templates, docs, platform workflows, and architecture decisions. It combines a reuse-first workflow with audit scripts and decision templates so teams can adopt, adapt, consolidate, or justify divergence with evidence.

Install:

```bash
npx skills@latest add JUNERDD/skills --skill reduce-reinvention
```

Best for:

- auditing duplicated implementations and overlapping reusable assets
- deciding build-vs-reuse/buy with ownership, maintenance, security, and migration tradeoffs
- creating reuse catalogs, ADR/RFC records, migration plans, or golden-path guidance

Key entry points:

- Workflow and guardrails: [`skills/reduce-reinvention/SKILL.md`](./skills/reduce-reinvention/SKILL.md)
- Reuse playbook: [`skills/reduce-reinvention/references/reuse-playbook.md`](./skills/reduce-reinvention/references/reuse-playbook.md)
- Audit checklist: [`skills/reduce-reinvention/references/audit-checklist.md`](./skills/reduce-reinvention/references/audit-checklist.md)
- Decision matrix: [`skills/reduce-reinvention/references/decision-matrix.md`](./skills/reduce-reinvention/references/decision-matrix.md)
- Output templates: [`skills/reduce-reinvention/references/templates.md`](./skills/reduce-reinvention/references/templates.md)
- Reinvention audit script: [`skills/reduce-reinvention/scripts/reinvention_audit.py`](./skills/reduce-reinvention/scripts/reinvention_audit.py)
- Reuse catalog script: [`skills/reduce-reinvention/scripts/reuse_catalog.py`](./skills/reduce-reinvention/scripts/reuse_catalog.py)
- Optional runtime metadata: [`skills/reduce-reinvention/agents/openai.yaml`](./skills/reduce-reinvention/agents/openai.yaml)

### `find-local-skill`

[`skills/find-local-skill/`](./skills/find-local-skill/) helps agents decompose a request into deliverables, workflow phases, tools, domains, and implicit prerequisites before inspecting available local skills, selecting the ones that match, and applying those workflows before normal analysis. It includes a local scanner for plain project `skills/` folders, Cursor, Claude Code, OpenCode, Codex, shared Agent Skills roots, and plugin skill caches.

Install:

```bash
npx skills@latest add JUNERDD/skills --skill find-local-skill
```

Best for:

- finding relevant local skills before planning or implementation
- routing ambiguous or multi-phase requests through explicit skill selection
- surfacing implicit prerequisite skills before deeper requirement analysis
- auditing available skill coverage across plain project `skills/`, Cursor, Claude Code, OpenCode, Codex, and shared Agent Skills roots
- distinguishing plugin skills with names such as `product-design:index`

Key entry points:

- Workflow and guardrails: [`skills/find-local-skill/SKILL.md`](./skills/find-local-skill/SKILL.md)
- Local skill scanner: [`skills/find-local-skill/scripts/list_agent_skills.py`](./skills/find-local-skill/scripts/list_agent_skills.py)
- Optional runtime metadata: [`skills/find-local-skill/agents/openai.yaml`](./skills/find-local-skill/agents/openai.yaml)

### `git-commit`

[`skills/git-commit/`](./skills/git-commit/) drafts a Conventional Commit message from the staged diff only. It is intentionally narrow: it reads what is already staged, proposes one accurate message, and does not mutate Git state.

Install:

```bash
npx skills@latest add JUNERDD/skills --skill git-commit
```

Best for:

- generating a clean commit subject from the current index
- checking whether a staged batch is too mixed for one honest commit message
- keeping commit wording grounded in staged files instead of unstaged work

Key entry points:

- Workflow and guardrails: [`skills/git-commit/SKILL.md`](./skills/git-commit/SKILL.md)
- Optional runtime metadata: [`skills/git-commit/agents/openai.yaml`](./skills/git-commit/agents/openai.yaml)

### `mr`

[`skills/mr/`](./skills/mr/) supports the `mr` Node CLI for generic Git MR/PR workflows. It covers target aliases, MR branch strategies, default detached mode, request providers or custom request commands, configuration, conflict resume, install/update/uninstall behavior, automatic update notices, and maintenance of the TypeScript CLI implementation behind the tool.

Install:

```bash
npx skills@latest add JUNERDD/skills --skill mr
```

Best for:

- creating or previewing Git merge requests or pull requests with `mr`, `mrm`, `mrt`, or `mrp`
- checking for a missing local `mr` install and installing it after user confirmation
- choosing between `merge`, `rebase`, `merge-target`, `pr`, and default detached-mode flows
- configuring CNB/GitHub/GitLab providers or a custom `mr.requestCommand`
- understanding non-blocking update notices and the environment variables that disable them
- handling stopped merge/rebase states by preserving CLI-owned resume paths
- maintaining the TypeScript/Pastel/Ink/Zod implementation behind the CLI

Key entry points:

- Workflow and guardrails: [`skills/mr/SKILL.md`](./skills/mr/SKILL.md)
- CLI reference: [`skills/mr/references/mr-cli-reference.md`](./skills/mr/references/mr-cli-reference.md)
- Optional runtime metadata: [`skills/mr/agents/openai.yaml`](./skills/mr/agents/openai.yaml)

### `split-commits`

[`skills/split-commits/`](./skills/split-commits/) helps break a mixed working tree into a sequence of focused local commits. It stages one logical batch at a time, asks `$git-commit` for a message, and requires explicit confirmation before each `git commit`.

Install:

```bash
npx skills@latest add JUNERDD/skills --skill split-commits
```

Best for:

- separating unrelated concerns in the same working tree
- isolating refactors from behavior changes
- building a short series of reviewable local commits without pushing

Key entry points:

- Workflow and guardrails: [`skills/split-commits/SKILL.md`](./skills/split-commits/SKILL.md)
- Optional runtime metadata: [`skills/split-commits/agents/openai.yaml`](./skills/split-commits/agents/openai.yaml)

### `multitask-coordinator`

[`skills/multitask-coordinator/`](./skills/multitask-coordinator/) coordinates non-trivial multi-step work where an agent may use background subagents or local task decomposition. It keeps the parent agent responsible for framing, decomposition, shared contracts, delegation decisions, worker ownership boundaries, isolation choices, synthesis, verification, and user communication.

Install:

```bash
npx skills@latest add JUNERDD/skills --skill multitask-coordinator
```

Best for:

- deciding whether complex repo work should stay local, be decomposed, or be delegated
- assigning disjoint worker scopes in large repositories, monorepos, multi-root workspaces, dirty worktrees, or isolated worktrees and branches
- keeping shared contracts, package exports, sequencing, and destructive migration boundaries under parent-agent ownership
- coordinating queued independent requests, async exploration, implementation, review, or verification without duplicating work
- preserving parent-agent ownership of final integration, validation, and user-facing status

Key entry points:

- Workflow and guardrails: [`skills/multitask-coordinator/SKILL.md`](./skills/multitask-coordinator/SKILL.md)
- Optional runtime metadata: [`skills/multitask-coordinator/agents/openai.yaml`](./skills/multitask-coordinator/agents/openai.yaml)

### `plan-mode`

[`skills/plan-mode/`](./skills/plan-mode/) mirrors Cursor's Plan Mode loop for complex, ambiguous, risky, or multi-file work: create a disk-backed editable Markdown plan, research the codebase into file/code references, ask focused clarification questions, maintain buildable todos, pressure-test non-trivial plans with `$grill-me`, and build only after the plan is approved.

Install:

```bash
npx skills@latest add JUNERDD/skills --skill plan-mode
```

Best for:

- planning implementation for broad or multi-file tasks before editing
- tracing routes, data flow, architecture constraints, tradeoffs, or risky operations
- maintaining an editable plan document with file references and checkbox todos
- invoking `$grill-me` to pressure-test meaningful assumptions, risks, and rollout edges
- building all or selected todos only after the user approves the plan

Key entry points:

- Workflow and guardrails: [`skills/plan-mode/SKILL.md`](./skills/plan-mode/SKILL.md)
- Plan artifact helper: [`skills/plan-mode/scripts/plan_artifact.py`](./skills/plan-mode/scripts/plan_artifact.py)
- Architecture reference: [`skills/plan-mode/references/architecture.md`](./skills/plan-mode/references/architecture.md)
- Optional runtime metadata: [`skills/plan-mode/agents/openai.yaml`](./skills/plan-mode/agents/openai.yaml)

### `debug`

[`skills/debug/`](./skills/debug/) provides evidence-first runtime debugging for application bugs, regressions, flaky behavior, and unclear runtime failures. It is the most operational skill in the repository and includes both workflow guidance and a local log collector.

Install:

```bash
npx skills@latest add JUNERDD/skills --skill debug
```

Key entry points:

- Workflow and guardrails: [`skills/debug/SKILL.md`](./skills/debug/SKILL.md)
- Operator reference: [`skills/debug/references/runtime-debugging.md`](./skills/debug/references/runtime-debugging.md)
- Local NDJSON collector: [`skills/debug/scripts/local_log_collector/`](./skills/debug/scripts/local_log_collector/)
- Optional runtime metadata: [`skills/debug/agents/openai.yaml`](./skills/debug/agents/openai.yaml)

### `debug` Skill Snapshot

The `debug` skill is designed to prevent speculative fixes by forcing a prove-it loop:

1. Generate precise hypotheses.
2. Attach to or start an authoritative logging session.
3. Add minimal temporary instrumentation.
4. Reproduce the issue and read the recorded log file.
5. Mark each hypothesis as `CONFIRMED`, `REJECTED`, or `INCONCLUSIVE`.
6. Apply a fix only after the root cause is proven.
7. Verify with fresh post-fix logs before removing instrumentation.

This keeps the skill focused on evidence, not guesswork.

### `debug` Architecture

```mermaid
flowchart LR
  User["Developer / Operator"] --> Agent["Agent Runtime"]
  Agent --> Skill["debug/SKILL.md<br/>workflow + guardrails"]
  Agent --> Ref["runtime-debugging.md<br/>bootstrap + log format"]
  Agent --> App["Target app under debug"]
  Agent --> Logs["Temporary instrumentation"]
  Logs --> Collector["Local NDJSON collector<br/>same-origin dashboard + APIs"]
  App --> Logs
  Collector --> File["Session log file"]
  Collector --> UI["Live dashboard"]
  File --> Agent
  UI --> Agent
  Agent --> Fix["Proven fix + post-fix verification"]
```

### `debug` Highlights

- Evidence-first debugging instead of inspection-only reasoning
- Minimal instrumentation with explicit cleanup after verification
- Per-hypothesis logging and before/after comparison
- Local collector bootstrap when the host does not already provide logging
- Browser-first log transport for frontend debugging, with explicit prohibition on app-local proxy routes unless direct delivery is proven blocked

### `debug` Runtime Support

The current `debug` skill is intentionally portable. It works with:

- OpenAI Codex and similar local-skill runtimes
- Agent shells that read `~/.agents/skills/<name>/SKILL.md`
- Custom agent frameworks that mount a skill folder and inject `SKILL.md` into context
- Internal toolchains that want the collector, references, or workflow as reusable assets

If your runtime ignores [`skills/debug/agents/openai.yaml`](./skills/debug/agents/openai.yaml), the core logic is still fully available through [`skills/debug/SKILL.md`](./skills/debug/SKILL.md).

### `debug` Dashboard Preview

![Runtime Debug dashboard preview](./docs/images/dashboard-overview.png)

### `debug` Collector

The bundled collector is a zero-dependency Python app built on the standard library. It accepts JSON log events, appends them to an NDJSON file, and serves a same-origin dashboard for live inspection.

For frontend and browser debugging, the intended transport is direct client-to-collector HTTP posting. The collector already handles CORS and preflight, so the skill should not create temporary Next.js API routes or other app-local proxy layers unless direct browser delivery has been proven blocked in the current host.

Collector endpoints:

- `POST /ingest`
- `GET /health`
- `GET /api/state`
- `GET /api/logs`
- `GET /api/logs/detail`
- `POST /api/clear`
- `POST /api/shutdown`

Minimal smoke test:

```bash
mkdir -p .debug-logs
python3 skills/debug/scripts/local_log_collector/main.py \
  --log-file "$PWD/.debug-logs/demo.ndjson" \
  --ready-file "$PWD/.debug-logs/demo.json" \
  --session-id "demo-session"
```

### `hack-review`

[`skills/hack-review/`](./skills/hack-review/) reviews whether an implementation is relying on hack-like tactics instead of sound ownership and abstraction boundaries. It produces a coverage-led reviewer report that enumerates all distinct hack-risk findings discovered within scope, records intentional exceptions, and marks uncovered ownership boundaries explicitly.

Install:

```bash
npx skills@latest add JUNERDD/skills --skill hack-review
```

Best for:

- identifying impossible-state fallbacks that hide a broken invariant
- flagging symptom-masking patches that do not fix the root cause
- catching duplicate abstractions or parallel wheels when a stable boundary already exists
- showing which touched ownership boundaries were reviewed, skipped, or left uncovered

Key entry points:

- Workflow and guardrails: [`skills/hack-review/SKILL.md`](./skills/hack-review/SKILL.md)
- Report template: [`skills/hack-review/references/report-template.md`](./skills/hack-review/references/report-template.md)
- Optional runtime metadata: [`skills/hack-review/agents/openai.yaml`](./skills/hack-review/agents/openai.yaml)

### `receiving-hack-review`

[`skills/receiving-hack-review/`](./skills/receiving-hack-review/) consumes a `hack-review` report and builds a disposition ledger for every finding, intentional exception, and open ownership coverage gap before deciding whether to fix, challenge, confirm, or carry it forward.

Install:

```bash
npx skills@latest add JUNERDD/skills --skill receiving-hack-review
```

Best for:

- re-checking that a hack report matches the exact requested review scope
- fixing ownership problems without mechanically deleting necessary guards
- narrowing or disproving hack findings with stronger code-path evidence
- closing or explicitly carrying forward `Not covered` ownership boundaries from the coverage ledger

Key entry points:

- Workflow and guardrails: [`skills/receiving-hack-review/SKILL.md`](./skills/receiving-hack-review/SKILL.md)
- Optional runtime metadata: [`skills/receiving-hack-review/agents/openai.yaml`](./skills/receiving-hack-review/agents/openai.yaml)

### `regression-review`

[`skills/regression-review/`](./skills/regression-review/) reviews whether the current change set introduces user-visible behavioral regressions. It writes a coverage-led reviewer report that enumerates all distinct findings discovered within scope, records intentional visible changes, builds scoped behavior-graph deltas for affected surfaces when useful, and marks uncovered surfaces explicitly.

Install:

```bash
npx skills@latest add JUNERDD/skills --skill regression-review
```

Best for:

- checking whether a refactor or feature work breaks user-facing flows
- auditing changed defaults, loading states, retries, ordering, or exported output
- tracing changed inputs, guards, transforms, and outputs through scoped behavior graphs
- writing a review artifact that keeps severity aligned with the strongest unresolved finding while showing full reviewed coverage

Key entry points:

- Workflow and guardrails: [`skills/regression-review/SKILL.md`](./skills/regression-review/SKILL.md)
- Report template: [`skills/regression-review/references/report-template.md`](./skills/regression-review/references/report-template.md)
- Optional runtime metadata: [`skills/regression-review/agents/openai.yaml`](./skills/regression-review/agents/openai.yaml)

### `receiving-regression-review`

[`skills/receiving-regression-review/`](./skills/receiving-regression-review/) consumes a `regression-review` report and builds a disposition ledger for every finding, behavior-graph delta, intentional visible change, and open coverage gap before deciding whether to fix, challenge, confirm, or carry it forward.

Install:

```bash
npx skills@latest add JUNERDD/skills --skill receiving-regression-review
```

Best for:

- re-checking a regression gate against the current diff and baseline
- reconciling behavior-graph deltas with findings and coverage rows
- fixing only proven user-visible regressions instead of blindly following review comments
- separating real regressions from intentional product deltas with stronger evidence
- closing or explicitly carrying forward `Not covered` user-visible surfaces from the coverage ledger

Key entry points:

- Workflow and guardrails: [`skills/receiving-regression-review/SKILL.md`](./skills/receiving-regression-review/SKILL.md)
- Optional runtime metadata: [`skills/receiving-regression-review/agents/openai.yaml`](./skills/receiving-regression-review/agents/openai.yaml)

## 🌱 Growing The Repository

When you add more skills later:

- Create a new folder under `skills/<skill-name>/`.
- Keep each skill self-contained so it can be installed independently.
- Add or update `agents/`, `references/`, `scripts/`, and `assets/` only when they materially help that specific skill.
- Update the `Current Skills` section in this README with a one-line summary and relevant links.
- Keep repo-level README content about the collection itself; move deep procedural detail into the skill that owns it.

## 🏗️ Repository Layout

```text
.
├── LICENSE
├── README.md
├── docs/
│   └── images/
│       └── dashboard-overview.png
└── skills/
    ├── comment-strategist/
    │   ├── SKILL.md
    │   └── agents/
    │       └── openai.yaml
    ├── debug/
    │   ├── SKILL.md
    │   ├── agents/
    │   │   └── openai.yaml
    │   ├── references/
    │   │   └── runtime-debugging.md
    │   └── scripts/
    │       └── local_log_collector/
    │           ├── main.py
    │           ├── collector_server.py
    │           ├── collector_state.py
    │           ├── collector_browser.py
    │           └── static/
    ├── exhaustive-code-slimmer/
    │   ├── SKILL.md
    │   ├── agents/
    │   │   └── openai.yaml
    │   ├── references/
    │   │   ├── code_cleanliness_guide.md
    │   │   ├── dx_architecture_gate.md
    │   │   ├── language_tactics.md
    │   │   ├── oracle_design.md
    │   │   ├── research_basis.md
    │   │   └── transformation_catalog.md
    │   └── scripts/
    │       ├── architecture_dx_scan.py
    │       ├── code_slim_audit.py
    │       └── exhaustive_shrink.py
    ├── find-local-skill/
    │   ├── SKILL.md
    │   ├── agents/
    │   │   └── openai.yaml
    │   └── scripts/
    │       └── list_agent_skills.py
    ├── git-commit/
    │   ├── SKILL.md
    │   └── agents/
    │       └── openai.yaml
    ├── hack-review/
    │   ├── SKILL.md
    │   ├── agents/
    │   │   └── openai.yaml
    │   └── references/
    │       └── report-template.md
    ├── mr/
    │   ├── SKILL.md
    │   ├── agents/
    │   │   └── openai.yaml
    │   └── references/
    │       └── mr-cli-reference.md
    ├── multitask-coordinator/
    │   ├── SKILL.md
    │   └── agents/
    │       └── openai.yaml
    ├── receiving-hack-review/
    │   ├── SKILL.md
    │   └── agents/
    │       └── openai.yaml
    ├── receiving-regression-review/
    │   ├── SKILL.md
    │   └── agents/
    │       └── openai.yaml
    ├── regression-review/
    │   ├── SKILL.md
    │   ├── agents/
    │   │   └── openai.yaml
    │   └── references/
    │       └── report-template.md
    └── split-commits/
        ├── SKILL.md
        └── agents/
            └── openai.yaml
```

## ⚖️ License

Released under the [MIT License](./LICENSE).
