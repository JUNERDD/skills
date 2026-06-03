# MR CLI Reference

## Command Surface

`mr` is a Node CLI for CNB merge requests. It is implemented with Pastel, Ink, React, Zod, TypeScript, and a small git/CNB runner layer.

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

Maintenance commands:

```sh
mr --config
mr --config --show
mr --config --strategy rebase
mr --config --local --strategy merge-target
mr --config --global --strategy pr
mr --config --detached
mr --config --no-detached
mr --config --global --detached
mr --config --unset
mr --update
mr --uninstall
mr --version
mr -h
mr -help
mr --help
```

`mr config`, `mr update`, and `mr uninstall` remain valid target-branch invocations. Use the `--config`, `--update`, and `--uninstall` flags for maintenance.

## Branch And PR Semantics

Generated MR branches use:

```text
mr/<target>/<current>
```

CNB PR creation uses:

```sh
git cnb pull create -H <source> -B <target>
```

For MR-branch strategies, `<source>` is `mr/<target>/<current>`. For `--pr`, `<source>` is the current branch.

Before real execution, the CLI verifies git context, resolves strategy and detached mode, fetches `origin/<target>`, checks whether the current branch is already merged into the target, and skips PR creation when no work is needed. Inline MR-branch strategies require a clean tracked working tree; detached mode intentionally does not.

Remote MR branch checks use exact `refs/heads/<branch>` matching. A branch that only suffix-matches `mr/<target>/<current>` must not be treated as the MR branch. If the remote MR branch disappears between checking and fetching, the CLI treats it as absent and recreates or regenerates it.

When a remote MR branch already exists, the CLI reuses it when that is safe:

- `merge` pulls the existing MR branch, merges the current branch, syncs the target branch, pushes, and confirms/creates the PR.
- `rebase` can skip rebuilding when the existing MR branch already represents the current branch's equivalent replayed changes on the target.
- `merge-target` can skip rebuilding when the existing MR branch already contains both current and target.

`--rm-mr` deletes `origin/mr/<target>/<current>` first and then rebuilds using an MR-branch strategy. It is invalid with `--pr`.

## Strategy Details

Use one strategy per run.

### merge

Built-in default.

1. Fetch `origin/<target>`.
2. Create or reuse `origin/mr/<target>/<current>`.
3. Switch local `mr/<target>/<current>` from the remote MR branch or `origin/<target>`.
4. Merge the current branch into the MR branch.
5. Merge `origin/<target>` into the MR branch to sync the target.
6. Push `HEAD:mr/<target>/<current>`.
7. Confirm or create the CNB PR.
8. Switch back to the original current branch.

### rebase

1. Fetch `origin/<target>`.
2. Switch local `mr/<target>/<current>` from the current branch.
3. Compute the merge base between `origin/<target>` and the current branch.
4. Rebase the MR branch onto `origin/<target>`.
5. Push with `--force-with-lease --set-upstream`.
6. Confirm or create the CNB PR.
7. Switch back to the original current branch.

### merge-target

1. Fetch `origin/<target>`.
2. Switch local `mr/<target>/<current>` from the current branch.
3. Merge `origin/<target>` into the MR branch.
4. Push with `--force-with-lease --set-upstream`.
5. Confirm or create the CNB PR.
6. Switch back to the original current branch.

### pr

1. Fetch `origin/<target>`.
2. Push the current branch with upstream.
3. Create or confirm the CNB PR from the current branch to the target branch.

## Detached Mode

Detached mode is orthogonal to strategy and is enabled by `--detached`, `MR_DETACHED`, or `git config mr.detached true`.

Behavior:

- The main worktree stays on the business branch.
- Tracked working tree cleanliness is not required.
- `pr` behaves like direct PR creation and has no branch-switching work to avoid.
- Happy-path `merge` and `merge-target` use git plumbing (`merge-tree`, `commit-tree`, and pushing the resulting object) to update `mr/<target>/<current>` without switching local `HEAD`.
- `rebase` and conflicted merge/merge-target paths use a temporary git worktree under `$TMPDIR/mr-worktrees/`.
- Re-running the same detached command from the main repo detects an unresolved leftover worktree, resumes the merge or rebase there, pushes the MR branch, creates/confirms the PR, and removes the worktree.

Detached resume command examples:

```sh
mr test --detached
mr test --detached --rebase
mr test --detached --merge-target
```

If the user resolved conflicts inside the worktree but forgot `git add`, the CLI reports the unmerged paths and asks for `git add` before retrying.

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
3. Local git config: `git config mr.strategy ...`
4. Global git config: `git config --global mr.strategy ...`
5. Legacy `git config --bool mr.rebase`
6. Built-in `merge`

Detached values are booleans. Accepted environment/config forms include `true`, `false`, `1`, `0`, `yes`, `no`, `on`, and `off`.

Detached precedence from highest to lowest:

1. Command flag: `--detached`, `--no-detached`
2. `MR_DETACHED=true|false|1|0`
3. Local git config: `git config mr.detached true|false`
4. Global git config: `git config --global mr.detached true|false`
5. Built-in `false`

`mr --config` is interactive when no script-friendly option is supplied. In scripts, use `--show`, `--strategy`, `--detached`, `--no-detached`, `--global`, `--local`, or `--unset`.

## Conflict And Resume

The CLI has explicit resume paths. Let those paths run after the user finishes manual conflict resolution; do not replace them with hand-written git commits or a manual `--pr` shortcut.

