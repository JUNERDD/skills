---
name: git-commit
description: Draft a Conventional Commit message from the currently staged Git changes. Use when the user wants a commit message suggestion, asks to summarize staged work into a commit, or needs a Conventional Commit subject/body without actually running `git commit`. This skill must only inspect staged changes and must not stage files, inspect unstaged work, or create the commit.
---

# Git Commit

Draft a Conventional Commit message from the staged diff only. Return the proposed message text, but never run `git commit`.

## Workflow

1. Check whether there are staged changes.

```bash
git status --short
git diff --cached --stat
git diff --cached
```

If nothing is staged, stop and tell the user to stage the intended files first. Do not fall back to `git diff`.

2. Build a deep, recursive understanding of the staged code changes before classifying them.

- Trace each staged hunk through the surrounding code, tests, configuration, docs, API contracts, and generated artifacts when that context is necessary to understand the actual change.
- Keep the analysis grounded in `git diff --cached`; do not inspect unstaged work to fill gaps.
- If the staged diff cannot support a confident message, say what is unclear instead of guessing.

3. Infer the commit type from the staged diff.

- `feat`: new user-facing capability
- `fix`: bug fix or regression fix
- `docs`: documentation-only change
- `style`: formatting or non-behavioral style change
- `refactor`: internal code restructuring without behavior change
- `perf`: performance improvement
- `test`: test-only addition or update
- `build`: build tooling or dependency change
- `ci`: CI workflow or automation change
- `chore`: maintenance work that does not fit the types above

4. Infer the scope only when it is obvious from the staged paths or module names.

- Good scopes are short and specific, such as `auth`, `search`, `web`, or `extension`.
- Omit the scope when it is ambiguous.

5. Draft the message.

- Use the Conventional Commit subject format: `<type>[optional scope]: <description>`
- Keep the subject in imperative mood and present tense.
- Keep the subject under 72 characters.
- Keep the description factual and grounded in the staged diff.
- Add a concise body description when it is necessary to clarify the staged change beyond the subject.
- Do not invent motivations, side effects, or files that are not visible in the staged changes.
- Add `!` or a `BREAKING CHANGE:` footer only when the staged diff clearly shows a breaking change.
- Do not add an emoji prefix unless the user explicitly asks for one.

## Output Rules

- Default to one best commit message, not multiple options.
- Output only the final commit message text.
- Do not prefix the answer with explanations, bullets, labels, or `git commit -m`.
- Do not wrap the message in quotes or code fences unless the user asks.
- Add a body description or footer only when it materially helps explain the change, breaking impact, migration step, or issue reference.

Example single-line output:

`fix(auth): handle expired session refresh`

## Safety

- Never run `git add`, `git restore`, `git reset`, `git commit`, or `git commit --amend`.
- Never inspect unstaged changes with `git diff` or other working tree fallbacks.
- If the staged changes mix unrelated concerns, tell the user to split the commit instead of forcing one misleading message.
- If staged paths or diff content suggest secrets, such as `.env`, credentials, or private keys, warn the user before proposing a message.
