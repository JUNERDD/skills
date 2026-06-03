---
name: mr
description: Use and maintain the `mr` Node CLI for CNB merge requests. Use when the user asks to create, preview, configure, troubleshoot, install, update, uninstall, or explain CNB merge requests with `mr`, `mrm`, `mrt`, or `mrp`; when handling MR branches named like `mr/target/current`, `git cnb pull create`, strategy flags `--merge`, `--rebase`, `--merge-target`, `--pr`, detached mode (`--detached`, `--no-detached`, `MR_DETACHED`, `mr.detached`), conflict resume, `--rm-mr`, `--dry-run`, diagnostics flags, or the `/Users/zen/Documents/mr` project that implements this CLI.
---

# MR CNB Merge Request

## Core Model

Use this skill to operate the `mr` CLI safely and to maintain its TypeScript implementation. The CLI prepares CNB merge requests for a current branch and target branch by either:

- Creating or updating `mr/<target>/<current>` and then running `git cnb pull create -H mr/<target>/<current> -B <target>`.
- Using `--pr` to push the current branch and run `git cnb pull create -H <current> -B <target>` directly.

Read `references/mr-cli-reference.md` when the user asks beyond a simple command lookup, including detached mode, conflict resume, install/update behavior, or implementation changes.

## Command Map

Targets:

```sh
mr                 # interactive picker: master / test / prerelease
mrm                # target master
mrt                # target test
mrp                # target prerelease
mr <target>        # arbitrary target branch
```

Common flags:

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
mr --config --global --strategy pr
mr --config --detached
mr --config --no-detached
mr --config --unset
mr --update
mr --uninstall
mr --version
```

## Operating Workflow

1. Confirm the repository context with `git status --short --branch` before running mutating MR commands.
2. Resolve the target branch from the command or user intent:
   - `mrm` or `mr master` targets `master`.
   - `mrt` or `mr test` targets `test`.
   - `mrp` or `mr prerelease` targets `prerelease`.
   - `mr <target>` supports arbitrary target branches.
3. If the user gives only an MR identifier, MR URL, or generic MR task and no source/current branch is clear from local or remote refs, clarify before mutating:
   - Which source/current branch to use or check out.
   - Which target branch to use, if not clear.
   - Whether to keep the existing `mr/<target>/<current>` branch or delete and rebuild it with `--rm-mr`.
   Ask the keep/delete question as its own yes/no decision. `--rm-mr` is opt-in only.
4. Prefer `mr <target> --dry-run` when the target, strategy, detached mode, or repository state is ambiguous. It prints the git/CNB plan without changing local branches, remote branches, or merge requests.
5. Run the real command only when the user requested creation/update or the task clearly requires it.

## Strategy And Config Rules

Use exactly one strategy:

- `merge` is the built-in default: start from the target branch and merge the current branch into `mr/<target>/<current>`.
- `rebase`: start from the current branch and rebase it onto the target branch.
- `merge-target`: start from the current branch and merge the target branch into it.
- `pr`: push the current branch and create the CNB PR directly, without an `mr/*` branch.

Strategy precedence is: command flag, `MR_STRATEGY`, local `git config mr.strategy`, global `git config --global mr.strategy`, legacy `mr.rebase`, built-in `merge`. Underscore input such as `merge_target` normalizes to `merge-target`.

Detached mode is orthogonal to strategy. Precedence is: `--detached` / `--no-detached`, `MR_DETACHED`, local `git config mr.detached`, global `git config --global mr.detached`, built-in `false`.

Do not combine strategy flags. Do not combine `--rm-mr` with `--pr`.

## Conflict And Resume Rules

Let the CLI own resume. Do not replace CLI resume with a manual `--pr` flow.

When `mr` stops for a merge or rebase conflict:

- Preserve the branch or worktree state where the CLI stopped.
- Run only read-only inspection unless the user explicitly asks you to resolve conflicts: `git status --short --branch`, `git branch --show-current`, and checks for `MERGE_HEAD` / `REBASE_HEAD`.
- Tell the user to resolve conflicts, run `git add <files>`, and then either ask you to continue or rerun the command shown by the CLI.
- Do not run `git add`, `git commit`, `git rebase --continue`, `git merge --continue`, aborts, resets, branch switches, pushes, or `git cnb pull create` unless the user explicitly asks for that exact operation.

After the user says conflict resolution is staged and asks you to continue, inspect status first. If the state matches the stopped operation, rerun the CLI resume command instead of inventing git steps:

- Inline default merge or rebase resume: `mr <target>` or the matching alias (`mrm`, `mrt`, `mrp`).
- Inline merge-target resume: `mr <target> --merge-target` or the matching alias plus `--merge-target`.
- Detached resume: run `mr <target> --detached` from the main repo, preserving the original strategy flag when it was `--rebase` or `--merge-target`.

Detached conflicts happen in a temporary worktree under `$TMPDIR/mr-worktrees/`. The main repo stays on the business branch. The user should resolve conflicts inside the reported worktree, run `git add <files>` there, then rerun `mr <target> --detached` from the main repo. The CLI resumes, pushes, creates/confirms the PR, and removes the worktree.

## Maintaining The Project

When editing `/Users/zen/Documents/mr`, preserve the existing TypeScript/Pastel/Ink/Zod structure. Run the narrowest relevant Vitest tests plus `npm run check` for behavior changes when feasible.

Before changing behavior, command semantics, workflow logic, branch strategy, user-facing output, or configuration, decide whether `/Users/zen/Documents/mr/README.md` must be updated. After any logic change, either update that README in the same change or explicitly state that it is unchanged because the change is internal-only.

Do not add skill-local README, changelog, or install guide files. Keep skill details in `SKILL.md` and `references/`.
