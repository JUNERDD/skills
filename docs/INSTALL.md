# Installing JUNERDD Skills For Agent Runtimes

Expose every skill from this repository as a direct child of the shared agent
skill directory:

```text
~/.agents/skills/<skill-name> -> <repo>/skills/<skill-name>
```

This flat link farm works with runtimes that only inspect
`~/.agents/skills/*/SKILL.md`. Each link still points at the checkout, so edits
inside an existing skill are visible immediately. A managed reconciliation step
adds, removes, or renames top-level links when the collection structure changes.

Do not install the collection through this older nested layout:

```text
~/.agents/skills/junerdd-skill -> <repo>/skills
```

Some runtimes do not recurse through that extra collection directory.

## Path Rules

There are three different paths in this setup. Do not mix them up.

- Repository checkout path: where the `JUNERDD/skills` Git repository lives.
- Skill discovery path: the shared `~/.agents/skills` directory read by agent
  runtimes.
- Installation state path: the manifest and managed hook snapshot, normally
  below `~/.local/state/junerdd-skills/`.

The installer creates one symlink per direct child containing `SKILL.md`. It
does not replace the skill discovery directory itself and does not modify other
skills already installed there. Keep the installation state outside the entire
repository checkout, the selected source tree, and the discovery directory.

## Install Location Policy

Before cloning or linking anything, decide where the local checkout should
live.

- If the user already gave an install path or asked to use the current local
  checkout, use that path.
- If the user did not specify an install location, stop and ask them where they
  want the repository installed.
- If the user explicitly says the agent can choose the install location, use
  `~/.junerdd/JUNERDD-skills` as the default checkout path.

## Installation

1. Determine the absolute path of this repository.
   - If the agent is already working inside a local checkout of
     `JUNERDD/skills`, use that checkout.
   - Otherwise, follow the install location policy above before cloning
     anything.
   - If the user lets the agent choose the install location, clone
     `https://github.com/JUNERDD/skills.git` to
     `~/.junerdd/JUNERDD-skills` and use that checkout.

2. Confirm that `node` is available. The link manager uses only Node.js
   built-in modules and installs no packages.

3. From the repository checkout, install the flat link farm:

   ```bash
   node scripts/sync-skill-links.mjs install
   ```

   The command:

   - validates every `skills/<skill-name>/SKILL.md` and its frontmatter name
   - refuses to overwrite a real directory, file, or unowned symlink
   - creates one top-level directory symlink per skill
   - records ownership in
     `~/.local/state/junerdd-skills/link-install.json`, or below
     `$XDG_STATE_HOME` when set
   - records a checkout-specific identifier and the selected state path in the
     repository's local Git configuration, so another clone cannot uninstall
     this checkout's links
   - removes the old `junerdd-skill` collection symlink only when it points to
     this checkout and the direct links have been verified
   - writes a pinned synchronizer and four managed hooks beside the state file,
     outside the checked-out worktree, then enables that directory through the
     local `core.hooksPath` setting

   Keeping the active hooks and synchronizer outside the checkout means a
   destination branch cannot replace executable hook code during checkout. The
   wrappers also record the current Node executable so they work in Git clients
   with a reduced `PATH`.

4. Verify the installation:

   ```bash
   node scripts/sync-skill-links.mjs doctor
   ```

   A healthy result reports the number of direct skill links and confirms that
   automatic Git synchronization is enabled.

## Existing Git Hooks

The installer reads the effective `core.hooksPath` across system, global, local,
and worktree scopes. It refuses to replace a custom value or hide active hooks
already stored in `.git/hooks`, including hooks reached through a symlinked
directory. If this repository already uses either form, keep it intact and
install the links with:

```bash
node scripts/sync-skill-links.mjs install --no-hooks
```

This leaves automatic synchronization disabled. Run reconciliation manually
after structural changes:

```bash
node scripts/sync-skill-links.mjs sync
```

If you integrate synchronization into an existing hook system, do not execute a
script from the checked-out worktree during checkout. Install a reviewed copy of
the synchronizer at a trusted path outside the checkout and invoke that copy
with `JUNERDD_SKILL_LINKS_REPO_ROOT` set to the current Git top level. Do not
overwrite an existing hook merely to add synchronization.

## Updating

Changes to files inside an existing skill pass through its directory symlink
immediately. The installed Git hooks reconcile structural changes after pulls,
merges, rebases, branch checkouts, and local commits:

- a new skill gets a new top-level link
- a deleted skill loses only its previously managed link
- a renamed skill is treated as one managed removal plus one creation

The hooks invoke the pinned synchronizer beside the state file rather than code
from the destination branch. Rerun `install` when this repository's link-manager
implementation changes; ordinary skill content and directory changes do not
require reinstalling it.

When skill directories are added, removed, or renamed without a following Git
operation, reconcile them explicitly:

```bash
node scripts/sync-skill-links.mjs sync
```

Run the doctor command at any time to detect missing links, ownership drift, a
reintroduced legacy collection link, disabled hooks, or changed/missing managed
hook assets.

After the checkout directory is moved, the next sync, install, or managed Git
hook remaps the default repository-relative source. A custom `--source` remains
absolute. Rerunning `install` with a new `--state` path migrates the manifest and
managed hook assets rather than leaving two owners for the same links.

## Uninstalling

From the installed checkout, run:

```bash
node scripts/sync-skill-links.mjs uninstall
```

The command removes only manifest-owned symlinks that still point to their
recorded source directories. Changed paths and unrelated skills are preserved.
It also restores the previous local Git hooks configuration when the installer
enabled it, removes its local ownership metadata, and deletes unchanged managed
hook assets before removing the installation state file.

## Runtimes That Reject Directory Symlinks

The flat link farm assumes the runtime follows a top-level directory symlink
when it checks for `SKILL.md`. If a runtime rejects symlinked directories rather
than merely avoiding recursive discovery, install individual skills as copied
packages instead:

```bash
npx skills@latest add JUNERDD/skills --skill <skill-name>
```

Copied installs require an explicit reinstall to receive source updates and do
not provide the checkout-backed live synchronization of the link farm.
