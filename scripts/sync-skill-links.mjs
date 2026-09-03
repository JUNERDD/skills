#!/usr/bin/env node

import {
  accessSync,
  chmodSync,
  constants,
  lstatSync,
  mkdirSync,
  readFileSync,
  readlinkSync,
  readdirSync,
  realpathSync,
  renameSync,
  rmdirSync,
  symlinkSync,
  unlinkSync,
  writeFileSync,
} from 'node:fs'
import { createHash, randomUUID } from 'node:crypto'
import { homedir } from 'node:os'
import {
  basename,
  dirname,
  isAbsolute,
  join,
  parse,
  relative,
  resolve,
} from 'node:path'
import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const scriptFile = fileURLToPath(import.meta.url)
const repoRoot = resolve(
  process.env.JUNERDD_SKILL_LINKS_REPO_ROOT ??
    resolve(dirname(scriptFile), '..'),
)
const defaultSourceRoot = resolve(repoRoot, 'skills')
const defaultTargetRoot = resolve(homedir(), '.agents/skills')
const stateBase = process.env.XDG_STATE_HOME
  ? resolve(process.env.XDG_STATE_HOME)
  : resolve(homedir(), '.local/state')
const defaultStateFile = resolve(
  stateBase,
  'junerdd-skills/link-install.json',
)
const hooksNodeConfig = 'junerdd.skillLinksNode'
const installationStateConfig = 'junerdd.skillLinksState'
const repositoryIdConfig = 'junerdd.skillLinksRepositoryId'
const legacyCollectionName = 'junerdd-skill'
const stateSchemaVersion = 1
const skillNamePattern = /^[a-z0-9]+(?:-[a-z0-9]+)*$/
const hookNames = ['post-checkout', 'post-commit', 'post-merge', 'post-rewrite']

function usage() {
  process.stdout.write(`Usage:
  node scripts/sync-skill-links.mjs install [options]
  node scripts/sync-skill-links.mjs sync [options]
  node scripts/sync-skill-links.mjs doctor [options]
  node scripts/sync-skill-links.mjs uninstall [options]

Commands:
  install    Create or refresh one top-level symlink per skill and enable Git hooks.
  sync       Reconcile an existing installation after skill additions or removals.
  doctor     Verify source skills, managed links, installation state, and Git hooks.
  uninstall Remove only links still owned by this installation.

Options:
  --source <path>  Skill source directory (default: <repo>/skills).
  --target <path>  Harness discovery directory (default: ~/.agents/skills).
  --state <path>   Installation state file (must be outside managed trees).
  --no-hooks       Install links without changing core.hooksPath.
  --if-installed   Exit successfully when no matching installation exists.
  --quiet          Suppress successful sync output.
  -h, --help       Show this help.
`)
}

function parseArguments(argv) {
  const options = {
    command: null,
    source: null,
    target: null,
    state: defaultStateFile,
    noHooks: false,
    ifInstalled: false,
    quiet: false,
  }

  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index]

    if (argument === '-h' || argument === '--help') {
      options.command = 'help'
      continue
    }

    if (!argument.startsWith('-') && options.command === null) {
      options.command = argument
      continue
    }

    if (argument === '--no-hooks') {
      options.noHooks = true
      continue
    }
    if (argument === '--if-installed') {
      options.ifInstalled = true
      continue
    }
    if (argument === '--quiet') {
      options.quiet = true
      continue
    }

    if (argument === '--source' || argument === '--target' || argument === '--state') {
      const value = argv[index + 1]
      if (!value || value.startsWith('-')) {
        throw new Error(`${argument} requires a path`)
      }
      options[argument.slice(2)] = resolve(value)
      index += 1
      continue
    }

    throw new Error(`Unknown argument: ${argument}`)
  }

  if (!options.command) {
    options.command = 'help'
  }

  const commands = new Set(['help', 'install', 'sync', 'doctor', 'uninstall'])
  if (!commands.has(options.command)) {
    throw new Error(`Unknown command: ${options.command}`)
  }

  return options
}

function lstatOptional(path) {
  try {
    return lstatSync(path)
  } catch (error) {
    if (error && (error.code === 'ENOENT' || error.code === 'ENOTDIR')) {
      return null
    }
    throw error
  }
}

function assertSafeRoot(path, label) {
  if (!isAbsolute(path)) {
    throw new Error(`${label} must be absolute: ${path}`)
  }
  if (resolve(path) === parse(resolve(path)).root) {
    throw new Error(`${label} cannot be a filesystem root: ${path}`)
  }
}

function assertRealDirectory(path, label, { create = false } = {}) {
  assertSafeRoot(path, label)
  let stat = lstatOptional(path)
  if (!stat && create) {
    mkdirSync(path, { recursive: true, mode: 0o755 })
    stat = lstatSync(path)
  }
  if (!stat) {
    throw new Error(`${label} does not exist: ${path}`)
  }
  if (stat.isSymbolicLink() || !stat.isDirectory()) {
    throw new Error(`${label} must be a real directory, not a symlink or file: ${path}`)
  }
}

function canonicalDirectory(path, label, { create = false } = {}) {
  assertRealDirectory(path, label, { create })
  return realpathSync(path)
}

function comparableDirectory(path) {
  const stat = lstatOptional(path)
  if (stat && !stat.isSymbolicLink() && stat.isDirectory()) {
    return realpathSync(path)
  }
  return canonicalPotentialPath(path)
}

function canonicalPotentialPath(path) {
  const absolute = resolve(path)
  const missing = []
  let cursor = absolute

  while (!lstatOptional(cursor)) {
    const parent = dirname(cursor)
    if (parent === cursor) {
      return absolute
    }
    missing.push(basename(cursor))
    cursor = parent
  }

  return resolve(realpathSync(cursor), ...missing.reverse())
}

function isWithinPath(root, candidate) {
  const child = relative(resolve(root), resolve(candidate))
  return child === '' || (!child.startsWith('..') && !isAbsolute(child))
}

function statePathOverlap(stateFile, sourceRoot, targetRoot) {
  const candidate = canonicalPotentialPath(stateFile)
  return (
    isWithinPath(realpathSync(repoRoot), candidate) ||
    isWithinPath(sourceRoot, candidate) ||
    isWithinPath(targetRoot, candidate)
  )
}

function assertSeparateStatePath(stateFile, sourceRoot, targetRoot) {
  assertSafeRoot(stateFile, 'Installation state')
  if (statePathOverlap(stateFile, sourceRoot, targetRoot)) {
    throw new Error(
      `Installation state must be outside the repository, source, and target trees: ${stateFile}`,
    )
  }
}

