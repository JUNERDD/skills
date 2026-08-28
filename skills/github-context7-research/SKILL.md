---
name: github-context7-research
description: Reconcile current or version-specific third-party library documentation from Context7 with read-only GitHub evidence from source, types, tests, examples, releases, issues, pull requests, and commits. Use when implementing against an external library, SDK, or framework; diagnosing behavior the docs do not fully explain; checking whether an API changed; or asking how an open-source dependency actually works. Do not use for ordinary questions about the current repository that need no external library evidence.
---

# GitHub + Context7 Research

Answer third-party library questions by separating the supported public contract from the implementation evidence behind it. Context7 establishes what users are meant to call; GitHub explains how the matched release behaves and why.

## Evidence workflow

1. **Freeze identity and version.** Identify the package or product, the user's exact question, the canonical repository, and the target version. Prefer an explicit user version, then the consuming project's manifest or lockfile. If none exists, mark the investigation as current and unpinned.
2. **Establish the public contract with Context7.** Use a supplied Context7 library ID directly. Otherwise resolve the library name with the concrete question, select the result by package identity, source reputation, coverage, and version match, then query only the documentation needed for the question. Record the selected library ID and version.
3. **Match GitHub to the same release.** Prefer the tag or immutable commit corresponding to the target package version. If no trustworthy mapping exists, state that before using the default branch; never silently compare versioned docs with unrelated HEAD source.
4. **Collect the narrowest decisive repository evidence.** Start with exact symbols, imports, error text, or configuration keys. Inspect public exports and types, then implementation, tests, and examples. Add releases, changelogs, commits, pull requests, or issues only when they explain a behavior or version change.
5. **Reconcile instead of blending.** State whether the documentation and repository evidence agree. Treat documented public APIs as the supported usage contract. Treat internal helpers as implementation details, tests as behavior evidence for their exact ref, and issues or pull requests as historical context unless the referenced change is released.
6. **Answer at the user's requested level.** Give the direct recommendation first, then enough versioned evidence to make the conclusion auditable. If code is requested, implement against the supported public API unless the user explicitly accepts an internal or temporary workaround.

Context7 tools may be namespaced by the host. Use the equivalents of `resolve-library-id` and `query-docs`; if the prompt already contains an exact `/org/project` or versioned Context7 ID, skip resolution. GitHub tool names also vary by enabled toolset, so select read-only code search, file-content, commit, release, issue, and pull-request capabilities by purpose rather than assuming a fixed prefix.

## Evidence depth

| Question | Context7 anchor | GitHub follow-up |
| --- | --- | --- |
| Correct API or configuration | Current or requested-version public docs | Public exports, types, and official examples at the matching ref |
| Unexpected runtime behavior | Documented contract and caveats | Implementation path plus focused tests at the matching ref |
| Regression or version change | Both versions' relevant docs when available | Tags, diff or commits, release notes, and the merged pull request |
| Suspected bug or workaround | Supported usage and documented limitations | Reproduction test, implementation, and relevant issue or pull request status |

Do not broaden into repository archaeology once the evidence already resolves the question.

## Reporting contract

Include the following when they materially affect the answer:

- the package version or unpinned status, Context7 library ID, and GitHub repository ref or commit;
- the public documentation claim and the source or test evidence that confirms, narrows, or contradicts it;
- direct links or stable identifiers for decisive docs, files, lines, commits, pull requests, and issues;
- any mismatch, unresolved version mapping, missing dependency, or inference, with calibrated confidence;
- a clear distinction between supported public usage, observed implementation behavior, and a proposed workaround.

## Boundaries

- Use GitHub MCP only for read-only research. Do not create or edit repository content, issues, pull requests, releases, workflows, or commits under this skill. A separate explicit user request is required for any mutation.
- Never send credentials, private source, proprietary identifiers, or personal data in a Context7 query. Keep queries limited to public library names and the minimum technical question.
- Do not use source visibility to recommend private, generated, deprecated, compatibility, test-only, or feature-flagged APIs as public interfaces.
- If Context7 or GitHub MCP is unavailable, continue with the evidence that is available and explicitly mark combined verification incomplete. Never fill the missing half from memory while claiming it was verified.
