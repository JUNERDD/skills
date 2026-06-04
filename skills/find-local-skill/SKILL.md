---
name: find-local-skill
description: Find and select applicable local skills before analyzing or handling a user request, then apply the selected skill workflows. Use when the user asks to find, choose, inspect, route, or reason about available local skills; when a request explicitly says to check all local/available skills first; or when doing skill-aware requirement analysis, planning, or capability routing.
---

# Find Local Skill

## Core Rule

Do the work in this order:

1. Inventory available skills.
2. Select applicable skills for the current request.
3. Analyze the user's request using the selected skills.

Do not start requirement analysis before the skill inventory and selection pass is complete.

## Inventory

First use any skill list already present in the current session context. Then supplement it with the bundled local scan script when filesystem access is available:

```bash
python3 <path-to-this-skill>/scripts/list_agent_skills.py --format markdown
```

Replace `<path-to-this-skill>` with the loaded `find-local-skill` skill directory. Use `--query "<terms>"` to narrow the list only after the first broad pass. Use `--format json` when structured output is useful.

The script scans common local roots for `SKILL.md`, including user, project, Codex, Claude, and plugin-cache skill directories. If the user names another skill root, pass it with `--root <path>`.

## Selection

For each candidate skill, compare the user's request against:

- `name`
- `description`
- explicit user mentions such as `$skill-name`
- tool, file type, product, domain, and workflow cues

Select only skills that materially change how the work should be done. Avoid loading unrelated skill bodies. If a candidate is selected and its body has not already been provided, read its `SKILL.md` before relying on it.

If no skill matches, say that no suitable local skill was found and proceed with normal analysis.

## Analysis

After selection, analyze the request with the chosen skill order:

1. State the selected skill names and one short reason for each.
2. Apply their workflows in dependency order.
3. Then provide the actual requirement analysis, plan, or implementation guidance the user asked for.

Keep the skill-selection summary brief unless the user asks for a detailed audit.
