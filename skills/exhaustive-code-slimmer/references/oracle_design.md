# Oracle design

A slimming oracle answers: “Does this changed repository still behave as required?” It is the gate for every deletion.

## Minimal oracle stack

Use as many layers as the repository supports:

1. **Build/install:** dependency install sanity, compile, bundle, package, container build.
2. **Type and static checks:** typecheck, lint rules that catch unreachable/unused code, schema validation, generated-code consistency.
3. **Unit/integration tests:** fast first; include integration tests for public APIs and persistence boundaries.
4. **Smoke tests:** CLI commands, server boot, health check, example requests, golden output checks.
5. **Contract checks:** API schemas, database migrations, protocol compatibility, public package exports.
6. **Runtime evidence:** coverage, production traces, route maps, feature-flag state, telemetry for dynamic code paths.
7. **Security/performance where relevant:** auth flows, permission checks, benchmark guardrails for hot paths.

## Oracle command examples

- JavaScript/TypeScript: `npm test && npm run typecheck && npm run lint`
- Python: `python -m pytest && python -m mypy . && ruff check .`
- Go: `go test ./... && go vet ./...`
- Rust: `cargo test && cargo clippy -- -D warnings`
- Java/Kotlin: `./gradlew test check` or `mvn test verify`

Adapt these to the repository. Do not invent unavailable commands; inspect package files first.

## Blind spots to call out

- Public APIs with no consumer tests.
- Reflection, dependency injection, dynamic imports, monkey-patching.
- Feature flags and environment-specific branches.
- Generated code and build-time plugins.
- Database migrations and data backfills.
- Cron jobs, queues, webhooks, serverless handlers.
- Error handling, fallback logic, compatibility shims.
- Tests that assert implementation details rather than behavior.

## Strengthening a weak oracle

- Add a small smoke test before deletion.
- Add characterization tests around legacy code before deleting nearby logic.
- Snapshot external outputs, CLI output, routes, API schemas, or serialized data.
- Run coverage and production/usage traces to distinguish untested from unused.
- Ask the user to classify feature flags, old migrations, public APIs, or deprecated modules as removable before deleting them.

## Extra oracle requirements for architecture refactors

Architecture changes need stronger coverage than local deletion because imports, boundaries, and developer workflows can change even when unit tests pass.

Add relevant checks before executing approved architecture slimming:

- Public API/export snapshots or route maps.
- Import-cycle checks or dependency-direction checks.
- Build graph/workspace checks.
- Framework boot smoke tests.
- Representative integration tests across moved boundaries.
- Typecheck/lint rules that catch stale imports and invalid exports.
- Test commands for packages affected by moved modules.

If these checks are unavailable, report the blind spot and keep the architecture refactor smaller.
