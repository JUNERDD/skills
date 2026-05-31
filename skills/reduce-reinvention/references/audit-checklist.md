# Audit Checklist

Use this reference for repo/org audits, pre-build discovery, and evidence gathering.

## Scope questions

- What capability is being requested or duplicated?
- Which repos, modules, teams, platforms, docs, or workflows are in scope?
- Is the goal to stop a new build, consolidate existing duplicates, create a catalog, or define governance?
- What constraints matter: performance, security, compliance, license, latency, team ownership, API compatibility, timeline, budget?
- What counts as success: fewer duplicated functions, fewer services, faster onboarding, lower support load, or fewer repeated decisions?

## Local discovery sequence

1. **Read manifests and docs.** Inspect package manifests, module files, README/AGENTS docs, ADRs, architecture docs, CI templates, Terraform modules, OpenAPI specs, GraphQL schemas, design-system docs, and runbooks.
2. **Search names and synonyms.** Search the user’s term plus domain synonyms, abbreviations, error messages, API paths, config keys, table names, UI labels, and business rules.
3. **Search by behavior.** Look for validation messages, SQL fragments, HTTP routes, event names, constants, copied comments, and test names—not only function names.
4. **Search by shape.** Scan for similar files, duplicate symbols, repeated dependencies, parallel folder structures, and near-identical tests.
5. **Map ownership and consumers.** Use CODEOWNERS, package metadata, service catalog files, commit history, imports, API clients, and deployment config.
6. **Separate evidence from interpretation.** A duplicate candidate is not a recommendation until domain semantics, change cadence, and owner readiness are checked.

## Useful local commands

Adapt commands to the environment and avoid destructive operations.

```bash
# Fast text search for behavior, names, and copy/fork signals
rg -n --hidden --glob '!{.git,node_modules,dist,build,target,venv,.venv}' \
  'duplicate|copied|forked|same as|TODO.*reuse|FIXME.*dedupe|重复|复制|复用|轮子' .

# Search manifests and likely reusable modules
find . -type f \( -name 'package.json' -o -name 'pyproject.toml' -o -name 'go.mod' \
  -o -name 'Cargo.toml' -o -name 'pom.xml' -o -name 'catalog-info.yaml' \
  -o -name 'CODEOWNERS' \) -print

# Search likely shared locations
find . -type d | rg '/(shared|common|utils|lib|packages|components|templates|modules)(/|$)'

# Run bundled scripts
python3 scripts/reinvention_audit.py . --output reinvention-audit.md
python3 scripts/reuse_catalog.py . --output reuse-catalog.md
```

## GitHub Code Search examples

Use these when the workspace is on GitHub or when cross-repo discovery is necessary:

```text
org:YOUR_ORG "exact error message or business rule"
org:YOUR_ORG (language:typescript OR language:python) "validatorName"
org:YOUR_ORG path:/src/**/*.ts "functionName"
org:YOUR_ORG "fatal error" NOT path:__testing__
org:YOUR_ORG /(?i)(duplicate|copied|forked|same as|reuse|dedupe)/
language:go symbol:WithContext org:YOUR_ORG
language:rust symbol:/^String::to_.*/ org:YOUR_ORG
```

## Duplicate classification rubric

| Finding | Evidence | Default action |
|---|---|---|
| Exact code/file copy | Same normalized file hash, comments, copied tests | Consolidate or document generated/vendor status |
| Near clone | Same structure with renamed symbols/constants | Compare semantics and change cadence |
| Same business rule | Same validation, pricing, entitlement, compliance rule | Extract source of truth or shared policy module |
| Overlapping service/API | Similar routes/events/schemas/SLAs | Evaluate merge, façade, or domain split |
| Repeated platform workflow | Similar CI/CD, IaC, observability setup | Create/update golden path/template |
| Duplicate docs/templates | Similar onboarding/runbook/process | Merge into authoritative source and redirect |
| Shadow fork | Local copy of external/internal asset with changes | Upstream, wrap, or create explicit fork policy |
| Justified divergence | Clear domain, compliance, latency, or ownership reason | Record ADR and review date |

## Evidence checklist for recommendations

Before recommending consolidation, gather:

- Existing asset path/repo/package/service and owner.
- Duplicate consumers and import/call paths.
- Similarity evidence: files, symbols, behavior, tests, docs, APIs.
- Differences that may be legitimate.
- Current test coverage and missing behavioral checks.
- Migration scope and compatibility risks.
- Security/license/dependency status when third-party assets are involved.
- Owner capacity and support model.