function parseSkillName(skillFile) {
  const content = readFileSync(skillFile, 'utf8')
  const frontmatter = content.match(/^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/)
  if (!frontmatter) {
    throw new Error(`Missing YAML frontmatter: ${skillFile}`)
  }
  const nameLine = frontmatter[1]
    .split(/\r?\n/)
    .find((line) => /^name\s*:/.test(line))
  const match = nameLine?.match(/^name\s*:\s*['"]?([^'"\s]+)['"]?\s*$/)
  if (!match) {
    throw new Error(`Missing or unsupported frontmatter name: ${skillFile}`)
  }
  return match[1]
}

function discoverSkills(sourceRoot) {
  const skills = []

  for (const entry of readdirSync(sourceRoot, { withFileTypes: true })) {
    if (!entry.isDirectory()) {
      continue
    }

    const name = entry.name
    const skillFile = join(sourceRoot, name, 'SKILL.md')
    const skillFileStat = lstatOptional(skillFile)
    if (!skillFileStat) {
      continue
    }
    if (!skillFileStat.isFile() || skillFileStat.isSymbolicLink()) {
      throw new Error(`SKILL.md must be a regular file: ${skillFile}`)
    }
    if (!skillNamePattern.test(name)) {
      throw new Error(`Unsupported skill directory name: ${name}`)
    }

    const declaredName = parseSkillName(skillFile)
    if (declaredName !== name) {
      throw new Error(
        `Skill directory and frontmatter name differ: ${name} != ${declaredName}`,
      )
    }

    skills.push({
      name,
      source: resolve(sourceRoot, name),
    })
  }

  skills.sort((left, right) => left.name.localeCompare(right.name))
  if (skills.length === 0) {
    throw new Error(`No direct child skills found in ${sourceRoot}`)
  }
  return skills
}

function validateState(state, stateFile) {
  if (!state || typeof state !== 'object' || Array.isArray(state)) {
    throw new Error(`Invalid installation state: ${stateFile}`)
  }
  if (state.schemaVersion !== stateSchemaVersion) {
    throw new Error(
      `Unsupported installation state schema in ${stateFile}: ${state.schemaVersion}`,
    )
  }
  if (state.collection !== 'JUNERDD/skills') {
    throw new Error(`Unexpected collection in installation state: ${stateFile}`)
  }
  if (
    !isAbsolute(state.sourceRoot) ||
    !isAbsolute(state.targetRoot) ||
    (state.repoRoot && !isAbsolute(state.repoRoot))
  ) {
    throw new Error(`Installation state paths must be absolute: ${stateFile}`)
  }
  assertSafeRoot(state.sourceRoot, 'State source root')
  assertSafeRoot(state.targetRoot, 'State target root')
  if (
    state.sourceRelative !== undefined &&
    state.sourceRelative !== null &&
    state.sourceRelative !== 'skills'
  ) {
    throw new Error(`Invalid relative source in installation state: ${stateFile}`)
  }
  if (!Array.isArray(state.links) || state.links.some((name) => !skillNamePattern.test(name))) {
    throw new Error(`Invalid managed link names in installation state: ${stateFile}`)
  }
  if (new Set(state.links).size !== state.links.length) {
    throw new Error(`Duplicate managed link names in installation state: ${stateFile}`)
  }
  if (state.installation) {
    if (
      typeof state.installation.repositoryId !== 'string' ||
      !state.installation.repositoryId ||
      !isAbsolute(state.installation.stateFile)
    ) {
      throw new Error(`Invalid repository metadata in installation state: ${stateFile}`)
    }
  }
  return state
}

function readState(stateFile, { optional = false } = {}) {
  const stat = lstatOptional(stateFile)
  if (!stat) {
    if (optional) {
      return null
    }
    throw new Error(
      `No managed installation found at ${stateFile}. Run the install command first.`,
    )
  }
  if (!stat.isFile() || stat.isSymbolicLink()) {
    throw new Error(`Installation state must be a regular file: ${stateFile}`)
  }

  let state
  try {
    state = JSON.parse(readFileSync(stateFile, 'utf8'))
  } catch (error) {
    throw new Error(`Could not parse installation state ${stateFile}: ${error.message}`)
  }
  return validateState(state, stateFile)
}

function writeState(stateFile, state) {
  const stateDirectory = dirname(stateFile)
  assertSafeRoot(stateDirectory, 'State directory')
  mkdirSync(stateDirectory, { recursive: true, mode: 0o700 })
  const tempFile = join(
    stateDirectory,
    `.link-install.${process.pid}.${Date.now()}.tmp`,
  )

  try {
    writeFileSync(tempFile, `${JSON.stringify(state, null, 2)}\n`, {
      encoding: 'utf8',
      mode: 0o600,
    })
    chmodSync(tempFile, 0o600)
    renameSync(tempFile, stateFile)
  } catch (error) {
    if (lstatOptional(tempFile)) {
      unlinkSync(tempFile)
    }
    throw error
  }
}

function resolvedLinkTarget(linkPath) {
  return resolve(dirname(linkPath), readlinkSync(linkPath))
}

function isExpectedLink(linkPath, expectedSource) {
  const stat = lstatOptional(linkPath)
  if (!stat || !stat.isSymbolicLink()) {
    return false
  }
  if (resolvedLinkTarget(linkPath) === resolve(expectedSource)) {
    return true
  }

  try {
    return realpathSync(linkPath) === realpathSync(expectedSource)
  } catch {
    return false
  }
}

function createAtomicDirectoryLink(source, target) {
  const targetDirectory = dirname(target)
  let attempt = 0
  let tempLink

  do {
    tempLink = join(
      targetDirectory,
      `.junerdd-skill-link.${process.pid}.${Date.now()}.${attempt}`,
    )
    attempt += 1
  } while (lstatOptional(tempLink))

  try {
    symlinkSync(source, tempLink, 'dir')
    renameSync(tempLink, target)
  } catch (error) {
    if (lstatOptional(tempLink)) {
      unlinkSync(tempLink)
    }
    throw error
  }
}

