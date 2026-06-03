# MR CLI Reference

## Contents

- [Command Surface](#command-surface)
- [Availability Preflight](#availability-preflight)
- [Branch And Request Semantics](#branch-and-request-semantics)
- [Strategy Details](#strategy-details)
- [Detached Mode](#detached-mode)
- [Configuration](#configuration)
- [Conflict And Resume](#conflict-and-resume)
- [Diagnostics And Output](#diagnostics-and-output)
- [Install, Update, Uninstall](#install-update-uninstall)
- [Project Maintenance](#project-maintenance)

## Command Surface

`mr` is a Node CLI for generic Git merge-request and pull-request workflows. It is implemented with Pastel, Ink, React, Zod, TypeScript, and a small Git/request runner layer.

Core target commands:

```sh
mr                         # interactive target picker: master / test / prerelease
mr master
mr test
mr prerelease
mrm                        # target master
mrt                        # target test
mrp                        # target prerelease
mr <target>                # arbitrary target branch
```

Workflow flags:

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
mr test --color
mr test --no-color
mr test --no-spinner
```

Maintenance and config commands:

```sh
mr --config
mr --config --show
mr --config --strategy rebase
mr --config --local --strategy merge-target
mr --config --global --strategy pr
mr --config --request-provider github
mr --config --request-provider none
mr --config --request-command 'gh pr create --fill --head "$MR_SOURCE_BRANCH" --base "$MR_TARGET_BRANCH"'
mr --config --detached
mr --config --no-detached
mr --config --global --detached
mr --config --unset
mr --config --unset-request-command
mr --config --unset-request-provider
mr --update
mr --uninstall
mr --version
mr -h
mr -help
mr --help
```

`mr config`, `mr update`, and `mr uninstall` remain valid target-branch invocations. Use the `--config`, `--update`, and `--uninstall` flags for maintenance.

`--detached` and `--no-detached` are orthogonal modifiers. They work on MR workflows and also work with `mr --config` to write the default.

## Availability Preflight

Before running an MR workflow, config, resume, update, uninstall, or diagnostic command that depends on the installed CLI, check:

```sh
command -v mr
```

If `mr` is installed, use the normal command flow.

If `mr` is missing:

- For an explicit install request, run the official installer and verify with `mr --version`.
- For create, preview, config, troubleshoot, or resume requests, do not substitute hand-written Git commands for the CLI workflow. Tell the user the CLI is missing, show the installer command, and ask whether to install it now.
- If the user answers yes, install automatically, verify with `mr --version`, then continue the original task when the repository state still matches the requested operation.
- If the user declines, stop before running MR workflow commands and leave the manual install command.

Install command:

```sh
curl -fsSL https://raw.githubusercontent.com/JUNERDD/mr/main/install.sh | bash
```

If `mr` exists but an alias such as `mrt` is missing, prefer the equivalent `mr test` form for the current task and suggest reinstalling only if the user wants the aliases restored.

## Branch And Request Semantics

Generated MR branches use:

```text
mr/<target>/<current>
```

Request creation is optional and provider-driven. After the CLI pushes the source branch, it resolves a request command from `MR_REQUEST_COMMAND`, `mr.requestCommand`, or a provider preset. If no request command is available, it does not fail the workflow; it prints the pushed source branch and asks the user to create the merge request manually.

For MR-branch strategies, `<source>` is `mr/<target>/<current>`. For `--pr`, `<source>` is the current branch.

Before real execution, the CLI verifies Git context, resolves strategy and detached mode, fetches `origin/<target>`, checks whether the current branch is already merged into the target, and skips request handling when no work is needed.

Inline MR-branch strategies require a clean tracked working tree. Detached mode intentionally does not. The `pr` strategy pushes the current branch directly and follows the direct branch path, including the clean tracked working-tree guard.

Remote MR branch checks use exact `refs/heads/<branch>` matching. A branch that only suffix-matches `mr/<target>/<current>` must not be treated as the MR branch. If the remote MR branch disappears between checking and fetching, the CLI treats it as absent and recreates or regenerates it.

When a remote MR branch already exists, the CLI reuses it when that is safe:

- `merge` can reuse the existing MR branch, merge the current branch, sync the target branch, push, and handle the request.
- `rebase` can skip rebuilding when the existing MR branch already represents the current branch's equivalent replayed changes on the target.
- `merge-target` can skip rebuilding when the existing MR branch already contains both current and target.

`--rm-mr` deletes `origin/mr/<target>/<current>` first and then rebuilds using an MR-branch strategy. It is invalid with `--pr`.

If a configured request command fails, the CLI warns but does not undo the pushed branch. Treat the source branch as ready and report that request creation needs follow-up.

## Strategy Details

Use one strategy per run.

### merge

Built-in strategy default.

Detached happy path:

1. Fetch `origin/<target>`.
2. Create the remote MR branch from `origin/<target>` when needed.
3. Use Git plumbing (`merge-tree`, `commit-tree`) to merge the current branch and then `origin/<target>` without switching local `HEAD`.
4. Push the resulting commit to `mr/<target>/<current>`.
5. Run the configured request command/provider, or print manual request instructions.

Inline mode (`--no-detached` or effective `mr.detached=false`):

1. Fetch `origin/<target>`.
2. Create or reuse `origin/mr/<target>/<current>`.
3. Switch local `mr/<target>/<current>` from the remote MR branch or `origin/<target>`.
4. Merge the current branch into the MR branch.
5. Merge `origin/<target>` into the MR branch to sync the target.
6. Push `HEAD:mr/<target>/<current>`.
7. Run the configured request command/provider, or print manual request instructions.
8. Switch back to the original current branch.

### rebase

1. Fetch `origin/<target>`.
2. Start `mr/<target>/<current>` from the current branch. Detached mode performs this in a temporary worktree.
3. Compute the merge base between `origin/<target>` and the current branch.
4. Rebase the MR branch onto `origin/<target>`.
5. Push with `--force-with-lease --set-upstream`.
6. Run the configured request command/provider, or print manual request instructions.
7. In inline mode, switch back to the original current branch.

### merge-target

1. Fetch `origin/<target>`.
2. Start from the current branch.
3. Merge `origin/<target>` into the MR content. Detached happy path uses plumbing; conflicts fall back to a temporary worktree.
4. Push `mr/<target>/<current>` with `--force-with-lease --set-upstream`.
5. Run the configured request command/provider, or print manual request instructions.
6. In inline mode, switch back to the original current branch.

### pr

1. Fetch `origin/<target>`.
2. Push the current branch with upstream.
3. Run the configured request command/provider from current branch to target, or print manual request instructions.

## Detached Mode

Detached mode is the built-in default. It is enabled by `--detached`, `MR_DETACHED=true`, `git config mr.detached true`, or no detached config at all.

Behavior:

- The main worktree stays on the business branch.
- MR-branch strategies do not require tracked working-tree cleanliness.
- `pr` behaves like direct current-branch request creation; it has no local branch switching to avoid.
- Happy-path `merge` and `merge-target` use Git plumbing (`merge-tree`, `commit-tree`, and pushing the resulting object) to update `mr/<target>/<current>` without switching local `HEAD`.
- `rebase` and conflicted merge/merge-target paths use a temporary Git worktree under `$TMPDIR/mr-worktrees/`.
- Re-running the same detached command from the main repo detects an unresolved leftover worktree, resumes the merge or rebase there, pushes the MR branch, handles the request, and removes the worktree.

Detached resume command examples:

```sh
mr test --detached
mr test --detached --rebase
mr test --detached --merge-target
```

If the user resolved conflicts inside the worktree but forgot `git add`, the CLI reports the unmerged paths and asks for `git add` before retrying.

Use `--no-detached`, `MR_DETACHED=false`, or `git config mr.detached false` only when the user intentionally wants the traditional local branch-switching workflow.

## Configuration

Strategy values:

```text
pr
merge
rebase
merge-target
```

Underscore input such as `merge_target` normalizes to `merge-target`.

Strategy precedence from highest to lowest:

1. Command flag: `--pr`, `--merge`, `--rebase`, `--merge-target`
2. `MR_STRATEGY=pr|merge|rebase|merge-target`
3. Local Git config: `git config mr.strategy ...`
4. Global Git config: `git config --global mr.strategy ...`
5. Legacy `git config --bool mr.rebase`
6. Built-in `merge`

Detached values are booleans. Accepted environment/config forms include `true`, `false`, `1`, `0`, `yes`, `no`, `on`, and `off`.

Detached precedence from highest to lowest:

1. Command flag: `--detached`, `--no-detached`
2. `MR_DETACHED=true|false|1|0`
3. Local Git config: `git config mr.detached true|false`
4. Global Git config: `git config --global mr.detached true|false`
5. Built-in `true`

Request provider values:

```text
auto
none
cnb
github
gitlab
```

Provider preset commands:

```sh
git cnb pull create -H "$MR_SOURCE_BRANCH" -B "$MR_TARGET_BRANCH"
gh pr create --fill --head "$MR_SOURCE_BRANCH" --base "$MR_TARGET_BRANCH"
glab mr create --fill --source-branch "$MR_SOURCE_BRANCH" --target-branch "$MR_TARGET_BRANCH"
```

`auto` detects the host from `remote.origin.url` and only uses a preset when the matching command is available:

- CNB remote plus `git cnb`
- GitHub remote plus `gh`
- GitLab remote plus `glab`

`none` disables request commands. The CLI still pushes the source branch and prints manual request instructions.

Custom request commands override provider presets. They run through `sh -c` and receive:

```text
MR_SOURCE_BRANCH / MR_HEAD_BRANCH
MR_TARGET_BRANCH / MR_BASE_BRANCH
```

Request command/provider precedence from highest to lowest:

1. `MR_REQUEST_COMMAND='...'`
2. Local Git config: `git config mr.requestCommand '...'`
3. Global Git config: `git config --global mr.requestCommand '...'`
4. `MR_REQUEST_PROVIDER=auto|none|cnb|github|gitlab`
5. Local Git config: `git config mr.requestProvider ...`
6. Global Git config: `git config --global mr.requestProvider ...`
7. Built-in `auto`

Examples:

```sh
git config --global mr.requestProvider github
git config --global mr.requestProvider gitlab
git config --global mr.requestProvider cnb
git config --global mr.requestProvider none
git config --global mr.requestCommand 'gh pr create --fill --head "$MR_SOURCE_BRANCH" --base "$MR_TARGET_BRANCH"'
git config --global mr.requestCommand 'glab mr create --fill --source-branch "$MR_SOURCE_BRANCH" --target-branch "$MR_TARGET_BRANCH"'
git config --global mr.requestCommand 'git cnb pull create -H "$MR_SOURCE_BRANCH" -B "$MR_TARGET_BRANCH"'
```

`mr --config` is interactive when no script-friendly option is supplied. In scripts, use `--show`, `--strategy`, `--request-provider`, `--request-command`, `--detached`, `--no-detached`, `--global`, `--local`, `--unset`, `--unset-request-command`, or `--unset-request-provider`.

`mr --config --show` prints the effective strategy, detached mode, provider, request command, local values, and global values.

`mr --config --unset` clears only `mr.strategy` and `mr.detached` in the selected scope. It does not clear request config. Use `--unset-request-command` or `--unset-request-provider` for request settings.

## Conflict And Resume

The CLI has explicit resume paths. Let those paths run after the user finishes manual conflict resolution; do not replace them with hand-written Git commits or a manual `--pr` shortcut.

### Detached conflicts

Detached mode is default. The main repo remains on the business branch. The CLI reports a worktree path under `$TMPDIR/mr-worktrees/`.

Handoff to the user:

```sh
cd <reported-worktree>
# resolve files
git add <files>
cd <main-repo>
mr <target> --detached
```

Preserve the original strategy flag when it was `--rebase` or `--merge-target`:

```sh
mr <target> --detached --rebase
mr <target> --detached --merge-target
```

On resume, the CLI checks unresolved paths, continues merge/rebase inside the worktree, pushes the MR branch, handles the request, removes the worktree, and reports that the main repo stayed on the business branch.

### Inline merge conflicts

Inline mode means the original run used `--no-detached`, `MR_DETACHED=false`, or `mr.detached=false`. The CLI stops on `mr/<target>/<current>` with `MERGE_HEAD` active.

Handoff to the user:

```sh
git status --short --branch
# resolve files
git add <files>
mr <target> --no-detached
```

If inline mode came from persistent config (`mr.detached=false`), the explicit `--no-detached` flag is not required but is still safe.

On resume, the CLI checks for unmerged files, runs `git commit --no-edit`, pushes `mr/<target>/<current>`, handles the request, and switches back to `<current>`.

### Inline rebase conflicts

The CLI stops in an active rebase for `mr/<target>/<current>`; `git branch --show-current` may be empty.

Handoff to the user:

```sh
git status --short --branch
# resolve files
git add <files>
mr <target> --no-detached --rebase
```

On resume, the CLI checks for unmerged files, runs `git -c core.editor=true rebase --continue`, pushes with force-with-lease, handles the request, and switches back to `<current>`.

### Inline merge-target conflicts

The CLI stops on `mr/<target>/<current>` with `MERGE_HEAD` active.

Handoff to the user:

```sh
git status --short --branch
# resolve files
git add <files>
mr <target> --no-detached --merge-target
```

Preserve the `--merge-target` flag on resume.

Allowed agent inspection after a stopped run:

```sh
git status --short --branch
git branch --show-current
git rev-parse -q --verify MERGE_HEAD
git rev-parse -q --verify REBASE_HEAD
git worktree list --porcelain
```

Avoid mutating recovery commands unless the user explicitly asks for that exact action. This includes `git add`, `git commit`, `git rebase --continue`, `git merge --continue`, `git merge --abort`, `git rebase --abort`, `git reset`, `git switch`, `git push`, and request commands.

For non-conflict failures in inline mode, the CLI attempts to restore the initial branch and appends manual recovery instructions if restoration fails.

## Diagnostics And Output

Use `--dry-run` to print the planned Git/request commands without mutating local branches, remote branches, or merge requests. Detached dry-run says that it will not switch local branches and may use a temporary worktree on conflict. If tracked files are dirty, dry-run still prints the plan and warns when real execution would stop first.

Use `--verbose` for executed commands and full output. `DEBUG=mr` is equivalent to verbose. Without verbose, failed command output is compacted and the CLI suggests adding `--verbose`.

Use `--quiet` for errors only. Use `--no-color` or `MR_NO_COLOR=1` for plain logs. `NO_COLOR`, `MR_NO_COLOR`, `FORCE_COLOR`, `TERM=dumb`, `--color`, and `--no-color` control color. Non-TTY, CI, `TERM=dumb`, no-color output, and `--no-spinner` disable spinner animation.

Help is available through `mr -h`, `mr -help`, and `mr --help`.

Progress, diagnostics, and errors write to stderr so command output does not pollute stdout pipelines.

## Install, Update, Uninstall

Install from GitHub release:

```sh
curl -fsSL https://raw.githubusercontent.com/JUNERDD/mr/main/install.sh | bash
```

The installer downloads the release `mr.tar.gz`, copies `dist/`, `package.json`, `README.md`, `install.sh`, and `uninstall.sh`, and links `mr`, `mrm`, `mrt`, `mrp`, and `mr-uninstall`.

Environment overrides:

```sh
MR_REPO_OWNER=JUNERDD
MR_REPO_NAME=mr
MR_RELEASE_TAG=v0.6.6
MR_ASSET_NAME=mr.tar.gz
MR_INSTALL_DIR="$HOME/.mr"
MR_BIN_DIR="$HOME/bin"
MR_TARBALL_URL="file:///path/to/mr.tar.gz"
MR_RC="$HOME/.zshrc"
```

Default install dir is `~/.local/share/mr`. The installer prefers a writable directory already in `PATH`; otherwise it falls back to `~/.local/bin` and updates the shell profile so future shells can find the command. Successful install output points users to `mr --version`, `mr --update`, and `mr --uninstall`.

`mr --update` reruns the installed `install.sh` to download the latest release. If an old install lacks lifecycle scripts, it falls back to the official remote script while preserving current install and bin directories.

`mr --uninstall` removes command links, install directory, and the shell profile block. It also removes `mr-uninstall`.

For local development:

```sh
nvm use
npm install
npm run fix
npm run check
npm run build
npm link
npm run install:local
```

`npm run check` runs format check, lint, strict TypeScript typecheck, Vitest, tsdown build, and `node --check dist/index.js`.

`npm run install:local` builds, packages `artifacts/mr.tar.gz`, and installs from that local tarball. Use `MR_LOCAL_SKIP_BUILD=1 npm run install:local` only when the current build is already valid.

## Project Maintenance

Project root:

```text
/Users/zen/Documents/mr
```

Source map:

- `src/index.ts`: executable entry and top-level error fallback.
- `src/commands/`: Pastel command, Zod args/options, Ink command component, maintenance option parsing.
- `src/cli/`: Pastel startup, invocation name, runtime argv state.
- `src/core/`: context, settings, request provider/command resolution, target parsing, dry-run rendering, errors, formatting.
- `src/workflow/`: MR workflow orchestration, strategy flows, detached mode, config command, request handling, conflict resume.
- `src/git/`: Git command wrappers, exact branch/ref checks, worktree helpers, conflict marker rewriting, working-tree guards, plumbing helpers.
- `src/runtime/`: command runner and lifecycle script dispatch.
- `src/ui/`: terminal rendering, color/spinner behavior, target/config pickers.
- `test/`: Vitest coverage for command parsing, strategy/config/request precedence, branch flows, conflicts, detached mode, install scripts, and lifecycle behavior.

Preserve the TypeScript/Pastel/Ink/Zod structure when editing. For behavior changes, run the narrowest relevant tests first, then `npm run check` when feasible. Keep `/Users/zen/Documents/mr/README.md` aligned with behavior, command examples, Mermaid diagrams, provider behavior, and install/update/uninstall notes.
