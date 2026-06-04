---
name: find-local-skill
description: Decompose a user request into deliverables, workflow phases, tools, domains, and implicit prerequisites, then find and select applicable local skills from Cursor, Claude Code, OpenCode, Codex, and shared Agent Skills roots before analyzing or handling the request. Use when the user asks to find, choose, inspect, route, or reason about available local skills; when a request explicitly says to check all local/available skills first; or when doing skill-aware requirement analysis, planning, or capability routing where deeper request understanding is needed before skill selection.
---

# Find Local Skill

## Core Rule

Do the work in this order:

1. Decompose the user's request into skill-search facets.
2. Inventory available skills.
3. Run supplemental searches for decomposed facets when needed.
4. Select applicable skills for the current request.
5. Analyze the user's request using the selected skills.

Do not start solution analysis before the decomposition, inventory, and selection pass is complete.

## Request Decomposition

Before inventorying skills, build a compact scratch decomposition of the request. Use it to search and select skills; do not turn it into a long user-facing analysis unless the user asked for one.

Extract these facets:

- Explicit asks: verbs such as write, design, create, implement, review, audit, debug, deploy, summarize, or commit.
- Deliverables: PRD, requirements, UX spec, design brief, Figma design, prototype, code, test, report, document, spreadsheet, slide deck, or PR.
- Artifacts and tools: file types, screenshots/images, URLs, Figma, browser, GitHub, Linear, Vercel, Lark, iOS, web, local repo, or APIs.
- Workflow phases: discovery, requirement clarification, product/design brief, ideation, UI design, implementation, verification, publication, or handoff.
- Implicit prerequisites: steps not explicitly named but required by the ask, such as using a product-design brief before a Figma/prototype workflow, or selecting document tooling before producing a `.docx`.
- Synonyms and neighboring terms: expand terse terms into likely skill vocabulary, such as "PRD" -> requirements/product brief/spec, "UX" -> product flow/design/audit/accessibility, and "Figma" -> design/prototype/screen/component.

If the request contains multiple phases, preserve the dependency order. A later phase can imply earlier skills even when the user only names the final output.

## Inventory

First use any skill list already present in the current session context. Then supplement it with the bundled local scan script when filesystem access is available:

```bash
python3 <path-to-this-skill>/scripts/list_agent_skills.py --format markdown
```

Replace `<path-to-this-skill>` with the loaded `find-local-skill` skill directory. Use `--query "<terms>"` to narrow the list only after the first broad pass. Use `--format json` when structured output is useful.

The script scans common local roots for `SKILL.md` across Cursor, Claude Code, OpenCode, Codex, and shared Agent Skills directories:

- Codex: `~/.codex/skills/`, project `.codex/skills/`, and `~/.codex/plugins/cache/`
- Claude Code: `~/.claude/skills/`, project `.claude/skills/`, and `~/.claude/plugins/cache/`
- Cursor: `~/.cursor/skills/`, `~/.cursor/skills-*`, and project `.cursor/skills/`
- OpenCode: `~/.config/opencode/skills/`, `~/.config/opencode/plugins/`, and project `.opencode/skills/`
- Shared Agent Skills roots used by these hosts: `~/.agents/skills/` and project `.agents/skills/`
- Plain project skill collections: `skills/` in the current directory or any parent directory

Plugin skills are reported with a namespace when the scanner can identify the plugin manifest, such as `product-design:index` or `figma:figma-use`. If the user names another skill root, pass it with `--root <path>`.

## Supplemental Search

After the broad inventory, use the decomposition facets to avoid shallow keyword matching:

- Run focused follow-up queries for individual facets or tight synonym groups, such as `--query figma`, `--query design`, or `--query docx`.
- Do not put unrelated facets into one long query. The scanner matches all query terms, so `--query "prd ux figma design"` may hide relevant skills that match only one phase.
- Search for upstream or prerequisite skills, not just the final output skill. For example, a request to write a PRD and then create a Figma screen should search product/requirements/design-brief terms as well as Figma terms.
- If a plugin or skill has an index/router skill for a domain, inspect that skill when the decomposed request enters the domain and the broad inventory suggests it may route to more specific skills.
- Prefer namespaced plugin entries, such as `product-design:index`, over similarly named plain skills like `index` when the path shows the request belongs to that plugin domain.

## Selection

For each candidate skill, compare the user's request against:

- `name`
- `description`
- explicit user mentions such as `$skill-name`
- tool, file type, product, domain, and workflow cues
- decomposed deliverables, workflow phases, synonyms, and implicit prerequisites

Select only skills that materially change how the work should be done. Avoid loading unrelated skill bodies. If a candidate is selected and its body has not already been provided, read its `SKILL.md` before relying on it.

Before finalizing selection, perform a gap check: every explicit deliverable and important implicit prerequisite should either have a selected skill, be intentionally handled by normal Codex behavior, or be noted as having no suitable local skill. Do not select only this routing skill when a deeper workflow skill materially governs part of the task.

If no skill matches, say that no suitable local skill was found and proceed with normal analysis.

## Analysis

After selection, analyze the request with the chosen skill order:

1. State the selected skill names and one short reason for each. Include a compact decomposition summary only when it explains a non-obvious skill choice.
2. Apply their workflows in dependency order.
3. Then provide the actual requirement analysis, plan, or implementation guidance the user asked for.

Keep the skill-selection summary brief unless the user asks for a detailed audit.