function preflightDesiredLinks(skills, targetRoot, previousState) {
  const previousNames = new Set(previousState?.links ?? [])
  const collisions = []

  for (const skill of skills) {
    const target = join(targetRoot, skill.name)
    const stat = lstatOptional(target)
    if (!stat || isExpectedLink(target, skill.source)) {
      continue
    }

    const wasManagedAtSameTarget = Boolean(
      previousState &&
        previousState.targetRoot === targetRoot &&
        previousNames.has(skill.name) &&
        isExpectedLink(target, join(previousState.sourceRoot, skill.name)),
    )
    if (!wasManagedAtSameTarget) {
      const kind = stat.isSymbolicLink()
        ? `symlink to ${resolvedLinkTarget(target)}`
        : stat.isDirectory()
          ? 'directory'
          : 'file'
      collisions.push(`${target} (${kind})`)
    }
  }

  if (collisions.length > 0) {
    throw new Error(
      `Refusing to replace unmanaged skill entries:\n${collisions
        .map((collision) => `  - ${collision}`)
        .join('\n')}`,
    )
  }
}

function staleLinks(previousState, skills, targetRoot) {
  if (!previousState) {
    return { removable: [], preserved: [] }
  }

  const desiredNames = new Set(skills.map((skill) => skill.name))
  const removable = []
  const preserved = []
  const oldTargetStat = lstatOptional(previousState.targetRoot)

  if (
    oldTargetStat &&
    (oldTargetStat.isSymbolicLink() || !oldTargetStat.isDirectory())
  ) {
    throw new Error(
      `Previous target root is no longer a real directory: ${previousState.targetRoot}`,
    )
  }

  for (const name of previousState.links) {
    const oldTarget = join(previousState.targetRoot, name)
    const retainedAtSamePath =
      previousState.targetRoot === targetRoot && desiredNames.has(name)
    if (retainedAtSamePath) {
      continue
    }

    const stat = lstatOptional(oldTarget)
    if (!stat) {
      continue
    }
    const expectedSource = join(previousState.sourceRoot, name)
    if (isExpectedLink(oldTarget, expectedSource)) {
      removable.push(oldTarget)
    } else {
      preserved.push(oldTarget)
    }
  }

  return { removable, preserved }
}

function rollbackError(error, rollbackFailure) {
  if (!rollbackFailure) {
    return error
  }
  return new Error(`${error.message}; rollback failed: ${rollbackFailure.message}`)
}

function reconcile({ sourceRoot, targetRoot, previousState }) {
  const skills = discoverSkills(sourceRoot)
  assertRealDirectory(targetRoot, 'Skill discovery root')
  preflightDesiredLinks(skills, targetRoot, previousState)
  const stale = staleLinks(previousState, skills, targetRoot)
  const created = []
  const refreshed = []
  const unchanged = []
  const undo = []
  let finished = false

  function rollback() {
    if (finished) {
      return
    }
    let firstFailure = null
    for (const restore of [...undo].reverse()) {
      try {
        restore()
      } catch (error) {
        firstFailure ??= error
      }
    }
    finished = true
    if (firstFailure) {
      throw firstFailure
    }
  }

  function commit() {
    finished = true
    undo.length = 0
  }

  try {
    for (const skill of skills) {
      const target = join(targetRoot, skill.name)
      if (isExpectedLink(target, skill.source)) {
        unchanged.push(skill.name)
        continue
      }

      const stat = lstatOptional(target)
      const formerLink = stat?.isSymbolicLink() ? readlinkSync(target) : null
      createAtomicDirectoryLink(skill.source, target)
      undo.push(() => {
        if (isExpectedLink(target, skill.source)) {
          unlinkSync(target)
        } else if (lstatOptional(target)) {
          throw new Error(`Refusing to roll back changed skill entry: ${target}`)
        }
        if (formerLink !== null) {
          symlinkSync(formerLink, target, 'dir')
        }
      })
      if (!isExpectedLink(target, skill.source)) {
        throw new Error(`Could not verify managed skill link: ${target}`)
      }
      if (stat) {
        refreshed.push(skill.name)
      } else {
        created.push(skill.name)
      }
    }

    for (const link of stale.removable) {
      const formerLink = readlinkSync(link)
      unlinkSync(link)
      undo.push(() => {
        if (lstatOptional(link)) {
          throw new Error(`Refusing to restore occupied skill entry: ${link}`)
        }
        symlinkSync(formerLink, link, 'dir')
      })
    }

    const legacyLink = join(targetRoot, legacyCollectionName)
    let legacyRemoved = false
    if (isExpectedLink(legacyLink, sourceRoot)) {
      const formerLink = readlinkSync(legacyLink)
      unlinkSync(legacyLink)
      undo.push(() => {
        if (lstatOptional(legacyLink)) {
          throw new Error(`Refusing to restore occupied legacy link: ${legacyLink}`)
        }
        symlinkSync(formerLink, legacyLink, 'dir')
      })
      legacyRemoved = true
    }

    return {
      skills,
      created,
      refreshed,
      unchanged,
      removed: stale.removable,
      preserved: stale.preserved,
      legacyRemoved,
      rollback,
      commit,
    }
  } catch (error) {
    let failure = null
    try {
      rollback()
    } catch (rollbackFailure) {
      failure = rollbackFailure
    }
    throw rollbackError(error, failure)
  }
}

function git(args, { allowMissing = false } = {}) {
  const result = spawnSync('git', ['-C', repoRoot, ...args], {
    encoding: 'utf8',
  })
  if (allowMissing && result.status === 1) {
    return null
  }
  if (result.status !== 0) {
    const detail = (result.stderr || result.stdout || '').trim()
    throw new Error(`git ${args.join(' ')} failed${detail ? `: ${detail}` : ''}`)
  }
  return result.stdout.trim()
}

function localConfig(key) {
  return git(['config', '--local', '--get', key], { allowMissing: true })
}

function effectiveConfig(key) {
  return git(['config', '--get', key], { allowMissing: true })
}

function setLocalGitConfig(key, value) {
  if (value === null) {
    const current = localConfig(key)
    if (current !== null) {
      git(['config', '--local', '--unset-all', key])
    }
    return
  }
  git(['config', '--local', key, value])
}

function assertActiveGitRoot() {
  const gitRoot = realpathSync(git(['rev-parse', '--show-toplevel']))
  if (gitRoot !== realpathSync(repoRoot)) {
    throw new Error(`Script repository is not the active Git root: ${repoRoot}`)
  }
}

function sameHooksPath(value, expectedPath) {
  if (value === null || value === '') {
    return false
  }
  return resolve(repoRoot, value) === resolve(repoRoot, expectedPath)
}

function displayConfig(value) {
  if (value === null) {
    return 'unset'
  }
  return value === '' ? '<empty>' : value
}

