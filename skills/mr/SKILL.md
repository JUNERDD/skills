---
name: mr
description: Use and maintain the `mr` Node CLI for generic Git MR/PR branch workflows. Use when the user asks to create, preview, configure, troubleshoot, install, update, uninstall, or explain MR/PR flows with `mr`, `mrm`, `mrt`, or `mrp`; when handling branches named like `mr/target/current`, strategy flags `--merge`, `--rebase`, `--merge-target`, `--pr`, default detached mode (`--detached`, `--no-detached`, `MR_DETACHED`, `mr.detached`), detached conflict worktree placement (`MR_WORKTREE_DIR`, `mr.worktreeDir`), request providers or commands (`MR_REQUEST_PROVIDER`, `mr.requestProvider`, `MR_REQUEST_COMMAND`, `mr.requestCommand`, CNB/GitHub/GitLab), automatic update notices (`MR_NO_UPDATE_CHECK`, `NO_UPDATE_NOTIFIER`), conflict resume, `--rm-mr`, `--dry-run`, diagnostics flags, or the upstream `JUNERDD/mr` implementation behind this CLI.
---

# MR Git Merge Request

## Core Model

Use this skill to operate the `mr` CLI safely. For implementation work, treat `JUNERDD/mr` as the upstream TypeScript project behind the CLI. The CLI prepares a merge-request or pull-request source for the current branch and a target branch by either:

- Creating or updating `mr/<target>/<current>`, pushing that branch, and then running the configured request command/provider when available.
- Using `--pr` to push the current branch directly as the request source.

If no request command/provider is available, the CLI still pushes the source branch and tells the user to create the request manually in the Git platform.

Detached mode is the built-in default. It keeps the main worktree on the current branch and usually does not require a clean tracked working tree. Traditional inline branch-switching mode is opt-in with `--no-detached`, `MR_DETACHED=false`, or `git config mr.detached false`.

Read `references/mr-cli-reference.md` when the user asks beyond a simple command lookup, including provider setup, detached mode, conflict resume, install/update behavior, or implementation changes.

## Command Map

Targets:

```sh
mr                 # interactive picker: master / test / prerelease
mrm                # target master
mrt                # target test
mrp                # target prerelease
mr <target>        # arbitrary target branch
```

Common workflow flags:

```sh
mr test --dry-run
mr test --rm-mr
mr test --pr
mr test --merge
mr test --rebase
mr test --merge-target
mr test --detached
mr test --no-detached
mr test --verbose
mr test --quiet
mr test --no-color
mr test --no-spinner
```

Maintenance and configuration:

```sh
mr --config
mr --config --show
mr --config --strategy rebase
mr --config --request-provider github
mr --config --request-provider none
mr --config --request-command 'gh pr create --fill --head "$MR_SOURCE_BRANCH" --base "$MR_TARGET_BRANCH"'
git config mr.worktreeDir .mr-worktrees
git config --global mr.worktreeDir .mr-worktrees
mr --config --global --strategy pr
mr --config --detached
mr --config --no-detached
mr --config --unset
mr --config --unset-request-command
mr --config --unset-request-provider
mr --update
mr --uninstall
mr --version
```

Environment controls:

```sh
MR_NO_UPDATE_CHECK=1 mr test
NO_UPDATE_NOTIFIER=1 mr test
MR_WORKTREE_DIR=.mr-worktrees mr test
```

## Operating Workflow

1. Before any task that requires executing `mr`, `mrm`, `mrt`, or `mrp`, check whether the CLI is installed with `command -v mr`.
   - If the command exists, continue.
   - If the user explicitly asked to install or update the CLI, run the official install/update flow directly.
   - If the command is missing for a create, preview, config, troubleshoot, or resume task, do not invent a manual Git replacement. Tell the user `mr` is not installed, show the install command, and ask whether to install it now.
   - If the user answers yes, install automatically with `curl -fsSL https://raw.githubusercontent.com/JUNERDD/mr/main/install.sh | bash`, verify with `mr --version`, then continue the original task if the repository state is still appropriate.
   - If the user declines, provide the manual install command and stop before running MR workflow commands.
2. Confirm the repository context with `git status --short --branch` before running mutating MR commands.
3. Resolve the target branch from the command or user intent:
   - `mrm` or `mr master` targets `master`.
   - `mrt` or `mr test` targets `test`.
   - `mrp` or `mr prerelease` targets `prerelease`.
   - `mr <target>` supports arbitrary target branches.
4. If the user gives only an MR identifier, MR URL, or generic MR task and no source/current branch is clear from local or remote refs, clarify before mutating:
   - Which source/current branch to use or check out.
   - Which target branch to use, if not clear.
   - Whether to keep the existing `mr/<target>/<current>` branch or delete and rebuild it with `--rm-mr`.
   Ask the keep/delete question as its own yes/no decision. `--rm-mr` is opt-in only.
5. Prefer `mr <target> --dry-run` when the target, strategy, detached mode, provider, or repository state is ambiguous. Dry-run prints the Git/request plan without mutating local branches, remote branches, or merge requests.
6. Run the real command only when the user requested creation/update or the task clearly requires it.

## Strategy, Detached, And Request Rules

Use exactly one strategy:

- `merge` is the built-in strategy default: start from the target/MR branch and merge the current branch into `mr/<target>/<current>`.
- `rebase`: start from the current branch and rebase it onto the target branch.
- `merge-target`: start from the current branch and merge the target branch into it.
- `pr`: push the current branch and handle the request directly, without an `mr/*` branch.

