# AST-first candidate generation

Use this reference when code-slimming claims depend on code structure rather than file size, duplicate bytes, or repository layout.

## Core rule

Prefer AST, language-server, parser, or repository-native static-analysis evidence over regex or text-search evidence for structural deletion claims.

Use text search, line-window duplicate detection, and bundled scripts as candidate generators, cross-checks, or fallback tools. Do not use them as final authority when AST or symbol-aware evidence is available for the same relationship. The behavior-preservation oracle still decides whether a candidate is accepted.

## Analysis preference

Use this order when code is available:

1. Type-aware AST or compiler symbol data.
2. Language-server references or repository-owned code-intelligence tools.
3. Syntax AST from a parser.
4. Repository-native static tools such as lint, typecheck, dead-code analyzers, dependency analyzers, and coverage reports.
5. Bundled heuristic scripts and targeted `rg` searches.
6. Manual inspection for parser-inaccessible or dynamic paths.

Do not install new parser dependencies, rewrite project configuration, or mutate generated files just to obtain AST access unless the user explicitly asks for that setup work.

## What AST should prove

AST or symbol-aware evidence is most useful for:

- unused imports, exports, variables, constants, functions, classes, methods, and type aliases
- symbol references, aliases, re-exports, wrappers, and call sites
- local function or class spans for `delete_span` or `replace_span` candidates
- unreachable branches after `return`, `throw`, constant conditions, or confirmed feature flags
- single-use wrappers, pass-through functions, needless adapters, and delegation chains
- import graph edges, dependency direction, cycles, fan-in, and fan-out
- duplicated function or method bodies after syntax normalization rather than raw line matching
- parameter deletion candidates together with all known call sites
- config/schema fields whose readers can be resolved statically

## Candidate evidence fields

When writing candidate JSONL, include evidence metadata when practical:

```json
{
  "id": "delete-symbol:src/example.ts:unusedHelper",
  "type": "delete_span",
  "path": "src/example.ts",
  "start_line": 42,
  "end_line": 57,
  "score": 240,
  "group": "src/example.ts",
  "reason": "unused_local_function",
  "evidence_mode": "AST-verified",
  "analysis_source": "typescript-compiler-api",
  "symbol": "unusedHelper",
  "node_kind": "FunctionDeclaration",
  "blind_spots": []
}
```

Use these `evidence_mode` values:

- `AST-verified`: parsed or language-server evidence directly proves the structural relationship.
- `AST-inferred`: AST proves nearby facts, but aliases, dynamic access, generated code, or partial type information require inference.
- `Static-tool-verified`: repository-native tools report the issue, such as compiler unused checks or dependency analyzers.
- `Inventory-verified`: repository inventory, file metrics, or hashing proves the candidate shape, such as empty files or byte-identical duplicates.
- `Text-fallback`: based on search or heuristic scripts because AST access was unavailable or insufficient.
- `Runtime/coverage-observed`: coverage, traces, or runtime instrumentation support the candidate.
- `Unknown / not covered`: candidate is plausible but not structurally proven.

## Fallback rules

When AST access is unavailable or incomplete:

- state the unavailable capability and use the strongest repository-native static tool before broad text search
- prefer narrow, named searches over repository-wide pattern guesses
- lower confidence for reflection, dynamic imports, plugin discovery, dependency injection, decorators, macros, generated code, computed property access, and public package APIs
- mark unresolved risk in the report and candidate metadata
- avoid claiming a public API, schema field, plugin entry point, migration, or compatibility shim is unused based only on a search miss

## Language notes

- JavaScript/TypeScript: prefer TypeScript Compiler API, language-server references, ESLint parser services, `ts-morph`, Babel, SWC, or project-owned analysis tools when already available.
- Python: use stdlib `ast` for imports, definitions, call sites, and branch structure; combine with ruff/pyright/mypy/vulture-style tools where available.
- Go: prefer `go list`, `go test`, `go vet`, `staticcheck`, and compiler package data.
- Rust: prefer `cargo check`, `cargo clippy`, rust-analyzer evidence, and feature-aware test matrices.
- Java/Kotlin/C#: prefer compiler/IDE symbol data and build-tool dependency analyzers; watch for reflection and dependency-injection wiring.
- C/C++/Swift: prefer compiler warnings, clang tooling or SourceKit when available; treat macros, conditional compilation, ABI, and generated bindings as high-risk blind spots.

## Reporting requirements

In the final slimming report, include:

- which analysis modes were used
- which candidate classes were AST-verified versus text-fallback
- where parser, language-server, type-resolution, macro, generated-code, or runtime blind spots remain
- whether accepted changes were proven only by the oracle or also by structural evidence