function activeDefaultHooks() {
  const configuredDirectory = git(['rev-parse', '--git-path', 'hooks'])
  const unresolvedDirectory = resolve(repoRoot, configuredDirectory)
  let directory
  try {
    directory = realpathSync(unresolvedDirectory)
  } catch (error) {
    if (error && error.code === 'ENOENT') {
      return []
    }
    throw error
  }
  const directoryStat = lstatOptional(directory)
  if (!directoryStat || !directoryStat.isDirectory()) {
    return []
  }

  return readdirSync(directory)
    .filter((name) => !name.endsWith('.sample'))
    .filter((name) => {
      const path = join(directory, name)
      const stat = lstatOptional(path)
      if (!stat || (!stat.isFile() && !stat.isSymbolicLink())) {
        return false
      }
      try {
        accessSync(path, constants.X_OK)
        return true
      } catch {
        return false
      }
    })
    .sort()
}

function digest(content) {
  return createHash('sha256').update(content).digest('hex')
}

function digestFile(path) {
  return digest(readFileSync(path))
}

function shellQuote(value) {
  return `'${String(value).replaceAll("'", `'"'"'`)}'`
}

function managedAssetsRoot(stateFile) {
  return resolve(`${stateFile}.assets`)
}

function hookProgram(name, nodePath, runtimePath, stateFile) {
  const discardInput = name === 'post-rewrite' ? 'cat >/dev/null\n' : ''
  return `#!/bin/sh

${discardInput}repository_root=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0

if ! JUNERDD_SKILL_LINKS_REPO_ROOT="$repository_root" \\
  ${shellQuote(nodePath)} ${shellQuote(runtimePath)} \\
  sync --state ${shellQuote(stateFile)} --if-installed --quiet; then
  printf '%s\\n' \\
    'Warning: JUNERDD skill link sync failed; run the doctor command for details.' >&2
fi

exit 0
`
}

function ensureManagedDirectory(path, createdDirectories) {
  const stat = lstatOptional(path)
  if (stat) {
    if (stat.isSymbolicLink() || !stat.isDirectory()) {
      throw new Error(`Managed hook path must be a real directory: ${path}`)
    }
    return
  }
  mkdirSync(path, { mode: 0o700 })
  createdDirectories.push(path)
}

function writeManagedFile(path, content, mode) {
  const stat = lstatOptional(path)
  if (stat && (!stat.isFile() || stat.isSymbolicLink())) {
    throw new Error(`Managed hook asset must be a regular file: ${path}`)
  }
  const previous = stat
    ? { content: readFileSync(path), mode: stat.mode & 0o777 }
    : null
  const temp = join(
    dirname(path),
    `.${basename(path)}.${process.pid}.${Date.now()}.tmp`,
  )

  try {
    writeFileSync(temp, content, { mode })
    chmodSync(temp, mode)
    renameSync(temp, path)
  } catch (error) {
    if (lstatOptional(temp)) {
      unlinkSync(temp)
    }
    throw error
  }

  return () => {
    if (previous) {
      const restoreTemp = `${path}.${process.pid}.restore.tmp`
      writeFileSync(restoreTemp, previous.content, { mode: previous.mode })
      chmodSync(restoreTemp, previous.mode)
      renameSync(restoreTemp, path)
    } else if (lstatOptional(path)) {
      unlinkSync(path)
    }
  }
}

function installManagedHookAssets(stateFile, previousHooks) {
  const assetsRoot = managedAssetsRoot(stateFile)
  const hooksDirectory = join(assetsRoot, 'hooks')
  const runtimePath = join(assetsRoot, 'sync-skill-links.mjs')
  const ownsExistingAssets =
    previousHooks?.assetsRoot &&
    resolve(previousHooks.assetsRoot) === assetsRoot
  const existingRoot = lstatOptional(assetsRoot)
  if (existingRoot && !ownsExistingAssets) {
    throw new Error(
      `Refusing to replace unowned managed hook assets: ${assetsRoot}`,
    )
  }

  mkdirSync(dirname(assetsRoot), { recursive: true, mode: 0o700 })
  const createdDirectories = []
  const undoFiles = []
  let finished = false

  function rollback() {
    if (finished) {
      return
    }
    let firstFailure = null
    for (const undo of [...undoFiles].reverse()) {
      try {
        undo()
      } catch (error) {
        firstFailure ??= error
      }
    }
    for (const directory of [...createdDirectories].reverse()) {
      try {
        rmdirSync(directory)
      } catch (error) {
        if (error.code !== 'ENOTEMPTY' && error.code !== 'ENOENT') {
          firstFailure ??= error
        }
      }
    }
    finished = true
    if (firstFailure) {
      throw firstFailure
    }
  }

  function commit() {
    finished = true
    undoFiles.length = 0
    createdDirectories.length = 0
  }

  try {
    ensureManagedDirectory(assetsRoot, createdDirectories)
    ensureManagedDirectory(hooksDirectory, createdDirectories)

    const runtime = readFileSync(scriptFile)
    undoFiles.push(writeManagedFile(runtimePath, runtime, 0o600))
    const hookDigests = {}
    for (const name of hookNames) {
      const program = hookProgram(name, process.execPath, runtimePath, stateFile)
      const path = join(hooksDirectory, name)
      undoFiles.push(writeManagedFile(path, program, 0o700))
      hookDigests[name] = digest(program)
    }

    return {
      assetsRoot,
      hooksDirectory,
      runtimePath,
      runtimeDigest: digest(runtime),
      hookDigests,
      rollback,
      commit,
    }
  } catch (error) {
    let failure = null
    try {
      rollback()
    } catch (rollbackFailure) {
      failure = rollbackFailure
    }
    throw rollbackError(error, failure)
  }
}

function inferredSourceRelative(state) {
  if (state.sourceRelative === 'skills') {
    return 'skills'
  }
  if (
    state.sourceRelative === undefined &&
    state.repoRoot &&
    resolve(state.repoRoot, 'skills') === resolve(state.sourceRoot)
  ) {
    return 'skills'
  }
  return null
}

function sourceFromState(state) {
  const sourceRelative = inferredSourceRelative(state)
  return sourceRelative ? resolve(repoRoot, sourceRelative) : state.sourceRoot
}

function stateRepositoryId(state) {
  return state.installation?.repositoryId ?? state.hooks?.repositoryId ?? null
}

