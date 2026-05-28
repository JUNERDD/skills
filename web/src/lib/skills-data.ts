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
    blurb: "Coordinate complex subagent work with clear ownership boundaries.",
    lead:
      "A parent-agent workflow for deciding when to delegate, assigning worker scopes, synthesizing results, and verifying the final outcome.",
    overview:
      "Use this skill for non-trivial multi-step work where background subagents may help but the parent agent must keep ownership of framing, shared contracts, delegation, integration, verification, and user communication. It gives the coordinator a decision checklist for handling simple work directly, choosing explorer or worker shapes, defining disjoint scopes, protecting atomic migrations, and turning worker outputs into reviewed evidence.",
    bestFor: [
      "Deciding whether a complex repo task should be handled directly or delegated.",
      "Assigning clear worker ownership boundaries in large repositories, monorepos, or dirty worktrees.",
      "Keeping shared contracts, package exports, sequencing, and destructive migration boundaries under parent-agent ownership.",
      "Coordinating independent exploration, implementation, review, or verification slices.",
      "Synthesizing worker outputs while preserving parent-agent accountability for the final result.",
    ],
    workflow: [
      "Read applicable repository rules and check the dirty worktree before assigning ownership.",
      "Map success criteria, affected systems, likely owner files, shared contracts, and verification commands.",
      "Keep shared files and contracts parent-owned unless one worker is explicitly assigned as the sole owner.",
      "Choose zero, one, or a small set of workers based on independence, scope clarity, and synthesis cost.",
      "Give each worker a concrete objective, allowed scope, forbidden actions, validation expectation, and output contract.",
      "Review worker evidence, resolve conflicts or gaps, integrate only adopted work, and run the narrowest credible verification.",
    ],
    outputs: [
      "A delegation decision that explains what stays with the parent and what, if anything, is assigned to workers.",
      "Worker prompts with explicit ownership boundaries, constraints, validation, and expected output.",
      "A synthesis of adopted results, blockers, command evidence, residual risks, and final verification.",
    ],
    guardrails: [
      "Do not delegate trivial requests or immediate blocking work that the parent must handle now.",
      "Do not assign sibling workers overlapping write ownership for shared files, schemas, generated artifacts, or global config.",
      "Do not accept worker output as fact without reviewing changed files, artifacts, command output, or other concrete evidence.",
    ],
    entryPoints: [
      {
        label: "Workflow",
        path: "skills/multitask-coordinator/SKILL.md",
        description: "Delegation decisions, worker prompt contracts, synthesis, and verification rules.",
      },
      {
        label: "Runtime metadata",
        path: "skills/multitask-coordinator/agents/openai.yaml",
        description: "Optional agent runtime metadata for this skill.",
      },
    ],
  },
  {
    slug: "plan-mode",
    title: "plan-mode",
    category: "Planning",
    blurb: "Plan complex or risky work before editing.",
    lead:
      "A no-mutation planning workflow for gathering evidence, resolving ambiguity, and producing an approval-gated implementation plan.",
    overview:
      "Use this skill when work is complex, ambiguous, risky, or broad enough that premature edits would create churn or damage user intent. It keeps the agent in read-only discovery, asks focused clarification questions, names the likely files and validation path, and waits for explicit approval before handing off to execution.",
    bestFor: [
      "Planning multi-file implementation, architecture, routing, data-flow, or tradeoff-heavy work.",
      "Holding a strict boundary around dirty worktrees, migrations, settings, deployment, generated code, or other high-blast-radius surfaces.",
      "Creating concrete plans that include affected areas, ordered steps, validation, non-goals, and material risks.",
    ],
    workflow: [
      "Restate the objective and define the no-mutation planning boundary.",
      "Research only what is needed with read-only file, code, documentation, diagnostic, or subagent exploration.",
      "Ask early when missing decisions materially change the implementation.",
      "Present a concise plan with scope, files or modules, implementation sequence, validation, non-goals, and risks.",
      "Wait for approval before editing, staging, starting write-oriented tools, or otherwise changing the system.",
    ],
    outputs: [
      "A concrete approval-gated plan for the requested task.",
      "Focused clarification questions when ambiguity would change the plan.",
      "A clean handoff to execution after approval, including promised validation steps.",
    ],
    guardrails: [
      "Do not edit files, create files, stage commits, install packages, start services, or run write-oriented scripts while planning.",
      "Do not hide unresolved product, data, safety, or architecture assumptions inside the final plan.",
      "Do not treat approval of research as approval to implement unrelated cleanup.",
    ],
    entryPoints: [
      {
        label: "Workflow",
        path: "skills/plan-mode/SKILL.md",
        description: "Planning boundary, workflow, clarification rules, and handoff requirements.",
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
    blurb: "Debug runtime issues with an evidence-first logging workflow.",
    lead:
      "A prove-it debugging system for runtime bugs, regressions, flaky behavior, and unclear failures.",
    overview:
      "Use this skill when code reading is not enough. It forces hypotheses, logging, reproduction, root-cause notes, and post-fix verification before cleanup. The bundled collector can capture browser or app logs into NDJSON and expose a same-origin dashboard for live inspection, then final cleanup removes collector artifacts and the root-cause document unless evidence retention is requested.",
    bestFor: [
      "Frontend issues where browser logs need to reach an active collector directly.",
      "Runtime failures that are easy to guess about but hard to prove from static code.",
      "Flaky behavior that needs timestamped evidence and before/after comparison.",
    ],
    workflow: [
      "State precise hypotheses before instrumenting.",
      "Attach to an existing logging session or start the bundled collector.",
      "Add minimal temporary instrumentation tied to each hypothesis.",
      "Reproduce the issue, inspect the recorded log file, and mark hypotheses as confirmed, rejected, or inconclusive.",
      "Apply only proven fixes, then collect fresh post-fix logs before removing instrumentation.",
    ],
    outputs: [
      "A root-cause document that evolves during investigation and is deleted after successful final cleanup unless retained by request.",
      "Temporary instrumentation plus collector, log, and root-cause document cleanup.",
      "A verified fix backed by fresh runtime logs.",
    ],
    guardrails: [
      "Do not ship speculative fixes without runtime proof.",
      "Do not create app-local proxy APIs for browser logs unless direct collector delivery is proven blocked.",
      "Keep root-cause documents through intermediate log clears, then delete them during final successful cleanup unless the user asks to retain evidence.",
    ],
    entryPoints: [
      {
        label: "Workflow",
        path: "skills/debug/SKILL.md",
        description: "Evidence-first debugging sequence and cleanup requirements.",
      },
      {
        label: "Runtime reference",
        path: "skills/debug/references/runtime-debugging.md",
        description: "Collector bootstrap, log format, and debugging notes.",
      },
      {
        label: "Root-cause reference",
        path: "skills/debug/references/root-cause-document.md",
        description: "Structure for the evolving evidence document.",
      },
      {
        label: "Collector",
        path: "skills/debug/scripts/local_log_collector/",
        description: "Local NDJSON collector and dashboard implementation.",
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
      "A coverage-led audit for broken or degraded user journeys, changed defaults, stale data, and visible behavior changes.",
    overview:
      "Use this skill when a change set needs a user-visible behavior gate. It reviews a declared scope, separates intended visible changes from regressions, and writes a report that maps every touched surface to reviewed, intentional, not covered, or not relevant.",
    bestFor: [
      "Checking whether refactors or feature work broke user-facing flows.",
      "Auditing loading, error, permission, retry, ordering, export, email, or CLI-output changes.",
      "Producing a review artifact with severity tied to the strongest unresolved finding.",
    ],
    workflow: [
      "Set or infer the review scope and read requirements when available.",
      "Map touched user-visible surfaces before judging behavior.",
      "Compare current behavior against baseline, intent, and user expectations.",
      "Write all distinct findings, not only the top few.",
      "Record intentional visible changes and uncovered surfaces in the coverage ledger.",
    ],
    outputs: [
      "A Markdown regression-review report.",
      "A gate recommendation aligned to findings and coverage.",
      "A complete findings index and coverage ledger.",
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
      "Use this skill after a regression-review report or related PR feedback. It verifies every finding, intentional visible change, and coverage gap against the current code before editing, then fixes proven regressions and challenges stale or intentional findings with evidence.",
    bestFor: [
      "Re-checking a regression gate against the current diff and baseline.",
      "Fixing only proven user-visible regressions.",
      "Separating real regressions from intentional product changes.",
    ],
    workflow: [
      "Read the report and list every finding, intentional change, and uncovered surface.",
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
