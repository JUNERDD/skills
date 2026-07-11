import type { SkillDetail } from "@/lib/content/types";

export type { SkillDetail, SkillEntryPoint } from "@/lib/content/types";
export {
  AGENT_INSTALL_INSTRUCTION,
  COLLECTION_VERSION,
  INSTALL_DOC_RAW,
  REPO_URL,
  getSkillInstallCommand,
  getSkillSourceUrl,
} from "@/lib/content/urls";

export const SKILLS: SkillDetail[] = [
  {
    slug: "comment-strategist",
    title: "comment-strategist",
    category: "Code documentation",
    blurb: "Add high-value code comments without comment noise.",
    lead:
      "A comment-editing workflow for making code easier to understand without translating syntax into prose.",
    overview:
      "Use this skill when a file needs durable comments around intent, constraints, data meaning, public contracts, or non-obvious control flow. It reads the local comment style first, removes weak or redundant comments where needed, and adds only the comments that help future readers reason about the code.",
    bestFor: [
      "Documenting exported functions, interfaces, classes, types, and configuration objects.",
      "Replacing stale or syntax-level comments with explanations that survive implementation churn.",
      "Clarifying fields, options, state variants, and branches whose meaning is part of the contract.",
    ],
    workflow: [
      "Read top-level definitions before editing so comments match the file's real ownership boundaries.",
      "Detect the nearby comment language, tone, density, and formatting conventions.",
      "Rank comment candidates by reader value, then choose the smallest useful granularity.",
      "Rewrite or remove low-value comments before adding new ones, preserving one documentation voice.",
      "Re-read the final file to make sure each comment still holds if small implementation details change.",
    ],
    outputs: [
      "A targeted patch to comments only, unless the user explicitly asks for broader code changes.",
      "Comments that explain why a branch exists, what a field means, or where misuse is likely.",
      "A concise completion note with any verification that was requested.",
    ],
    guardrails: [
      "Do not add narration that merely restates syntax.",
      "Do not stage, commit, or advance Git state unless the current request explicitly asks for it.",
      "Match the repository's existing comment style instead of imposing a new documentation system.",
    ],
    entryPoints: [
      {
        label: "Workflow",
        path: "skills/comment-strategist/SKILL.md",
        description: "Comment selection, granularity, and cleanup rules.",
      },
      {
        label: "Runtime metadata",
        path: "skills/comment-strategist/agents/openai.yaml",
        description: "Optional agent runtime metadata for this skill.",
      },
    ],
  },
  {
    slug: "exhaustive-code-slimmer",
    title: "exhaustive-code-slimmer",
    category: "Code cleanup",
    blurb: "Maximize safe code deletion with DX-aware architecture gates.",
    lead:
      "A deletion-first workflow for reducing maintained code while preserving externally observable behavior.",
    overview:
      "Use this skill when a codebase needs aggressive but disciplined simplification. It builds a behavior-preservation oracle, audits removable code, tests deletion and simplification candidates, and pauses for explicit approval before architecture-level refactors so code slimming improves developer experience instead of creating dense or risky code.",
    bestFor: [
      "Finding removable files, branches, exports, dependencies, wrappers, and duplicate logic.",
      "Running code-reduction candidates against build, typecheck, test, lint, smoke, or contract oracles.",
      "Diagnosing architecture problems that block safe deletion and proposing DX-oriented options before refactoring.",
    ],
    workflow: [
      "Record baseline files, LOC, bytes, dependencies, large files, duplicate blocks, and generated or vendor directories.",
      "Run the audit and architecture DX scans when a repository is available.",
      "Design the strongest available behavior-preservation oracle before deleting code.",
      "Enumerate deletion, simplification, dependency, config, test, and architecture candidates across every layer.",
      "Search exact or partitioned candidate sets until no untested candidate remains in the current frontier.",
    ],
    outputs: [
      "Before and after metrics, accepted candidates, rejected high-risk candidates, and shrink ratio.",
      "Oracle commands and residual blind spots for the final code-reduction result.",
      "Approval-gated architecture options when structural cleanup is needed before safe slimming.",
    ],
    guardrails: [
      "Do not count minification, obfuscation, whitespace-only deletion, or comment deletion as code slimming.",
      "Do not delete public APIs, migrations, compatibility shims, security checks, operational logging, or config without evidence.",
      "Do not perform architecture-level refactors until the user explicitly approves one option or scope.",
    ],
    entryPoints: [
      {
        label: "Workflow",
        path: "skills/exhaustive-code-slimmer/SKILL.md",
        description: "Exhaustive slimming workflow, oracle rules, and approval gates.",
      },
      {
        label: "Code-slim audit",
        path: "skills/exhaustive-code-slimmer/scripts/code_slim_audit.py",
        description: "Repository inventory, metrics, and candidate enumeration helper.",
      },
      {
        label: "Exhaustive shrink",
        path: "skills/exhaustive-code-slimmer/scripts/exhaustive_shrink.py",
        description: "Exact and partitioned candidate search against an oracle command.",
      },
      {
        label: "Transformation catalog",
        path: "skills/exhaustive-code-slimmer/references/transformation_catalog.md",
        description: "Deletion and simplification candidate catalog.",
      },
      {
        label: "Runtime metadata",
        path: "skills/exhaustive-code-slimmer/agents/openai.yaml",
        description: "Optional agent runtime metadata for this skill.",
      },
    ],
  },
  {
    slug: "reduce-reinvention",
    title: "reduce-reinvention",
    category: "Reuse strategy",
    blurb: "Find duplicated effort and guide reuse-first consolidation.",
    lead:
      "A reuse-first workflow for discovering existing assets, deciding whether to adopt or consolidate, and documenting justified divergence.",
    overview:
      "Use this skill when teams are duplicating code, libraries, services, templates, docs, platform workflows, or architecture decisions. It combines search-before-building habits, duplicate classification, build-vs-reuse scoring, migration planning, and lightweight catalog scripts so reuse decisions are evidence-backed instead of abstract mandates.",
    bestFor: [
      "Auditing duplicated implementations, overlapping services, repeated templates, or abandoned forks.",
      "Deciding whether to adopt, adapt, wrap, extract, consolidate, sunset, or justify divergence.",
      "Creating reusable-asset catalogs, ADR/RFC records, migration plans, golden paths, and governance notes.",
    ],
    workflow: [
      "Frame the duplicated capability, affected owners, target outcome, constraints, and requested depth.",
      "Search local code, docs, manifests, design systems, service catalogs, ADRs, tickets, and conventions before proposing new work.",
      "Classify duplicate candidates by exact copy, near clone, shared business rule, overlapping service, template duplication, abandoned fork, or justified divergence.",
      "Score reuse against fitness, ownership, maintenance, security, compatibility, migration cost, and future evolution.",
      "Recommend an intervention and make the reusable path obvious with examples, owners, lifecycle, feedback channels, and metrics.",
    ],
    outputs: [
      "Evidence with file paths, symbols, package or service names, docs, search terms, owners, consumers, and confidence.",
      "A recommendation with cost, risk, migration effort, security or license concerns, and compatibility notes.",
      "Next actions, owners, acceptance criteria, and a metric that proves duplicated effort decreased.",
    ],
    guardrails: [
      "Do not eliminate duplication solely because code looks alike; verify domain knowledge, change cadence, and future evolution.",
      "Do not create shared libraries, platform services, or golden paths without accountable ownership, examples, versioning, and support expectations.",
      "Do not rely only on automated clone detection; combine script output with code review, domain context, ownership data, and usage evidence.",
    ],
    entryPoints: [
      {
        label: "Workflow",
        path: "skills/reduce-reinvention/SKILL.md",
        description: "Reuse-first audit workflow, recommendations, and guardrails.",
      },
      {
        label: "Reuse playbook",
        path: "skills/reduce-reinvention/references/reuse-playbook.md",
        description: "End-to-end model for making reuse discoverable and maintainable.",
      },
      {
        label: "Audit checklist",
        path: "skills/reduce-reinvention/references/audit-checklist.md",
        description: "Search tactics and evidence-gathering prompts for reinvention audits.",
      },
      {
        label: "Decision matrix",
        path: "skills/reduce-reinvention/references/decision-matrix.md",
        description: "Build-vs-reuse scoring and recommendation rules.",
      },
      {
        label: "Templates",
        path: "skills/reduce-reinvention/references/templates.md",
        description: "Ready-to-fill audit, ADR/RFC, catalog, migration, and exception templates.",
      },
      {
        label: "Reinvention audit",
        path: "skills/reduce-reinvention/scripts/reinvention_audit.py",
        description: "Repository scanner for duplicate-code and reinvention signals.",
      },
      {
        label: "Reuse catalog",
        path: "skills/reduce-reinvention/scripts/reuse_catalog.py",
        description: "Lightweight reusable-asset inventory generator.",
      },
      {
        label: "Runtime metadata",
        path: "skills/reduce-reinvention/agents/openai.yaml",
        description: "Optional agent runtime metadata for this skill.",
      },
    ],
  },
  {
    slug: "find-local-skill",
    title: "find-local-skill",
    category: "Agent workflow",
    blurb: "Decompose requests, then find relevant local skills.",
    lead:
      "A skill-selection workflow for decomposing requests, inventorying local skills, choosing applicable ones, and applying those workflows before normal analysis.",
    overview:
      "Use this skill when an agent needs to inspect available local skills before planning, routing, or implementing a request. It decomposes the ask into deliverables, workflow phases, tools, domains, and implicit prerequisites, then combines session skill metadata with a bundled local scanner for plain project skills folders, Cursor, Claude Code, OpenCode, Codex, shared Agent Skills roots, and plugin skill caches before loading only the skill bodies that materially affect the task.",
    bestFor: [
      "Finding relevant local skills before requirement analysis, planning, or implementation.",
      "Routing ambiguous or multi-phase requests through explicit skill selection instead of relying on memory.",
      "Surfacing prerequisite skills that are implied by a deliverable, tool, or workflow phase.",
      "Auditing available skill coverage across plain project skills folders, Cursor, Claude Code, OpenCode, Codex, and shared Agent Skills roots.",
      "Distinguishing plugin skills with names such as product-design:index.",
    ],
    workflow: [
      "Decompose the request into explicit asks, deliverables, artifacts, tools, workflow phases, and implicit prerequisites.",
      "Inventory skills already present in session context before reading any additional skill bodies.",
      "Run the bundled local scanner when filesystem access is available, including supported user, project, and plugin roots.",
      "Run focused supplemental searches for individual facets or tight synonym groups after the broad inventory.",
      "Compare the request against skill names, namespaced plugin names, descriptions, explicit mentions, tools, file types, products, domains, workflow cues, and decomposed prerequisites.",
      "Select only skills that materially change how the work should be done.",
      "Apply the selected skill workflows in dependency order, then continue with the requested analysis or implementation.",
    ],
    outputs: [
      "A brief skill-selection summary with one reason for each selected skill.",
      "The requested analysis, plan, implementation guidance, or work product using the selected workflows.",
      "A clear note when no suitable local skill was found.",
    ],
    guardrails: [
      "Do not start solution analysis before the decomposition, inventory, and selection pass is complete.",
      "Do not load unrelated skill bodies.",
      "Do not narrow with a query until after the first broad inventory pass.",
      "Do not put unrelated decomposition facets into one long scanner query because the scanner matches all query terms.",
      "Prefer namespaced plugin entries over generic names when both could match the request.",
    ],
    entryPoints: [
      {
        label: "Workflow",
        path: "skills/find-local-skill/SKILL.md",
        description: "Skill inventory, selection, and analysis-order rules.",
      },
      {
        label: "Local skill scanner",
        path: "skills/find-local-skill/scripts/list_agent_skills.py",
        description: "Filesystem scanner for common local skill roots.",
      },
      {
        label: "Runtime metadata",
        path: "skills/find-local-skill/agents/openai.yaml",
        description: "Optional agent runtime metadata for this skill.",
      },
    ],
  },
  {
    slug: "git-commit",
    title: "git-commit",
    category: "Git workflow",
    blurb: "Draft a Conventional Commit message from the staged diff.",
    lead:
      "A narrow commit-message assistant that looks only at the index and returns an accurate Conventional Commit draft.",
    overview:
      "Use this skill when the staged changes are ready but the commit wording needs to be precise. It inspects staged status, staged stats, and the staged diff, then infers the correct Conventional Commit type and message without mutating the repository.",
    bestFor: [
      "Generating a clean subject and body from the current staged batch.",
      "Checking whether staged work is too mixed for one honest commit.",
      "Keeping commit wording grounded in what will actually be committed.",
    ],
    workflow: [
      "Check `git status --short`, `git diff --cached --stat`, and `git diff --cached`.",
      "Stop if nothing is staged rather than falling back to unstaged work.",
      "Infer the commit type from the staged behavior, not from branch names or intent alone.",
      "Draft a Conventional Commit subject and body that names the actual user-visible or structural change.",
      "Return the message text without running `git commit`.",
    ],
    outputs: [
      "A Conventional Commit message proposal.",
      "A warning when the staged batch is mixed or misleading.",
      "No repository mutations.",
    ],
    guardrails: [
      "Inspect staged changes only.",
      "Do not stage files, read unstaged diffs, or create the commit.",
      "Do not invent product context that is not visible in the staged diff.",
    ],
    entryPoints: [
      {
        label: "Workflow",
        path: "skills/git-commit/SKILL.md",
        description: "Staged-only inspection and Conventional Commit drafting rules.",
      },
      {
        label: "Runtime metadata",
        path: "skills/git-commit/agents/openai.yaml",
        description: "Optional agent runtime metadata for this skill.",
      },
    ],
  },
  {
    slug: "mr",
    title: "mr",
    category: "Git workflow",
    blurb: "Use and maintain the Git MR/PR helper CLI.",
    lead:
      "A Git merge-request workflow for running the mr CLI safely across branch strategies, default detached mode, request providers, config, conflict resume with configurable detached worktree placement and dependency setup, automatic update notices, and tool maintenance.",
    overview:
      "Use this skill when creating, previewing, configuring, troubleshooting, installing, updating, uninstalling, or maintaining Git merge requests or pull requests through the `mr`, `mrm`, `mrt`, and `mrp` commands. It keeps agents aligned with the CLI's real request-provider behavior, non-blocking update notices, detached conflict worktree placement and dependency setup, and resume paths for inline and detached conflicts instead of inventing manual git recovery steps.",
    bestFor: [
      "Creating or previewing Git merge requests or pull requests from a current branch to master, test, prerelease, or an arbitrary target.",
      "Checking for a missing local mr install and installing it after user confirmation.",
      "Choosing between merge, rebase, merge-target, direct PR, and default detached-mode workflows.",
      "Configuring CNB, GitHub, GitLab, or custom request commands for pushed source branches.",
      "Understanding automatic update notices and the environment variables that disable them.",
      "Handling stopped merge or rebase states while preserving the CLI-owned resume path, configuring detached conflict worktree placement and IDE worktree detection, and installing worktree dependencies.",
      "Maintaining the TypeScript/Pastel/Ink/Zod implementation behind the CLI.",
    ],
    workflow: [
      "Inspect repository state with `git status --short --branch` before mutating MR branches.",
      "Check `command -v mr` before running CLI-dependent workflows; if missing, ask before installing unless the user explicitly requested install.",
      "Resolve target aliases and clarify source, target, and MR-branch keep/delete intent before acting on ambiguous MR requests.",
      "Use `--dry-run` when strategy, detached mode, or repository state is unclear.",
      "Run exactly one strategy and respect config precedence for strategy, detached mode, request provider, and custom request command settings.",
      "Treat interactive update notices as informational stderr, not workflow output or command failures.",
      "On detached conflicts, install dependencies in the reported worktree when needed; then hand off resolution and rerun the matching `mr` resume command only after conflicts are staged.",
      "When editing the CLI project, verify the implementation repository instead of assuming a local path, and keep README behavior, command examples, and diagrams aligned with implementation changes.",
    ],
    outputs: [
      "Safe command choices for `mr`, `mrm`, `mrt`, and `mrp` workflows.",
      "Update-notice interpretation and disablement guidance.",
      "Conflict handoff, detached worktree placement, dependency setup, and resume instructions that match the current CLI implementation.",
      "Scoped maintenance guidance and verification commands for the mr project.",
    ],
    guardrails: [
      "Do not combine strategy flags or use `--rm-mr` with `--pr`.",
      "Do not replace CLI conflict resume with hand-written git commits, manual pushes, or a shortcut `--pr` flow.",
      "Do not mutate stopped merge/rebase states unless the user explicitly asks for that exact action.",
    ],
    entryPoints: [
      {
        label: "Workflow",
        path: "skills/mr/SKILL.md",
        description: "MR command selection, strategy rules, and conflict-resume guardrails.",
      },
      {
        label: "CLI reference",
        path: "skills/mr/references/mr-cli-reference.md",
        description: "Detailed command surface, detached mode, request providers, config, install, and maintenance notes.",
      },
      {
        label: "Runtime metadata",
        path: "skills/mr/agents/openai.yaml",
        description: "Optional agent runtime metadata for this skill.",
      },
    ],
  },
  {
    slug: "split-commits",
    title: "split-commits",
    category: "Git workflow",
    blurb: "Split a mixed working tree into focused local commits.",
    lead:
      "A disciplined staging workflow for turning broad local changes into a short series of reviewable commits.",
    overview:
      "Use this skill when unrelated concerns, refactors, behavior changes, generated files, or separable hunks are mixed together. It plans logical batches, stages one batch at a time, asks `git-commit` for the message, and waits for explicit approval before committing.",
    bestFor: [
      "Separating unrelated concerns in one working tree.",
      "Keeping refactors apart from behavior changes.",
      "Building local commits that are easier to review, revert, and explain.",
    ],
    workflow: [
      "Inspect current Git state, including staged and unstaged work.",
      "Decide whether the changes need splitting and write a short commit plan.",
      "Respect any existing index content before changing staged files.",
      "Stage one logical batch at a time, including only the files and hunks that belong together.",
      "Invoke `git-commit` for the staged batch and ask for confirmation before running each commit.",
    ],
    outputs: [
      "A proposed sequence of focused commits.",
      "One staged batch at a time with a matching Conventional Commit draft.",
      "Local commits only after explicit user approval.",
    ],
    guardrails: [
      "Do not push as part of the split workflow.",
      "Do not collapse unrelated changes into one convenient commit.",
      "Do not overwrite existing user changes while reshaping the index.",
    ],
    entryPoints: [
      {
        label: "Workflow",
        path: "skills/split-commits/SKILL.md",
        description: "Commit planning, staging, approval, and sequencing rules.",
      },
      {
        label: "Runtime metadata",
        path: "skills/split-commits/agents/openai.yaml",
        description: "Optional agent runtime metadata for this skill.",
      },
    ],
  },
  {
    slug: "multitask-coordinator",
    title: "multitask-coordinator",
    category: "Agent coordination",
    blurb: "Coordinate multi-step work with delegation-first parallel scheduling.",
    lead:
      "A parent-agent scheduler that builds a dependency graph, maximizes useful parallelism, keeps healthy workers uninterrupted, synthesizes evidence, and verifies the integrated result.",
    overview:
      "Use this skill for non-trivial multi-step work that benefits from parallel exploration, implementation, review, or verification. After triggering, the parent frames the objective, builds a task dependency graph, dispatches the maximum useful set of ready non-overlapping workers allowed by tools and isolation capacity, continues event-driven scheduling without interrupting healthy workers, and retains ownership of shared contracts, integration, validation, and user communication. Handle only truly trivial or non-delegable work directly.",
    bestFor: [
      "Maximizing useful parallelism across exploration, implementation, review, and verification.",
      "Building a dependency graph and filling every safe ready worker slot instead of serializing by default.",
      "Assigning disjoint write ownership in large repositories, monorepos, dirty worktrees, or isolated worktrees and branches.",
      "Keeping healthy workers uninterrupted while the parent integrates results and unlocks dependents.",
      "Auditing multi-agent orchestration for hidden serialization, idle capacity, or unnecessary interruption.",
    ],
    workflow: [
      "Frame the objective, acceptance criteria, constraints, and validation boundary.",
      "Read applicable repository rules and inspect the dirty worktree before assigning ownership.",
      "Build a task graph with dependencies, read/write scope, expected evidence, and completion criteria.",
      "Dispatch the maximum useful set of ready non-overlapping workers; continue event-driven scheduling as workers complete.",
      "Do not interrupt healthy workers; work the coordinator path on contracts, integration, and parent-only decisions.",
      "Synthesize evidence, resolve conflicts, verify the integrated result, and report residual risk.",
    ],
    outputs: [
      "A dependency-aware schedule that explains what stays with the parent and what is delegated.",
      "Worker prompts with explicit ownership boundaries, constraints, validation, and expected output.",
      "A synthesis of adopted results, blockers, command evidence, residual risks, and final verification.",
    ],
    guardrails: [
      "Do not leave a safe useful worker slot idle merely to minimize worker count.",
      "Do not cancel, restart, reassign, or send unsolicited follow-ups to healthy workers.",
      "Do not assign sibling workers overlapping write ownership unless isolated branches or worktrees make the planned merge explicit.",
      "Do not accept worker output as fact without reviewing changed files, artifacts, command output, or other concrete evidence.",
    ],
    entryPoints: [
      {
        label: "Workflow",
        path: "skills/multitask-coordinator/SKILL.md",
        description: "Delegation-first scheduling, ownership, healthy-worker continuity, synthesis, and verification rules.",
      },
      {
        label: "Scheduler audit",
        path: "skills/multitask-coordinator/references/scheduler-audit.md",
        description: "Metrics and diagnostics for parallel scheduling effectiveness.",
      },
      {
        label: "Runtime metadata",
        path: "skills/multitask-coordinator/agents/openai.yaml",
        description: "Optional agent runtime metadata for this skill.",
      },
    ],
  },
  {
    slug: "delegate-to-cursor-sdk",
    title: "delegate-to-cursor-sdk",
    category: "Agent coordination",
    blurb: "Route bounded work to Cursor with reviewed packets.",
    lead:
      "A Cursor SDK delegation workflow that keeps upstream ownership over scope, risk gates, model defaults, monitoring, and final acceptance.",
    overview:
      "Use this skill when bounded coding work should be routed through Cursor SDK for inspect-only, proposal, or apply-mode execution. It creates reviewed task packets, defaults Cursor and Cursor internal subagents to composer-2.5-fast unless explicitly overridden, monitors SDK runs through sanitized status files, and treats Cursor output as evidence for upstream review rather than final authority.",
    bestFor: [
      "Dispatching implementation slices through Cursor SDK with explicit scope, non-goals, stop conditions, and verification commands.",
      "Allowing Cursor Task()/taskToolCall internal subagents only under a packet policy with model, concurrency, purpose, and write limits.",
      "Coordinating planned single-stream work or hierarchical workstreams while preserving parent-agent ownership of integration and final approval.",
      "Monitoring long Cursor SDK runs through status.json, including active and recent internal subagents.",
      "Running focused repair loops when Cursor output needs narrow follow-up rather than broad re-planning.",
    ],
    workflow: [
      "Classify the task as direct Cursor, planned single-stream, hierarchical orchestration, or blocked.",
      "Prepare a bounded task packet with the required authority section and Cursor Internal Subagent Policy.",
      "Default Cursor and internal subagents to composer-2.5-fast unless the user explicitly authorizes another Cursor model.",
      "Dispatch through the Cursor SDK wrapper and monitor status.json for low-noise progress.",
      "Review Cursor reports, taskToolCall evidence, diffs, verification results, scope boundaries, and repair output before final acceptance.",
    ],
    outputs: [
      "A routing decision with mode, risk gates, workspace strategy, Cursor mode, model defaults, and internal subagent policy.",
      "A Cursor task packet or repair packet ready for reviewed CLI dispatch.",
      "A final review verdict grounded in logs, diffs, verification evidence, and any internal subagent reports.",
    ],
    guardrails: [
      "Do not use this skill unless the user explicitly invokes delegate-to-cursor-sdk or $delegate-to-cursor-sdk.",
      "Do not allow Cursor internal subagents unless the task packet includes a Cursor Internal Subagent Policy.",
      "Do not treat support, planning, workstream, or internal subagent output as final authority without upstream review.",
      "Do not commit, push, deploy, rotate credentials, alter billing, or broaden scope unless explicitly requested and reviewed.",
    ],
    entryPoints: [
      {
        label: "Workflow",
        path: "skills/delegate-to-cursor-sdk/SKILL.md",
        description: "Routing, model defaults, guardrails, review ownership, and final reporting rules.",
      },
      {
        label: "Internal subagents",
        path: "skills/delegate-to-cursor-sdk/references/cursor-internal-subagents.md",
        description: "Cursor Task()/taskToolCall policy, evidence, and model defaults.",
      },
      {
        label: "Direct task packet",
        path: "skills/delegate-to-cursor-sdk/references/task-direct.md",
        description: "Template for direct Cursor implementation packets.",
      },
      {
        label: "Planned task packet",
        path: "skills/delegate-to-cursor-sdk/references/task-planned.md",
        description: "Template for upstream-reviewed plan implementation packets.",
      },
      {
        label: "Local workstream packet",
        path: "skills/delegate-to-cursor-sdk/references/task-local.md",
        description: "Template for bounded hierarchical workstream packets.",
      },
      {
        label: "User-plan packet",
        path: "skills/delegate-to-cursor-sdk/references/task-user-plan.md",
        description: "Template for accepted user-provided plan packets.",
      },
      {
        label: "Follow-up packet",
        path: "skills/delegate-to-cursor-sdk/references/task-follow-up.md",
        description: "Template for bounded review follow-up packets.",
      },
      {
        label: "Dispatch wrapper",
        path: "skills/delegate-to-cursor-sdk/scripts/cursor_delegate.mjs",
        description: "Cursor SDK wrapper with authority, git, log, authorization, and status checks.",
      },
      {
        label: "Runtime metadata",
        path: "skills/delegate-to-cursor-sdk/agents/openai.yaml",
        description: "Optional agent runtime metadata for this skill.",
      },
    ],
  },
  {
    slug: "plan-mode",
    title: "plan-mode",
    category: "Planning",
    blurb: "Create Cursor-style editable plan files before building.",
    lead:
      "A Cursor-style planning workflow that creates an editable Markdown plan file with code references and todos, then builds only after approval.",
    overview:
      "Use this skill when work is complex, ambiguous, risky, or broad enough that premature edits would create churn or damage user intent. It mirrors Cursor's Plan Mode loop: create or update a disk-backed editable plan file, research the codebase into file and code references, ask focused clarification questions, maintain buildable todos, invoke `grill-me` for non-trivial pressure-testing, validate the plan artifact, and build only from the approved plan.",
    bestFor: [
      "Planning multi-file implementation, architecture, routing, data-flow, or tradeoff-heavy work.",
      "Maintaining a live Markdown plan document with file references, code references, and checkbox todos.",
      "Invoking `grill-me` to pressure-test meaningful assumptions, risks, failure modes, and rollout or rollback edges.",
      "Holding a strict boundary around dirty worktrees, migrations, settings, deployment, generated code, or other high-blast-radius surfaces.",
      "Building all or selected todos only after the user approves the plan.",
    ],
    workflow: [
      "Create or reuse the Markdown plan file immediately and cite its path.",
      "Research only what is needed, then update the plan with concrete file paths, code references, constraints, and open questions.",
      "Ask clarifying questions when decisions would change the plan, and update the file after each answer.",
      "Maintain editable checkbox todos that can be selected and built from later.",
      "Invoke `grill-me` before approval when the plan has meaningful assumptions, tradeoffs, failure modes, or scope edges.",
      "Validate the plan artifact, summarize it in chat, and wait for approval before building from all or selected todos.",
    ],
    outputs: [
      "A concrete approval-gated Markdown plan file with file/code references and editable todos.",
      "`grill-me` transcript and planning-ready outcome paths when a pressure-test was needed.",
      "Focused clarification questions when ambiguity would change the plan.",
      "A clean build-from-plan handoff after approval, including promised validation steps.",
    ],
    guardrails: [
      "Do not edit implementation files, stage commits, install packages, start services, or run write-oriented scripts while planning; plan files and `grill-me` logs/outcomes are the only allowed writes.",
      "Do not hide unresolved product, data, safety, or architecture assumptions inside the final plan.",
      "Do not build without rereading the plan file and confirming whether approval covers all todos or only selected todos.",
    ],
    entryPoints: [
      {
        label: "Workflow",
        path: "skills/plan-mode/SKILL.md",
        description: "Planning boundary, workflow, clarification rules, and handoff requirements.",
      },
      {
        label: "Plan artifact helper",
        path: "skills/plan-mode/scripts/plan_artifact.py",
        description: "Creates and validates required Markdown plan artifacts.",
      },
      {
        label: "Architecture reference",
        path: "skills/plan-mode/references/architecture.md",
        description: "Lifecycle, mode boundary, research strategy, diagrams, and common failure modes.",
      },
      {
        label: "Runtime metadata",
        path: "skills/plan-mode/agents/openai.yaml",
        description: "Optional agent runtime metadata for this skill.",
      },
    ],
  },
  {
    slug: "debug",
    title: "debug",
    category: "Runtime debugging",
    blurb: "Maximize root-cause evidence from one failing reproduction.",
    lead:
      "A coverage-first debugging system with a machine-validated hypothesis-and-probe plan, bounded runtime evidence, correlation-aware analysis, and optional specialized browser capture.",
    overview:
      "Use this skill when code reading is not enough and the first failing reproduction should carry as much discriminating evidence as safely possible. It builds a code-grounded causal map, records material hypotheses with both confirming and rejecting evidence, validates one `debug-plan/v1` file, and reuses that plan for collector location sync and expected-probe analysis. Correlated NDJSON is summarized by run, parent flow, operation, request, and child correlation before raw events are inspected. Diagnosis stops before behavior changes unless repair is authorized; authorized repairs are verified in a separate run before temporary instrumentation is removed. Complete browser `fetch` capture remains available through a conditionally loaded acknowledged transport.",
    bestFor: [
      "Expensive, flaky, timing-sensitive, destructive, environment-specific, or user-only reproductions.",
      "Runtime failures that are easy to guess about but hard to prove across causal boundaries.",
      "Investigations that need a deterministic coverage gate before adding broad temporary instrumentation.",
      "Concurrent or distributed flows that need parent-flow, operation, request, attempt, and ordering evidence.",
      "Browser investigations that conditionally require complete page-lifetime application-fetch capture.",
    ],
    workflow: [
      "Confirm diagnosis-versus-repair scope, choose the reproduction owner, define the failure contract, and inspect the relevant execution path.",
      "Build a causal-boundary map and enumerate code-grounded material hypotheses with both confirming and rejecting evidence.",
      "Create and validate one `debug-plan/v1` file whose boundaries, hypotheses, probes, observer controls, privacy checks, and residual ambiguities agree.",
      "Start or attach a logging session, instrument shared causal cuts and invariants, then pass compile, transport, collector, and expected-probe gates.",
      "Collect one clean failing run and summarize evidence by run, parent flow, operation, request, and child correlation before reading raw volume.",
      "Prove origin-to-symptom propagation or add only probes for the smallest unresolved causal interval.",
      "For diagnosis-only work, preserve evidence and clean temporary instrumentation before reporting; when repair is authorized, repair the proven mechanism, verify separately, and then clean owned artifacts.",
    ],
    outputs: [
      "A validated machine-readable coverage plan shared by location sync and expected-probe analysis.",
      "A cited origin-to-symptom proof or the smallest explicitly unresolved causal interval.",
      "An optional incremental investigation ledger for durable or multi-run work.",
      "When authorized, a causally sufficient repair backed by a separate verification run and deterministic cleanup.",
    ],
    guardrails: [
      "Do not claim a root cause without evidence for the originating fault, its propagation, and the reported symptom.",
      "Do not add a correlation header when it could change CORS, cache, routing, signing, authorization, or product behavior.",
      "Do not let dashboard availability gate evidence collection or reproduction.",
      "Do not apply a repair when the request is diagnosis-only or retain a smaller workaround that leaves the causal mechanism active.",
      "Do not sample, truncate, or count-cap required application-fetch lifecycle events when complete browser coverage is explicitly required.",
      "Do not analyze unbounded raw logs before summarization or leave temporary instrumentation and owned artifacts after successful cleanup.",
    ],
    entryPoints: [
      {
        label: "Workflow",
        path: "skills/debug/SKILL.md",
        description: "Coverage-first debugging sequence, authority boundaries, and cleanup requirements.",
      },
      {
        label: "Coverage planning",
        path: "skills/debug/references/coverage-first-debugging.md",
        description: "Causal maps, material hypotheses, debug-plan/v1, and the reproduction gate.",
      },
      {
        label: "Runtime reference",
        path: "skills/debug/references/runtime-debugging.md",
        description: "Collector bootstrap, session operations, structured logs, and cleanup.",
      },
      {
        label: "Browser reference",
        path: "skills/debug/references/browser-debugging.md",
        description: "Conditional browser transport, flow correlation, fetch capture, and lifecycle rules.",
      },
      {
        label: "Root-cause reference",
        path: "skills/debug/references/root-cause-document.md",
        description: "Structure for the incremental evidence and exclusion ledger.",
      },
      {
        label: "Coverage validator",
        path: "skills/debug/scripts/debug_plan.py",
        description: "Validate the shared coverage plan and fail closed before reproduction.",
      },
      {
        label: "Session helper",
        path: "skills/debug/scripts/debug_session.py",
        description: "Start, confirm, recover, and stop the local collector and dashboard session.",
      },
      {
        label: "Browser transport",
        path: "skills/debug/assets/browser-debug-transport.mjs",
        description: "Page-local in-memory queue for byte-framed acknowledged fetch capture.",
      },
      {
        label: "Log summarizer",
        path: "skills/debug/scripts/summarize_debug_log.py",
        description: "Summarize NDJSON evidence before reading raw volume.",
      },
      {
        label: "Collector",
        path: "skills/debug/scripts/local_log_collector/",
        description: "Local NDJSON collector and dashboard implementation.",
      },
      {
        label: "Lifecycle tests",
        path: "skills/debug/scripts/test_debug_tools.py",
        description: "Session, coverage-plan sync, correlation-summary, dashboard, and lifecycle regressions.",
      },
      {
        label: "Coverage-plan tests",
        path: "skills/debug/scripts/test_debug_plan.py",
        description: "Schema, mapping, sentinel, and gate validation regressions.",
      },
      {
        label: "Browser transport tests",
        path: "skills/debug/scripts/test_browser_debug_transport.mjs",
        description: "Memory-queue, complete-fetch, batching, timeout, and retry regressions.",
      },
    ],
  },
  {
    slug: "grill-me",
    title: "grill-me",
    category: "Planning pressure test",
    blurb: "Pressure-test a plan or design one high-leverage question at a time.",
    lead:
      "A structured interrogation workflow for making assumptions, tradeoffs, risks, and scope edges explicit.",
    overview:
      "Use this skill when a plan, design, rollout, or technical direction needs to be stress-tested before implementation. It asks one question at a time, keeps a Markdown Q&A log in sync, and finalizes a planning-ready outcome when the decision is concrete enough for another engineer to execute.",
    bestFor: [
      "Turning vague plans into explicit success criteria, non-goals, and phase boundaries.",
      "Finding hidden failure modes, irreversible decisions, and stakeholder costs.",
      "Producing a planning-ready record from a live Q&A session.",
    ],
    workflow: [
      "Start or resume the local grilling log for the session.",
      "Ask the highest-leverage unresolved question instead of collecting shallow preferences.",
      "Cover objective, scope, stakeholders, alternatives, risks, validation, rollout, and rollback where relevant.",
      "Keep the transcript synchronized with the conversation as the plan sharpens.",
      "Finalize an outcome Markdown file and remove the active session pointer.",
    ],
    outputs: [
      "A live Q&A transcript.",
      "A finalized planning-ready outcome document.",
      "Explicit assumptions, tradeoffs, risks, and open decisions.",
    ],
    guardrails: [
      "Ask one question at a time.",
      "Do not accept vague answers as final planning input.",
      "Do not leave the active session pointer behind after finalization.",
    ],
    entryPoints: [
      {
        label: "Workflow",
        path: "skills/grill-me/SKILL.md",
        description: "Questioning standard, coverage map, and finalization flow.",
      },
      {
        label: "Session script",
        path: "skills/grill-me/scripts/grill_log.py",
        description: "Local transcript and outcome file support.",
      },
      {
        label: "Reference",
        path: "skills/grill-me/references/logged-grilling.md",
        description: "Logged grilling behavior and session lifecycle notes.",
      },
    ],
  },
  {
    slug: "code-review",
    title: "code-review",
    category: "Code review",
    blurb: "Run product-grounded deep reviews with bounded report lineage.",
    lead:
      "A frozen-scope deep review workflow with authoritative expected-behavior evidence, stable issue fingerprints, and a terminal post-implementation generation.",
    overview:
      "Use this skill for `/code-review`, PR or diff review, branch or staged-change review, and merge-safety assessment. It begins with one read-only orchestration assessor, freezes the initial scope, traces propagated risk, requires authoritative product or contract evidence before classifying a product choice as a defect, and assigns deterministic semantic issue fingerprints. A receiving workflow may create one generation-1 review limited to the implementation delta and affected execution chains; that report is terminal and cannot automatically start another receiving cycle.",
    bestFor: [
      "Reviewing PRs, branch diffs, staged changes, working trees, focused files, or pasted code.",
      "Deciding when parallel specialist subagents add material review value.",
      "Surfacing correctness bugs, release-blocking regressions, security issues, contract risks, and missing tests.",
      "Separating verified defects from unconfirmed or settled product intent.",
      "Producing a reusable artifact with coverage evidence, semantic issue lineage, and a bounded receiving handoff.",
    ],
    workflow: [
      "Resolve review-chain generation, freeze scope, and capture baseline, target, requirements, and a minimal diff inventory.",
      "Launch the read-only orchestration-assessment subagent and follow its single-reviewer or specialist plan.",
      "Trace changed control, data, security, persistence, integration, and test paths beyond the diff when risk can propagate.",
      "Ground expected behavior, independently verify and de-duplicate candidates, then assign stable IDs, issue keys, and fingerprints.",
      "Write a canonical `code-review` Markdown report from the template, then validate it with `scripts/validate_review_report.py`.",
    ],
    outputs: [
      "A validated canonical `code-review` Markdown report.",
      "A short terminal summary with recommendation, completion, severity counts, and orchestration mode.",
      "A complete findings index, test gaps, coverage ledger, issue lineage, and bounded receiving handoff.",
    ],
    guardrails: [
      "Do not make code changes during review unless the user explicitly asks for fixes.",
      "Do not stage, commit, push, or mutate Git state.",
      "Do not equate review depth with agent count; launch specialists only when justified by scope and risk.",
      "Do not copy subagent conclusions into the report without independent coordinator synthesis.",
      "Do not classify an unconfirmed product choice as a defect; use an approval-affecting Question.",
      "Do not automatically consume a generation-1 post-review; return its findings to the user or product owner.",
      "Use `regression-review` or `hack-review` instead when the user asks for those specialized gates.",
    ],
    entryPoints: [
      {
        label: "Workflow",
        path: "skills/code-review/SKILL.md",
        description: "Orchestration, deep-review contract, report-writing rules, and guardrails.",
      },
      {
        label: "Subagent orchestration",
        path: "skills/code-review/references/subagent-orchestration.md",
        description: "Assessment protocol and specialist partition guidance.",
      },
      {
        label: "Report template",
        path: "skills/code-review/references/report-template.md",
        description: "Canonical code-review report sections and coverage ledger shape.",
      },
      {
        label: "Report validator",
        path: "skills/code-review/scripts/validate_review_report.py",
        description: "Validates lineage, expected-basis authority, fingerprints, and terminal generation rules.",
      },
      {
        label: "Validator tests",
        path: "skills/code-review/scripts/test_validate_review_report.py",
        description: "Regression coverage for report lineage and product-intent gates.",
      },
      {
        label: "Runtime metadata",
        path: "skills/code-review/agents/openai.yaml",
        description: "Optional agent runtime metadata for this skill.",
      },
    ],
  },
  {
    slug: "thermo-review",
    title: "thermo-review",
    category: "Code review",
    blurb: "Write harsh structural quality reports.",
    lead:
      "An extremely strict code-quality gate for structural simplification, file-size pressure, abstraction boundaries, and spaghetti growth.",
    overview:
      "Use this skill when a change needs a thermonuclear maintainability review rather than a general correctness review. It reviews the relevant scope, writes a Markdown report, applies a 350-line threshold for maintained source files, recursively sweeps structural candidates until coverage reaches a fixed point or is marked incomplete, and avoids code changes unless explicitly asked for fixes.",
    bestFor: [
      "Reviewing whether a diff makes the implementation more tangled, oversized, indirect, or hard to extend.",
      "Finding missed code-judo simplifications, decomposition opportunities, canonical-ownership moves, and clearer type boundaries.",
      "Producing a durable structural review artifact with findings, recursive coverage, line-count evidence, and residual blind spots.",
    ],
    workflow: [
      "Set the review scope and baseline, preferring staged changes before the working tree when the user does not name a scope.",
      "Build a diff and line-count inventory, including the 350-line maintained-source threshold check.",
      "Seed a recursive candidate frontier from file growth, branches, helpers, abstractions, types, ownership boundaries, orchestration, tests, and duplicated blocks.",
      "Trace each candidate inward and outward through local flow, call sites, contracts, tests, and canonical helpers.",
      "Append newly discovered simplification candidates until the frontier reaches a fixed point or uncovered areas are explicitly marked.",
      "Write a Markdown report with recommendation, findings, decomposition gaps, recursive coverage ledger, and evidence appendix.",
    ],
    outputs: [
      "A Markdown thermo-nuclear code-quality report.",
      "A short terminal summary with recommendation, completion status, severity counts, and top structural risks.",
      "A recursive coverage ledger, line-count ledger, candidate sweep log, and quality-gate recommendation.",
    ],
    guardrails: [
      "Do not make code changes during review unless the user explicitly asks for fixes.",
      "Do not treat passing tests as proof that the implementation is structurally sound.",
      "Do not silently waive the 350-line maintained-source threshold; account for oversized files or mark the area uncovered.",
      "Use `code-review` instead when correctness, security, privacy, data loss, or merge safety is the main question.",
    ],
    entryPoints: [
      {
        label: "Workflow",
        path: "skills/thermo-review/SKILL.md",
        description: "Structural quality gate, recursive sweep, 350-line threshold, and report rules.",
      },
      {
        label: "Report template",
        path: "skills/thermo-review/references/report-template.md",
        description: "Canonical report sections, recursive coverage ledger, and line-count ledger.",
      },
      {
        label: "Runtime metadata",
        path: "skills/thermo-review/agents/openai.yaml",
        description: "Optional agent runtime metadata for this skill.",
      },
    ],
  },
  {
    slug: "receiving-thermo-review",
    title: "receiving-thermo-review",
    category: "Code review follow-up",
    blurb: "Resolve harsh structural review reports.",
    lead:
      "A response workflow for consuming thermo reports without blindly turning harsh feedback into broad refactors or behavior regressions.",
    overview:
      "Use this skill after a thermo report or equivalent structural review feedback. It builds a disposition ledger for every finding, decomposition gap, recursive coverage row, line-count threshold item, candidate sweep entry, and blind spot before changing code, adds a behavior-parity ledger for touched user-visible or unknown-impact surfaces, then fixes only verified structural issues while preserving Git staging and avoiding unapproved architecture refactors.",
    bestFor: [
      "Verifying harsh structural findings against the current diff, line counts, call sites, and ownership boundaries.",
      "Resolving 350-line threshold concerns, decomposition gaps, recursive coverage gaps, and candidate sweep items.",
      "Applying scoped behavior-preserving simplifications while checking source, guard, output, and extension-point parity.",
    ],
    workflow: [
      "Read the full report and confirm scope, baseline, completion status, and current checkout still match.",
      "Create a disposition ledger from findings, decomposition gaps, recursive coverage rows, line-count rows, sweep rows, and blind spots.",
      "Resolve report inconsistencies or stale line counts before editing.",
      "Present a structural change plan with behavior-parity, ownership, verification, and no-staging notes before changing code.",
      "Fix or disprove Blocker and Major items first, then decide Minor, Question, decomposition, and coverage items.",
      "Recompute affected line counts and run targeted verification for every touched surface.",
    ],
    outputs: [
      "A full disposition ledger for every consumed thermo report item.",
      "Scoped structural fixes or evidence-backed challenges, waivers, and carry-forward decisions.",
      "Updated line-count, coverage, and behavior-parity status for affected surfaces.",
    ],
    guardrails: [
      "Do not blindly apply thermo review feedback.",
      "Do not start broad architecture refactors without approved scope.",
      "Do not hide potential user-visible regressions behind structural cleanup.",
      "Do not stage changes unless the current request explicitly asks for staging, committing, or PR publication.",
      "Do not claim the thermo gate is resolved until every finding, decomposition gap, threshold item, and open coverage row is accounted for.",
    ],
    entryPoints: [
      {
        label: "Workflow",
        path: "skills/receiving-thermo-review/SKILL.md",
        description: "Disposition ledger, structural response rules, and Git staging guardrails.",
      },
      {
        label: "Runtime metadata",
        path: "skills/receiving-thermo-review/agents/openai.yaml",
        description: "Optional agent runtime metadata for this skill.",
      },
    ],
  },
  {
    slug: "receiving-code-review",
    title: "receiving-code-review",
    category: "Code review follow-up",
    blurb: "Trace findings end to end and resolve them without recursive review loops.",
    lead:
      "An execution-chain-first response workflow that preserves settled intent, enforces compatible dispositions, and bounds post-implementation review.",
    overview:
      "Use this skill after a `code-review` report or equivalent PR feedback. Before assigning dispositions, it reconstructs each problem from its real trigger and entry through guards, control/data/state propagation, persistence and external effects, failure semantics, and terminal impact. It preserves matching Intentional, Disproved, Stale, and Duplicate decisions across generations, blocks fixes when chain or product-authority evidence is incomplete, delegates only compatible confirmed actions, returns distinct adjacent discoveries as provisional residuals, and allows at most one terminal post-implementation review without automatically consuming its findings.",
    bestFor: [
      "Re-verifying every `F#`, `T#`, and uncovered `A#` against a complete end-to-end execution chain.",
      "Formally challenging incorrect, overstated, or stale review claims with evidence.",
      "Fixing confirmed correctness, security, contract, or test issues through a coding subagent.",
      "Preserving authoritative product intent unless code, contract, or material evidence changes.",
      "Preserving staged work while keeping new fixes unstaged unless publication is requested.",
    ],
    workflow: [
      "Read the complete source review or normalize unstructured feedback into stable item IDs.",
      "Capture lineage and Git state, then reconstruct and freeze reusable EC# execution chains before launching re-review orchestration.",
      "Verify each item against its complete chain and expected-behavior authority, then assign compatible verdict, action, and implementation states.",
      "Delegate confirmed fix or test work to a coding subagent with explicit ownership and a no-staging rule.",
      "Use at most one implementation-delta post-review for a generation-0 source, link it as terminal, and return remaining findings without automatic receiving.",
    ],
    outputs: [
      "A validated `receiving-code-review` disposition ledger and resolution report.",
      "Formal challenge cards for disputed source claims.",
      "Auditable EC# execution-chain and semantic-lineage ledgers.",
      "Scoped unstaged fixes for confirmed review findings, plus verification evidence.",
    ],
    guardrails: [
      "Do not blindly apply review feedback.",
      "Do not edit code until intake, item enumeration, and complete-or-blocked EC# reconstruction are recorded.",
      "Do not implement confirmed code or test changes only in the coordinator when a coding subagent is available.",
      "Do not stage, commit, or mutate the Git index unless the current request explicitly asks for it.",
      "Do not claim resolution until every source item has a disposition and every implemented item has targeted verification.",
      "Do not silently drop or auto-implement distinct verifier discoveries; return them as provisional residual candidates.",
      "Do not auto-fix blocked chains or unconfirmed product choices, and do not start another receiving cycle from the terminal post-review.",
    ],
    entryPoints: [
      {
        label: "Workflow",
        path: "skills/receiving-code-review/SKILL.md",
        description: "Re-review, challenge, coding delegation, and Git-index preservation rules.",
      },
      {
        label: "Re-review orchestration",
        path: "skills/receiving-code-review/references/re-review-orchestration.md",
        description: "Assessment protocol and specialist re-review guidance.",
      },
      {
        label: "Disposition template",
        path: "skills/receiving-code-review/references/disposition-template.md",
        description: "Canonical receiving-code-review resolution report shape.",
      },
      {
        label: "Disposition validator",
        path: "skills/receiving-code-review/scripts/validate_disposition_report.py",
        description: "Validates execution chains, lineage inheritance, state compatibility, and the one-review budget.",
      },
      {
        label: "Validator tests",
        path: "skills/receiving-code-review/scripts/test_validate_disposition_report.py",
        description: "Regression coverage for chain-first dispositions and bounded follow-up.",
      },
      {
        label: "Runtime metadata",
        path: "skills/receiving-code-review/agents/openai.yaml",
        description: "Optional agent runtime metadata for this skill.",
      },
    ],
  },
  {
    slug: "hack-review",
    title: "hack-review",
    category: "Code review",
    blurb: "Review whether an implementation relies on brittle hack-like shortcuts.",
    lead:
      "A coverage-led audit for structural shortcuts, ownership leaks, masked root causes, and brittle boundary work.",
    overview:
      "Use this skill when a change needs an implementation-quality gate rather than a general code review. It reviews a declared scope, enumerates every distinct hack-risk finding, records intentional exceptions, and shows which ownership boundaries were covered or left unknown.",
    bestFor: [
      "Finding impossible-state fallbacks that hide broken invariants.",
      "Flagging symptom-masking patches that do not address root cause.",
      "Catching duplicate abstractions, hardcoded special cases, and boundary bypasses.",
    ],
    workflow: [
      "Set the review scope first and refuse to silently widen it.",
      "Read relevant diffs, requirements, and touched ownership boundaries.",
      "Identify hack-risk patterns and group them into distinct findings.",
      "Write a Markdown report with recommendation, findings, intentional exceptions, and coverage ledger.",
      "Keep the gate aligned with the highest-severity unresolved finding and coverage state.",
    ],
    outputs: [
      "A coverage-led Markdown hack-risk report.",
      "A short terminal summary.",
      "A complete index of findings, intentional exceptions, and uncovered boundaries.",
    ],
    guardrails: [
      "Do not sample large scopes silently.",
      "Do not lower the recommendation below the strongest unresolved finding.",
      "Use `regression-review` instead when the main question is user-visible behavior.",
    ],
    entryPoints: [
      {
        label: "Workflow",
        path: "skills/hack-review/SKILL.md",
        description: "Scope, findings, gate, and report-writing rules.",
      },
      {
        label: "Report template",
        path: "skills/hack-review/references/report-template.md",
        description: "Canonical report sections and coverage ledger shape.",
      },
      {
        label: "Runtime metadata",
        path: "skills/hack-review/agents/openai.yaml",
        description: "Optional agent runtime metadata for this skill.",
      },
    ],
  },
  {
    slug: "receiving-hack-review",
    title: "receiving-hack-review",
    category: "Code review follow-up",
    blurb: "Consume a hack-review report and verify each finding before changing code.",
    lead:
      "A response workflow for turning hack-risk review findings into evidence-backed fixes, challenges, or carry-forward decisions.",
    overview:
      "Use this skill after a hack-review report or equivalent PR feedback. It builds a disposition ledger for every finding, intentional exception, and coverage gap before changing code, then fixes only what still applies and preserves evidence for challenged or narrowed items.",
    bestFor: [
      "Verifying that each hack-risk finding still applies to the current diff.",
      "Fixing ownership problems without mechanically deleting necessary guards.",
      "Closing or carrying forward `Not covered` ownership boundaries.",
    ],
    workflow: [
      "Read the review report and enumerate every finding, exception, and coverage gap.",
      "Verify each item against the current code before planning edits.",
      "Create a disposition ledger: fix, disprove, narrow, confirm, or carry forward.",
      "Apply scoped fixes while naming affected ownership boundaries and regression risk.",
      "Report the final disposition for every item without staging unless explicitly asked.",
    ],
    outputs: [
      "A disposition ledger for the entire report.",
      "Evidence-backed code changes for confirmed items.",
      "A summary of disproven, narrowed, intentional, and carried-forward items.",
    ],
    guardrails: [
      "Do not execute the report mechanically.",
      "Do not stage changes unless the current request explicitly asks for staging or committing.",
      "Narrow or ask before editing if the fix would broaden behavior or weaken ownership boundaries.",
    ],
    entryPoints: [
      {
        label: "Workflow",
        path: "skills/receiving-hack-review/SKILL.md",
        description: "Disposition ledger and evidence-first response rules.",
      },
      {
        label: "Runtime metadata",
        path: "skills/receiving-hack-review/agents/openai.yaml",
        description: "Optional agent runtime metadata for this skill.",
      },
    ],
  },
  {
    slug: "regression-review",
    title: "regression-review",
    category: "Code review",
    blurb: "Review code changes for user-visible behavioral regressions.",
    lead:
      "A coverage-led audit for broken or degraded user journeys, changed defaults, stale data, and behavior-path changes.",
    overview:
      "Use this skill when a change set needs a user-visible behavior gate. It reviews a declared scope, separates intended visible changes from regressions, builds scoped behavior-graph deltas when they clarify affected paths, and writes a report that maps every touched surface to reviewed, intentional, not covered, or not relevant.",
    bestFor: [
      "Checking whether refactors or feature work broke user-facing flows.",
      "Auditing loading, error, permission, retry, ordering, export, email, or CLI-output changes.",
      "Tracing changed inputs, guards, transforms, and outputs without building a whole-repo call graph.",
      "Producing a review artifact with severity tied to the strongest unresolved finding.",
    ],
    workflow: [
      "Set or infer the review scope and read requirements when available.",
      "Map touched user-visible surfaces before judging behavior.",
      "Build scoped behavior graph baselines for graphable user-visible or unknown-impact surfaces.",
      "Compare current behavior against baseline, intent, and user expectations.",
      "Write all distinct findings, not only the top few.",
      "Record intentional visible changes and uncovered surfaces in the coverage ledger.",
    ],
    outputs: [
      "A Markdown regression-review report.",
      "A gate recommendation aligned to findings and coverage.",
      "A complete findings index, behavior graph deltas, and coverage ledger.",
    ],
    guardrails: [
      "Do not silently sample a large review scope.",
      "Do not treat implementation ugliness as a regression unless it changes visible behavior.",
      "Use `hack-review` instead when the main concern is brittle implementation structure.",
    ],
    entryPoints: [
      {
        label: "Workflow",
        path: "skills/regression-review/SKILL.md",
        description: "Scope, user-visible findings, coverage, and gate rules.",
      },
      {
        label: "Report template",
        path: "skills/regression-review/references/report-template.md",
        description: "Canonical report sections and coverage ledger shape.",
      },
      {
        label: "Runtime metadata",
        path: "skills/regression-review/agents/openai.yaml",
        description: "Optional agent runtime metadata for this skill.",
      },
    ],
  },
  {
    slug: "receiving-regression-review",
    title: "receiving-regression-review",
    category: "Code review follow-up",
    blurb: "Consume a regression-review report and verify each finding before changing code.",
    lead:
      "A response workflow for resolving regression-review findings with current evidence and scoped fixes.",
    overview:
      "Use this skill after a regression-review report or related PR feedback. It verifies every finding, behavior graph delta, intentional visible change, and coverage gap against the current code before editing, then fixes proven regressions and challenges stale or intentional findings with evidence.",
    bestFor: [
      "Re-checking a regression gate against the current diff and baseline.",
      "Reconciling behavior graph deltas with findings and coverage rows.",
      "Fixing only proven user-visible regressions.",
      "Separating real regressions from intentional product changes.",
    ],
    workflow: [
      "Read the report and list every finding, intentional change, and uncovered surface.",
      "Reconcile behavior graph deltas with the current code path and coverage ledger.",
      "Verify each item against the current code, baseline, and visible behavior.",
      "Create a disposition ledger before editing.",
      "Fix confirmed regressions with narrowly scoped changes.",
      "Report a disposition for every item and leave Git staging untouched unless asked.",
    ],
    outputs: [
      "A full disposition ledger.",
      "Scoped fixes for confirmed user-visible regressions.",
      "Evidence for challenged, narrowed, intentional, and carried-forward items.",
    ],
    guardrails: [
      "Do not blindly apply review feedback.",
      "Do not stage changes unless the current request explicitly asks for it.",
      "Do not broaden user-visible behavior while resolving a focused regression finding.",
    ],
    entryPoints: [
      {
        label: "Workflow",
        path: "skills/receiving-regression-review/SKILL.md",
        description: "Disposition ledger and regression-response requirements.",
      },
      {
        label: "Runtime metadata",
        path: "skills/receiving-regression-review/agents/openai.yaml",
        description: "Optional agent runtime metadata for this skill.",
      },
    ],
  },
];

export function getSkillBySlug(slug: string) {
  return SKILLS.find((skill) => skill.slug === slug);
}

export function getSkillNeighbors(slug: string) {
  const index = SKILLS.findIndex((skill) => skill.slug === slug);

  return {
    previous: index > 0 ? SKILLS[index - 1] : undefined,
    next: index >= 0 && index < SKILLS.length - 1 ? SKILLS[index + 1] : undefined,
  };
}