function stateBelongsToCurrentRepository(state, stateFile) {
  const recordedId = stateRepositoryId(state)
  const currentId = localConfig(repositoryIdConfig)
  const configuredState = localConfig(installationStateConfig)
  if (recordedId) {
    if (currentId === recordedId) {
      return true
    }
    return Boolean(
      currentId === null &&
        state.repoRoot &&
        resolve(state.repoRoot) === repoRoot &&
        configuredState !== null &&
        resolve(configuredState) === resolve(stateFile),
    )
  }
  if (state.repoRoot && resolve(state.repoRoot) === repoRoot) {
    return true
  }

  if (
    !state.hooks ||
    configuredState === null ||
    resolve(configuredState) !== resolve(stateFile)
  ) {
    return false
  }
  const effectiveHooks = effectiveConfig('core.hooksPath')
  return sameHooksPath(effectiveHooks, state.hooks.path)
}

function canonicalizePreviousTarget(state) {
  if (!state) {
    return null
  }
  const stat = lstatOptional(state.targetRoot)
  if (!stat || stat.isSymbolicLink() || !stat.isDirectory()) {
    return state
  }
  return { ...state, targetRoot: realpathSync(state.targetRoot) }
}

function resolvePreviousInstallation(options) {
  const requested = readState(options.state, { optional: true })
  if (requested) {
    if (!stateBelongsToCurrentRepository(requested, options.state)) {
      throw new Error(
        `Installation state belongs to another checkout: ${options.state}`,
      )
    }
    return {
      state: canonicalizePreviousTarget(requested),
      stateFile: options.state,
    }
  }

  const configuredState = localConfig(installationStateConfig)
  if (!configuredState) {
    if (localConfig(repositoryIdConfig) || localConfig(hooksNodeConfig)) {
      throw new Error(
        'Managed installation metadata exists without a readable state file. ' +
          'Restore that state or remove the stale junerdd.skillLinks* Git config.',
      )
    }
    return { state: null, stateFile: null }
  }
  if (resolve(configuredState) === resolve(options.state)) {
    throw new Error(`Configured installation state is missing: ${configuredState}`)
  }

  const previous = readState(configuredState)
  if (!stateBelongsToCurrentRepository(previous, configuredState)) {
    throw new Error(`Configured installation state belongs to another checkout: ${configuredState}`)
  }
  return {
    state: canonicalizePreviousTarget(previous),
    stateFile: resolve(configuredState),
  }
}

function configureInstallation({ previousState, previousStateFile, options }) {
  const currentState = localConfig(installationStateConfig)
  const currentRepositoryId = localConfig(repositoryIdConfig)
  const currentNode = localConfig(hooksNodeConfig)
  const configChanges = []
  let assets = null
  let finished = false

  const previousOwned = Boolean(
    previousState &&
      stateBelongsToCurrentRepository(previousState, previousStateFile),
  )
  if (previousState && !previousOwned) {
    throw new Error(`Installation state belongs to another checkout: ${previousStateFile}`)
  }
  if (
    !previousState &&
    (currentState !== null ||
      currentRepositoryId !== null ||
      currentNode !== null)
  ) {
    throw new Error(
      'Managed Git metadata exists without matching installation state; refusing to overwrite it.',
    )
  }
  if (
    options.noHooks &&
    previousState?.hooks &&
    previousStateFile &&
    resolve(previousStateFile) !== resolve(options.state)
  ) {
    throw new Error(
      'Cannot relocate a hook-enabled state with --no-hooks; rerun without --no-hooks.',
    )
  }

  const repositoryId =
    stateRepositoryId(previousState ?? {}) ??
    currentRepositoryId ??
    randomUUID()
  const priorInstallation = previousState?.installation
  const installation = {
    repositoryId,
    stateFile: options.state,
    configuredByInstaller: true,
    previousRepositoryId: previousOwned
      ? priorInstallation?.previousRepositoryId ?? null
      : currentRepositoryId,
    previousStateFile: previousOwned
      ? priorInstallation?.previousStateFile ??
        previousState?.hooks?.previousStateFile ??
        null
      : currentState,
  }

  function updateConfig(key, before, after) {
    if (before === after) {
      return
    }
    setLocalGitConfig(key, after)
    configChanges.push({ key, before })
  }

  function rollback() {
    if (finished) {
      return
    }
    let firstFailure = null
    for (const change of [...configChanges].reverse()) {
      try {
        setLocalGitConfig(change.key, change.before)
      } catch (error) {
        firstFailure ??= error
      }
    }
    try {
      assets?.rollback()
    } catch (error) {
      firstFailure ??= error
    }
    finished = true
    if (firstFailure) {
      throw firstFailure
    }
  }

  function commit() {
    assets?.commit()
    finished = true
    configChanges.length = 0
  }

  try {
    updateConfig(repositoryIdConfig, currentRepositoryId, repositoryId)
    updateConfig(installationStateConfig, currentState, options.state)

    if (options.noHooks) {
      return {
        installation,
        hooks: previousState?.hooks ?? null,
        rollback,
        commit,
      }
    }

    const previousHooks = previousState?.hooks ?? null
    const effectiveHooks = effectiveConfig('core.hooksPath')
    const localHooks = localConfig('core.hooksPath')
    const priorCoreOwned = Boolean(
      previousHooks &&
        (previousHooks.configuredByInstaller || previousHooks.previousPath === ''),
    )
    const currentMatchesOwnedHooks = Boolean(
      priorCoreOwned && sameHooksPath(effectiveHooks, previousHooks.path),
    )

    if (effectiveHooks !== null && !currentMatchesOwnedHooks) {
      throw new Error(
        `core.hooksPath is already set to ${displayConfig(effectiveHooks)}. ` +
          'Integrate the sync command there or rerun install with --no-hooks.',
      )
    }
    if (effectiveHooks === null) {
      const existingHooks = activeDefaultHooks()
      if (existingHooks.length > 0) {
        throw new Error(
          'Refusing to hide active hooks in .git/hooks: ' +
            `${existingHooks.join(', ')}. Integrate the sync command there or ` +
            'rerun install with --no-hooks.',
        )
      }
    }

    assets = installManagedHookAssets(options.state, previousHooks)
    const priorMetadataOwned = Boolean(
      previousHooks?.metadataConfiguredByInstaller,
    )
    const previousPath = priorCoreOwned
      ? previousHooks.previousPath ?? null
      : localHooks
    const previousNodePath = priorMetadataOwned
      ? previousHooks.previousNodePath ?? null
      : currentNode

    updateConfig('core.hooksPath', localHooks, assets.hooksDirectory)
    updateConfig(hooksNodeConfig, currentNode, process.execPath)
    const configuredHooks = effectiveConfig('core.hooksPath')
    if (!sameHooksPath(configuredHooks, assets.hooksDirectory)) {
      throw new Error(
        'Could not activate managed hooks; effective core.hooksPath is ' +
          `${displayConfig(configuredHooks)}.`,
      )
    }

    return {
      installation,
      hooks: {
        path: assets.hooksDirectory,
        repoRoot,
        repositoryId,
        configuredByInstaller: true,
        previousPath,
        metadataConfiguredByInstaller: true,
        nodePath: process.execPath,
        stateFile: options.state,
        previousNodePath,
        assetsRoot: assets.assetsRoot,
        runtimePath: assets.runtimePath,
        runtimeDigest: assets.runtimeDigest,
        hookDigests: assets.hookDigests,
      },
      rollback,
      commit,
    }
  } catch (error) {
    let failure = null
    try {
      rollback()
    } catch (rollbackFailure) {
      failure = rollbackFailure
    }
    throw rollbackError(error, failure)
  }
}