### Inline merge conflicts

The CLI stops on `mr/<target>/<current>` with `MERGE_HEAD` active.

Handoff to the user:

```sh
git status --short --branch
# resolve files
git add <files>
mr <target>
```

On resume, the CLI checks for unmerged files, runs `git commit --no-edit`, pushes `mr/<target>/<current>`, confirms/creates the PR, and switches back to `<current>`.

### Inline rebase conflicts

The CLI stops in an active rebase for `mr/<target>/<current>`; `git branch --show-current` may be empty.

Handoff to the user:

```sh
git status --short --branch
# resolve files
git add <files>
mr <target>
```

On resume, the CLI checks for unmerged files, runs `git -c core.editor=true rebase --continue`, pushes with force-with-lease, confirms/creates the PR, and switches back to `<current>`.

### Inline merge-target conflicts

The CLI stops on `mr/<target>/<current>` with `MERGE_HEAD` active.

Handoff to the user:

```sh
git status --short --branch
# resolve files
git add <files>
mr <target> --merge-target
```

Preserve the `--merge-target` flag on resume.

### Detached conflicts

The main repo remains on the business branch. The CLI reports a worktree path under `$TMPDIR/mr-worktrees/`.

Handoff to the user:

```sh
cd <reported-worktree>
# resolve files
git add <files>
cd <main-repo>
mr <target> --detached
```

Preserve the original strategy flag when it was `--rebase` or `--merge-target`.

Allowed agent inspection after a stopped run:

```sh
git status --short --branch
git branch --show-current
git rev-parse -q --verify MERGE_HEAD
git rev-parse -q --verify REBASE_HEAD
git worktree list --porcelain
```

Avoid mutating recovery commands unless the user explicitly asks for that exact action. This includes `git add`, `git commit`, `git rebase --continue`, `git merge --continue`, `git merge --abort`, `git rebase --abort`, `git reset`, `git switch`, `git push`, and `git cnb pull create`.

For non-conflict failures in inline mode, the CLI attempts to restore the initial branch and appends manual recovery instructions if restoration fails.

## Diagnostics And Output

Use `--dry-run` to print the planned git/CNB commands without mutating local branches, remote branches, or PRs. If tracked files are dirty, dry-run still prints the plan and warns that real inline execution would stop first.

Use `--verbose` for executed commands and full output. `DEBUG=mr` is equivalent to verbose. Without verbose, failed command output is compacted and the CLI suggests adding `--verbose`.

Use `--quiet` for errors only. Use `--no-color` or `MR_NO_COLOR=1` for plain logs. `NO_COLOR`, `MR_NO_COLOR`, `FORCE_COLOR`, `TERM=dumb`, `--color`, and `--no-color` control color. Non-TTY, CI, `TERM=dumb`, no-color output, and `--no-spinner` disable spinner animation.

Help is available through `mr -h`, `mr -help`, and `mr --help`.

## Install, Update, Uninstall

Install from GitHub release:

```sh
curl -fsSL https://raw.githubusercontent.com/JUNERDD/mr/main/install.sh | bash
```

The installer downloads the release `mr.tar.gz`, copies `dist/`, `package.json`, `README.md`, `install.sh`, and `uninstall.sh`, and links `mr`, `mrm`, `mrt`, `mrp`, and `mr-uninstall`.

Environment overrides:

```sh
MR_RELEASE_TAG=vX.Y.Z
MR_INSTALL_DIR="$HOME/.mr"
MR_BIN_DIR="$HOME/bin"
MR_TARBALL_URL="file:///path/to/mr.tar.gz"
MR_RC="$HOME/.zshrc"
```

Default install dir is `~/.local/share/mr`. The installer prefers a writable directory already in `PATH`; otherwise it falls back to `~/.local/bin` and updates the shell profile so future shells can find the command. Successful install output points users to `mr --version`, `mr --update`, and `mr --uninstall`.

`mr --update` reruns the installed `install.sh` to download the latest release. If an old install lacks lifecycle scripts, it falls back to the official remote script while preserving current install and bin directories.

`mr --uninstall` removes command links, install directory, and the shell profile block.

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

## Project Maintenance

Project root:

```text
/Users/zen/Documents/mr
```

Source map:

- `src/index.ts`: executable entry and top-level error fallback.
- `src/commands/`: Pastel command, Zod args/options, Ink command component, maintenance option parsing.
- `src/cli/`: Pastel startup, invocation name, runtime argv state.
- `src/core/`: context, settings, target parsing, dry-run rendering, errors, formatting.
- `src/workflow/`: MR workflow orchestration, strategy flows, detached mode, config command, update/uninstall dispatch, conflict resume.
- `src/git/`: git command wrappers, exact branch/ref checks, worktree helpers, conflict marker rewriting, working tree guards.
- `src/runtime/`: command runner and lifecycle script dispatch.
- `src/ui/`: terminal rendering, color/spinner behavior, target/config pickers.
- `test/`: Vitest coverage for command parsing, strategy/config precedence, branch flows, conflicts, detached mode, install scripts, and lifecycle behavior.

Preserve the TypeScript/Pastel/Ink/Zod structure when editing. For behavior changes, run the narrowest relevant tests first, then `npm run check` when feasible. Keep `/Users/zen/Documents/mr/README.md` aligned with behavior, command examples, and Mermaid diagrams.
