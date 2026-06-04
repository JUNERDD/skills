# Changelog

All notable changes to this skill collection are documented in this file.

This project uses SemVer for the collection version. GitHub release tags use the `vX.Y.Z` form.

## [0.2.2] - 2026-06-04

### Changed

- Reframed mr skill and catalog copy to keep the Git MR/PR CLI positioning while treating JUNERDD/mr as the underlying implementation repository.
- Removed hard-coded local mr checkout paths from mr skill maintenance guidance.
- Replaced fixed Signal labels on website skill detail lists with numeric markers.

## [0.2.1] - 2026-06-04

### Changed

- Added the mr skill for generic Git merge-request and pull-request workflows.
- Registered mr in the README and website catalog.
- Added automatic update-notice guidance for mr workflows.
- Added isolation guidance to multitask-coordinator.
- Clarified debug instrumentation budgets as guidance.

## [0.2.0] - 2026-05-31

### Changed

- Added plan-mode and reduce-reinvention skills to the collection.
- Expanded plan-mode with Cursor-style planning workflow guidance.
- Refined git-commit commit drafting rules.
- Added scoped behavior-graph guidance to regression-review and receiving-regression-review.
- Fixed debug collector dashboard detail scrolling for large payloads.

## [0.1.9] - 2026-05-19

### Changed

- Restored the collection behavior and public catalog to the `v0.1.6` state after the `v0.1.7` and `v0.1.8` releases performed poorly.
- Reverted the React wide API review skill additions and the AST-first exhaustive-code-slimmer updates from those releases.

## [0.1.6] - 2026-05-19

### Changed

- Updated the debug skill and bundled local log collector to distinguish dashboard auto-open from frontend page load.
- Added POST /api/dashboard-opened and POST /api/dashboard-open-failed plus MCP record_dashboard_open_failure for pre-reproduction fallback opens.

## [0.1.5] - 2026-05-15

### Changed

- Refined the multitask-coordinator skill around complex subagent work, shared contract ownership, atomic migrations, and evidence-backed synthesis.
- Updated the root README and website skill catalog to match the revised multitask-coordinator positioning.

## [0.1.4] - 2026-05-15

### Added

- Added the `exhaustive-code-slimmer` skill for approval-gated, behavior-preserving code reduction with DX-aware architecture checks.

### Changed

- Updated the root README and website skill catalog to include `exhaustive-code-slimmer`.

## [0.1.3] - 2026-05-14

### Added

- Added the `multitask-coordinator` skill for coordinating complex multi-step agent work, worker ownership boundaries, synthesis, and verification.
- Added root `AGENTS.md` repository instructions requiring README and website sync checks when project skills change.
- Added a CMS-ready content provider layer to the website while keeping the current in-repo skill catalog as the static provider.

### Changed

- Updated the root README and website skill catalog to include `multitask-coordinator`.
- Refactored website pages and components to consume skill content through provider APIs instead of importing the static catalog directly.

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