function statePayload({
  sourceRoot,
  sourceRelative,
  targetRoot,
  skills,
  installation,
  hooks,
}) {
  return {
    schemaVersion: stateSchemaVersion,
    collection: 'JUNERDD/skills',
    repoRoot,
    sourceRoot,
    sourceRelative,
    targetRoot,
    links: skills.map((skill) => skill.name),
    installation,
    hooks,
    updatedAt: new Date().toISOString(),
  }
}

function printReconcileResult(result, targetRoot, quiet) {
  if (quiet) {
    return
  }
  process.stdout.write(
    `Synchronized ${result.skills.length} skill links in ${targetRoot}.\n`,
  )
  if (result.created.length > 0) {
    process.stdout.write(`Created: ${result.created.join(', ')}\n`)
  }
  if (result.refreshed.length > 0) {
    process.stdout.write(`Refreshed: ${result.refreshed.join(', ')}\n`)
  }
  if (result.removed.length > 0) {
    process.stdout.write(
      `Removed stale links: ${result.removed
        .map((path) => basename(path))
        .join(', ')}\n`,
    )
  }
  if (result.legacyRemoved) {
    process.stdout.write(`Removed legacy collection link: ${legacyCollectionName}\n`)
  }
  for (const path of result.preserved) {
    process.stderr.write(
      `Warning: preserved changed or unowned former link: ${path}\n`,
    )
  }
}

function removeManagedHookAssets(hooks) {
  const preserved = []
  if (!hooks?.assetsRoot) {
    return preserved
  }
  const expectedRoot = managedAssetsRoot(hooks.stateFile)
  if (resolve(hooks.assetsRoot) !== expectedRoot) {
    preserved.push(hooks.assetsRoot)
    return preserved
  }

  const files = [
    {
      path: hooks.runtimePath,
      expectedDigest: hooks.runtimeDigest,
    },
    ...hookNames.map((name) => ({
      path: join(hooks.path, name),
      expectedDigest: hooks.hookDigests?.[name],
    })),
  ]
  for (const file of files) {
    if (!file.path) {
      continue
    }
    const stat = lstatOptional(file.path)
    if (!stat) {
      continue
    }
    if (
      !stat.isFile() ||
      stat.isSymbolicLink() ||
      !file.expectedDigest ||
      digestFile(file.path) !== file.expectedDigest
    ) {
      preserved.push(file.path)
      continue
    }
    unlinkSync(file.path)
  }

  for (const directory of [hooks.path, hooks.assetsRoot]) {
    try {
      rmdirSync(directory)
    } catch (error) {
      if (error.code !== 'ENOENT' && error.code !== 'ENOTEMPTY') {
        throw error
      }
    }
  }
  return preserved
}

function cleanupMigratedInstallation(previousState, previousStateFile, options) {
  if (!previousStateFile || resolve(previousStateFile) === resolve(options.state)) {
    return []
  }
  const warnings = []
  if (
    statePathOverlap(
      previousStateFile,
      previousState.sourceRoot,
      previousState.targetRoot,
    )
  ) {
    warnings.push(`preserved unsafe previous state path: ${previousStateFile}`)
  } else if (lstatOptional(previousStateFile)) {
    try {
      unlinkSync(previousStateFile)
    } catch (error) {
      warnings.push(
        `could not remove previous state ${previousStateFile}: ${error.message}`,
      )
    }
  }
  if (
    previousState.hooks?.assetsRoot &&
    previousState.hooks.assetsRoot !== managedAssetsRoot(options.state)
  ) {
    try {
      for (const path of removeManagedHookAssets(previousState.hooks)) {
        warnings.push(`preserved changed previous hook asset: ${path}`)
      }
    } catch (error) {
      warnings.push(
        `could not remove previous managed hook assets: ${error.message}`,
      )
    }
  }
  return warnings
}

function install(options) {
  assertActiveGitRoot()
  const sourceRoot = canonicalDirectory(
    options.source ?? defaultSourceRoot,
    'Skill source root',
  )
  const sourceRelative = options.source ? null : 'skills'
  const targetCandidate = canonicalPotentialPath(options.target ?? defaultTargetRoot)
  assertSeparateStatePath(options.state, sourceRoot, targetCandidate)
  const previous = resolvePreviousInstallation(options)
  const targetExisted = Boolean(lstatOptional(options.target ?? defaultTargetRoot))
  const targetRoot = canonicalDirectory(
    options.target ?? defaultTargetRoot,
    'Skill discovery root',
    { create: true },
  )
  assertSeparateStatePath(options.state, sourceRoot, targetRoot)
  const configuration = configureInstallation({
    previousState: previous.state,
    previousStateFile: previous.stateFile,
    options,
  })
  let result = null

  try {
    result = reconcile({
      sourceRoot,
      targetRoot,
      previousState: previous.state,
    })
    writeState(
      options.state,
      statePayload({
        sourceRoot,
        sourceRelative,
        targetRoot,
        skills: result.skills,
        installation: configuration.installation,
        hooks: configuration.hooks,
      }),
    )
    result.commit()
    configuration.commit()
  } catch (error) {
    let failure = null
    try {
      result?.rollback()
    } catch (rollbackFailure) {
      failure = rollbackFailure
    }
    try {
      configuration.rollback()
    } catch (rollbackFailure) {
      failure ??= rollbackFailure
    }
    if (!targetExisted) {
      try {
        rmdirSync(targetRoot)
      } catch {
        // Preserve a non-empty or concurrently changed directory.
      }
    }
    throw rollbackError(error, failure)
  }

  const cleanupWarnings = cleanupMigratedInstallation(
    previous.state,
    previous.stateFile,
    options,
  )
  printReconcileResult(result, targetRoot, options.quiet)
  if (!options.quiet) {
    process.stdout.write(
      configuration.hooks
        ? `Automatic Git sync enabled through ${configuration.hooks.path}.\n`
        : 'Automatic Git sync not configured; run sync after structural changes.\n',
    )
    process.stdout.write(`State: ${options.state}\n`)
  }
  for (const warning of cleanupWarnings) {
    process.stderr.write(`Warning: ${warning}\n`)
  }
}

