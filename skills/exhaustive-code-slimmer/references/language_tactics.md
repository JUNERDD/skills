# Language tactics

Use repository-native tools first. These are prompts for inspection, not mandatory commands.

## JavaScript / TypeScript

- Inspect `package.json`, lockfiles, `tsconfig`, bundler config, framework routes.
- Static checks: TypeScript `noUnusedLocals` / `noUnusedParameters`, ESLint unused imports, dependency checkers.
- Watch for dynamic imports, barrel exports, framework file-based routes, serverless functions, decorators, and plugin config.
- Candidate classes: unused dependencies, unused exports, duplicate components, wrapper hooks, stale feature flags, dead route files.

## Python

- Inspect `pyproject.toml`, `setup.cfg`, `requirements*`, package entry points, imports, CLI scripts.
- Static checks: ruff/flake unused imports, pyright/mypy, vulture-style dead-code discovery.
- Watch for reflection, dynamic imports, plugin discovery, decorators, monkey-patching, tests importing private helpers.
- Candidate classes: unused modules, single-use wrappers, duplicate fixtures, old CLI commands, dead optional dependency paths.

## Go

- Inspect `go.mod`, build tags, generated files, command packages.
- Static checks: `go test ./...`, `go vet ./...`, `staticcheck` when available.
- Watch for build tags, reflection, init side effects, code generation, public exported API.
- Candidate classes: unused packages, dead commands, obsolete build tags, duplicate helpers, unnecessary interfaces.

## Rust

- Inspect `Cargo.toml`, features, workspaces, build scripts.
- Static checks: `cargo test`, `cargo clippy`, feature-matrix tests when features exist.
- Watch for feature flags, macros, build.rs, public crates, unsafe code, serialization contracts.
- Candidate classes: unused features, obsolete modules, wrapper traits, dead examples/benches.

## Java / Kotlin

- Inspect Maven/Gradle files, generated sources, annotations, reflection, DI container config.
- Static checks: test/check tasks, dependency analysis plugins, IDE/compiler unused warnings.
- Watch for Spring/Guice reflection, annotations, service loaders, XML/YAML wiring, public libraries.
- Candidate classes: unused beans, duplicate DTO mappers, stale modules, dead endpoints, obsolete test fixtures.

## C / C++

- Inspect build system, compile flags, generated headers, platform guards.
- Static checks: compiler warnings, clang-tidy when available, tests under configured flags.
- Watch for macros, conditional compilation, ABI, undefined behavior, generated bindings, platform-specific code.
- Candidate classes: dead platform branches, duplicate utilities, unused static functions, obsolete flags.