Strategy precedence is: command flag, `MR_STRATEGY`, local `git config mr.strategy`, global `git config --global mr.strategy`, legacy `mr.rebase`, built-in `merge`. Underscore input such as `merge_target` normalizes to `merge-target`.

Detached mode is orthogonal to strategy. Precedence is: `--detached` / `--no-detached`, `MR_DETACHED`, local `git config mr.detached`, global `git config --global mr.detached`, built-in `true`.

Detached conflict worktree root precedence is: `MR_WORKTREE_DIR`, local `git config mr.worktreeDir`, global `git config --global mr.worktreeDir`, built-in system temporary directory. Relative paths resolve from the repository root. To make conflict worktrees easier for VS Code/Cursor Source Control to find, prefer `git config mr.worktreeDir .mr-worktrees`; also check that VS Code `git.detectWorktrees` is enabled for externally-created worktrees. Current `mr` writes the nested directory to local `.git/info/exclude` so the main repository does not show `.mr-worktrees/` as untracked.

Request command/provider precedence is: `MR_REQUEST_COMMAND`, local `mr.requestCommand`, global `mr.requestCommand`, `MR_REQUEST_PROVIDER`, local `mr.requestProvider`, global `mr.requestProvider`, built-in `auto`. Custom request commands run through `sh -c` with `MR_SOURCE_BRANCH`, `MR_HEAD_BRANCH`, `MR_TARGET_BRANCH`, and `MR_BASE_BRANCH`.

Provider values are `auto`, `none`, `cnb`, `github`, and `gitlab`. `auto` detects CNB/GitHub/GitLab from `origin` only when the matching CLI is available (`git cnb`, `gh`, or `glab`). `none` disables request creation and leaves only pushed branches plus manual instructions.

Do not combine strategy flags. Do not combine `--rm-mr` with `--pr`.

## Update Notice Rules

Interactive TTY runs may print a non-blocking "new version available" panel to stderr before the command runs. Treat it as informational, not as command failure.

The update check:

- Uses the GitHub latest release API and a 24-hour cache under the user cache directory.
- Skips `--quiet`, CI, non-TTY output, help, version, `mr --update`, and `mr --uninstall`.
- Silently ignores network failures.
- Can be disabled with `MR_NO_UPDATE_CHECK=1` or `NO_UPDATE_NOTIFIER=1`.

## Conflict And Resume Rules

Let the CLI own resume. Do not replace CLI resume with a manual `--pr` flow.

When `mr` stops for a merge or rebase conflict:

- Preserve the branch or worktree state where the CLI stopped.
- Run only read-only inspection unless the user explicitly asks you to resolve conflicts: `git status --short --branch`, `git branch --show-current`, `git rev-parse -q --verify MERGE_HEAD`, `git rev-parse -q --verify REBASE_HEAD`, and `git worktree list --porcelain`.
- If the user expects the conflict worktree to appear in the IDE Source Control panel and it does not, check `mr --config --show`, `git config --get mr.worktreeDir`, `git worktree list --porcelain`, and VS Code `git.detectWorktrees`. For future runs, suggest `git config mr.worktreeDir .mr-worktrees` from the main repo plus enabling `git.detectWorktrees` so externally-created worktrees are scanned.
- For detached conflict worktrees, make the reported worktree usable before asking the user to resolve or before resolving there yourself: install project dependencies inside that worktree using the repo's locked package-manager command (`npm ci`, `corepack pnpm install --frozen-lockfile`, `corepack yarn install --immutable` or Yarn classic `yarn install --frozen-lockfile`, `bun install --frozen-lockfile`). Do not install in the main repo as a substitute, do not modify lockfiles, and stop if private registry credentials or system dependencies are missing.
- Tell the user to resolve conflicts, run `git add <files>`, and then either ask you to continue or rerun the command shown by the CLI.
- Do not run `git add`, `git commit`, `git rebase --continue`, `git merge --continue`, aborts, resets, branch switches, pushes, or request commands unless the user explicitly asks for that exact operation.

After the user says conflict resolution is staged and asks you to continue, inspect status first. If the state matches the stopped operation, rerun the CLI resume command instead of inventing Git steps:

- Detached default merge resume: `mr <target> --detached` from the main repo.
- Detached rebase resume: `mr <target> --detached --rebase` from the main repo.
- Detached merge-target resume: `mr <target> --detached --merge-target` from the main repo.
- Inline default merge or rebase resume: `mr <target> --no-detached` or the matching alias plus `--no-detached`, unless `mr.detached=false` was the original source of inline mode.
- Inline merge-target resume: `mr <target> --no-detached --merge-target` or the matching alias plus both flags.

Detached conflicts happen in the reported detached worktree: by default under `$TMPDIR/mr-worktrees/`, or under the configured `MR_WORKTREE_DIR` / `mr.worktreeDir` root. The main repo stays on the business branch. The user should install dependencies in the reported worktree when needed, resolve conflicts inside that worktree, run `git add <files>` there, then rerun the matching detached command from the main repo. The CLI resumes, pushes, handles the request, and removes the worktree.

## Maintaining The Project

When editing the CLI implementation, verify that the workspace is the `JUNERDD/mr` repository or a user-provided workspace for that repository; do not assume or record machine-specific absolute paths. Preserve the existing TypeScript/Pastel/Ink/Zod structure. Run the narrowest relevant Vitest tests plus `npm run check` for behavior changes when feasible.

Before changing behavior, command semantics, workflow logic, branch strategy, user-facing output, or configuration, decide whether `JUNERDD/mr`'s README must be updated. After any logic change, either update that README in the same change or explicitly state that it is unchanged because the change is internal-only.

Do not add skill-local README, changelog, or install guide files. Keep skill details in `SKILL.md` and `references/`.