function matchingInstalledState(options) {
  const state = readState(options.state, { optional: options.ifInstalled })
  if (!state) {
    return null
  }
  if (!stateBelongsToCurrentRepository(state, options.state)) {
    if (options.ifInstalled) {
      return null
    }
    throw new Error(`Installation state belongs to another checkout: ${options.state}`)
  }

  const expectedSource = comparableDirectory(sourceFromState(state))
  if (options.source) {
    const invocationSource = canonicalDirectory(options.source, 'Skill source root')
    if (invocationSource !== expectedSource) {
      if (options.ifInstalled) {
        return null
      }
      throw new Error(
        `Installation state belongs to ${expectedSource} -> ${state.targetRoot}. ` +
          'Run install to migrate it.',
      )
    }
  }

  const storedTarget = comparableDirectory(state.targetRoot)
  if (options.target) {
    const invocationTarget = comparableDirectory(options.target)
    if (invocationTarget !== storedTarget) {
      if (options.ifInstalled) {
        return null
      }
      throw new Error(
        `Installation state belongs to ${expectedSource} -> ${storedTarget}. ` +
          'Run install to migrate it.',
      )
    }
  }
  return {
    ...state,
    targetRoot: storedTarget,
    effectiveSourceRoot: expectedSource,
  }
}

function sync(options) {
  const state = matchingInstalledState(options)
  if (!state) {
    return
  }
  const sourceRoot = canonicalDirectory(
    state.effectiveSourceRoot,
    'Installed skill source root',
  )
  const targetRoot = canonicalDirectory(
    state.targetRoot,
    'Installed skill discovery root',
    { create: true },
  )
  assertSeparateStatePath(options.state, sourceRoot, targetRoot)
  const result = reconcile({
    sourceRoot,
    targetRoot,
    previousState: { ...state, targetRoot },
  })
  try {
    writeState(
      options.state,
      statePayload({
        sourceRoot,
        sourceRelative: inferredSourceRelative(state),
        targetRoot,
        skills: result.skills,
        installation: state.installation ?? null,
        hooks: state.hooks ? { ...state.hooks, repoRoot } : null,
      }),
    )
    result.commit()
  } catch (error) {
    let failure = null
    try {
      result.rollback()
    } catch (rollbackFailure) {
      failure = rollbackFailure
    }
    throw rollbackError(error, failure)
  }
  printReconcileResult(result, targetRoot, options.quiet)
}

function managedHookIssues(hooks, stateFile) {
  const issues = []
  if (!hooks.assetsRoot || !hooks.runtimePath || !hooks.runtimeDigest || !hooks.hookDigests) {
    issues.push('Managed Git hooks use the legacy worktree layout; rerun install to migrate them')
    return issues
  }
  const expectedRoot = managedAssetsRoot(stateFile)
  if (resolve(hooks.assetsRoot) !== expectedRoot) {
    issues.push(`Managed hook asset root is unexpected: ${hooks.assetsRoot}`)
  }
  if (resolve(hooks.path) !== resolve(hooks.assetsRoot, 'hooks')) {
    issues.push(`Managed hook directory is unexpected: ${hooks.path}`)
  }
  if (resolve(hooks.runtimePath) !== resolve(hooks.assetsRoot, 'sync-skill-links.mjs')) {
    issues.push(`Managed hook runtime is unexpected: ${hooks.runtimePath}`)
  }
  if (isWithinPath(realpathSync(repoRoot), canonicalPotentialPath(hooks.path))) {
    issues.push(`Managed hook directory must be outside the checked-out worktree: ${hooks.path}`)
  }

  const runtimeStat = lstatOptional(hooks.runtimePath)
  if (!runtimeStat || !runtimeStat.isFile() || runtimeStat.isSymbolicLink()) {
    issues.push(`Managed hook runtime is missing or not a regular file: ${hooks.runtimePath}`)
  } else if (digestFile(hooks.runtimePath) !== hooks.runtimeDigest) {
    issues.push(`Managed hook runtime has changed: ${hooks.runtimePath}`)
  }

  for (const name of hookNames) {
    const path = join(hooks.path, name)
    const stat = lstatOptional(path)
    if (!stat || !stat.isFile() || stat.isSymbolicLink()) {
      issues.push(`Managed Git hook is missing or not a regular file: ${path}`)
      continue
    }
    try {
      accessSync(path, constants.X_OK)
    } catch {
      issues.push(`Managed Git hook is not executable: ${path}`)
    }
    if (!hooks.hookDigests[name] || digestFile(path) !== hooks.hookDigests[name]) {
      issues.push(`Managed Git hook has changed: ${path}`)
    }
  }
  return issues
}

