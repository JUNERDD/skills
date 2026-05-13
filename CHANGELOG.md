# Changelog

All notable changes to this skill collection are documented in this file.

This project uses SemVer for the collection version. GitHub release tags use the `vX.Y.Z` form.

## [0.1.2] - 2026-05-13

### Changed

- Updated the `debug` workflow so root-cause documents are kept during active investigation and intermediate log clears, then deleted during final successful cleanup unless evidence retention is requested.
- Extended the debug MCP server `stop_debug_session` tool with an optional root-cause document path for final cleanup.
- Synchronized the website collection version and debug skill copy for the new cleanup behavior.

## [0.1.1] - 2026-05-07

### Fixed

- Fixed the `debug` local log collector dashboard auto-open path to prefer platform launchers before falling back to Python's `webbrowser` helper.
- Added coverage for dashboard launcher selection, platform opener failure reporting, and fallback behavior.

## [0.1.0] - 2026-05-06

Initial public collection release.

### Added

- Published the repository-level `VERSION` file as the source of truth for the collection version.
- Documented the collection versioning model in `README.md`.
- Included the current skill collection: `comment-strategist`, `debug`, `git-commit`, `grill-me`, `hack-review`, `receiving-hack-review`, `receiving-regression-review`, `regression-review`, and `split-commits`.
- Included runtime support assets for the `debug` skill, including the local log collector and MCP server package.
- Included review-consumption workflows with explicit Git staging guardrails for receiving review reports.