function doctor(options) {
  const state = matchingInstalledState(options)
  if (!state) {
    return
  }
  const issues = []
  const sourceStat = lstatOptional(state.effectiveSourceRoot)
  let skills = []
  if (
    !sourceStat ||
    sourceStat.isSymbolicLink() ||
    !sourceStat.isDirectory()
  ) {
    issues.push(
      `Skill source root is missing or is not a real directory: ${state.effectiveSourceRoot}`,
    )
  } else {
    skills = discoverSkills(realpathSync(state.effectiveSourceRoot))
  }
  const discoveredNames = new Set(skills.map((skill) => skill.name))
  const managedNames = new Set(state.links)

  const targetStat = lstatOptional(state.targetRoot)
  if (
    !targetStat ||
    targetStat.isSymbolicLink() ||
    !targetStat.isDirectory()
  ) {
    issues.push(
      `Skill discovery root is missing or is not a real directory: ${state.targetRoot}`,
    )
  } else {
    for (const skill of skills) {
      const target = join(state.targetRoot, skill.name)
      if (!isExpectedLink(target, skill.source)) {
        issues.push(`Missing or incorrect skill link: ${target}`)
      }
      if (!managedNames.has(skill.name)) {
        issues.push(`Source skill is absent from state: ${skill.name}`)
      }
    }
  }

  for (const name of managedNames) {
    if (!discoveredNames.has(name)) {
      issues.push(`State contains a removed source skill: ${name}`)
    }
  }

  const legacyLink = join(state.targetRoot, legacyCollectionName)
  if (isExpectedLink(legacyLink, state.effectiveSourceRoot)) {
    issues.push(`Legacy collection link would duplicate recursive discovery: ${legacyLink}`)
  }
  if (statePathOverlap(options.state, state.effectiveSourceRoot, state.targetRoot)) {
    issues.push(`Installation state overlaps a managed tree: ${options.state}`)
  }

  const configuredState = localConfig(installationStateConfig)
  const configuredRepositoryId = localConfig(repositoryIdConfig)
  if (!state.installation) {
    issues.push('Installation uses legacy repository metadata; rerun install to migrate it')
  } else {
    if (configuredState === null || resolve(configuredState) !== resolve(options.state)) {
      issues.push(
        `Git installation state path is missing or changed: ${displayConfig(configuredState)}`,
      )
    }
    if (configuredRepositoryId !== state.installation.repositoryId) {
      issues.push(
        `Git repository identity is missing or changed: ${displayConfig(configuredRepositoryId)}`,
      )
    }
  }

  let hooksStatus = 'disabled'
  if (state.hooks) {
    const current = effectiveConfig('core.hooksPath')
    if (sameHooksPath(current, state.hooks.path)) {
      hooksStatus = `enabled (${state.hooks.path})`
    } else {
      issues.push(
        `Automatic Git sync expected ${state.hooks.path}, but effective ` +
          `core.hooksPath is ${displayConfig(current)}`,
      )
    }
    const configuredNode = localConfig(hooksNodeConfig)
    if (configuredNode !== state.hooks.nodePath) {
      issues.push(`Git hook Node path is missing or changed: ${displayConfig(configuredNode)}`)
    } else {
      try {
        accessSync(configuredNode, constants.X_OK)
      } catch {
        issues.push(`Configured Git hook Node is not executable: ${configuredNode}`)
      }
    }
    issues.push(...managedHookIssues(state.hooks, options.state))
  }

  if (issues.length > 0) {
    process.stderr.write(`Skill link installation has ${issues.length} issue(s):\n`)
    for (const issue of issues) {
      process.stderr.write(`  - ${issue}\n`)
    }
    process.exitCode = 1
    return
  }

  process.stdout.write(
    `Healthy: ${skills.length} top-level skill links in ${state.targetRoot}.\n`,
  )
  process.stdout.write(`Automatic Git sync: ${hooksStatus}.\n`)
  process.stdout.write(`State: ${options.state}\n`)
}

function restoreInstallationConfiguration(state) {
  let hooksRestored = false
  let metadataRestored = false
  const hooks = state.hooks

  if (hooks?.configuredByInstaller) {
    const current = localConfig('core.hooksPath')
    if (sameHooksPath(current, hooks.path)) {
      setLocalGitConfig('core.hooksPath', hooks.previousPath ?? null)
      hooksRestored = true
    }
  }
  if (hooks?.metadataConfiguredByInstaller) {
    const currentNode = localConfig(hooksNodeConfig)
    if (currentNode === hooks.nodePath) {
      setLocalGitConfig(hooksNodeConfig, hooks.previousNodePath ?? null)
      metadataRestored = true
    }
  }

  const installation = state.installation
  if (installation?.configuredByInstaller) {
    const currentId = localConfig(repositoryIdConfig)
    const currentState = localConfig(installationStateConfig)
    if (currentId === installation.repositoryId) {
      setLocalGitConfig(
        repositoryIdConfig,
        installation.previousRepositoryId ?? null,
      )
      metadataRestored = true
    }
    if (
      currentState !== null &&
      resolve(currentState) === resolve(installation.stateFile)
    ) {
      setLocalGitConfig(
        installationStateConfig,
        installation.previousStateFile ?? null,
      )
      metadataRestored = true
    }
  } else if (hooks?.metadataConfiguredByInstaller) {
    const currentState = localConfig(installationStateConfig)
    if (currentState === hooks.stateFile) {
      setLocalGitConfig(
        installationStateConfig,
        hooks.previousStateFile ?? null,
      )
      metadataRestored = true
    }
  }
  return { hooksRestored, metadataRestored }
}

function uninstall(options) {
  const state = matchingInstalledState(options)
  if (!state) {
    return
  }
  const removed = []
  const preserved = []

  const targetStat = lstatOptional(state.targetRoot)
  if (
    targetStat &&
    (targetStat.isSymbolicLink() || !targetStat.isDirectory())
  ) {
    throw new Error(
      `Skill discovery root is no longer a real directory: ${state.targetRoot}`,
    )
  }

  if (targetStat) {
    for (const name of state.links) {
      const target = join(state.targetRoot, name)
      const recordedSource = join(state.sourceRoot, name)
      const effectiveSource = join(state.effectiveSourceRoot, name)
      if (
        isExpectedLink(target, recordedSource) ||
        isExpectedLink(target, effectiveSource)
      ) {
        unlinkSync(target)
        removed.push(name)
      } else if (lstatOptional(target)) {
        preserved.push(target)
      }
    }
  }

  const restored = restoreInstallationConfiguration(state)
  preserved.push(...removeManagedHookAssets(state.hooks))
  unlinkSync(options.state)

  if (!options.quiet) {
    process.stdout.write(`Removed ${removed.length} managed skill links.\n`)
    if (restored.hooksRestored) {
      process.stdout.write('Restored the previous Git hooks configuration.\n')
    }
    process.stdout.write(`Removed state: ${options.state}\n`)
  }
  for (const path of preserved) {
    process.stderr.write(
      `Warning: preserved changed or unowned managed path: ${path}\n`,
    )
  }
}

function main() {
  const options = parseArguments(process.argv.slice(2))
  switch (options.command) {
    case 'help':
      usage()
      break
    case 'install':
      install(options)
      break
    case 'sync':
      sync(options)
      break
    case 'doctor':
      doctor(options)
      break
    case 'uninstall':
      uninstall(options)
      break
  }
}

try {
  main()
} catch (error) {
  process.stderr.write(`Error: ${error.message}\n`)
  process.exitCode = 1
}
