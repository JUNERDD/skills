import assert from 'node:assert/strict'
import {
  chmodSync,
  lstatSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  realpathSync,
  renameSync,
  rmSync,
  symlinkSync,
  writeFileSync,
} from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { spawnSync } from 'node:child_process'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

const repositoryRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const script = join(repositoryRoot, 'scripts/sync-skill-links.mjs')

function exists(path) {
  try {
    lstatSync(path)
    return true
  } catch (error) {
    if (error.code === 'ENOENT' || error.code === 'ENOTDIR') {
      return false
    }
    throw error
  }
}

function writeSkill(sourceRoot, name, body = '# Skill\n') {
  const directory = join(sourceRoot, name)
  mkdirSync(directory, { recursive: true })
  writeFileSync(
    join(directory, 'SKILL.md'),
    `---\nname: ${name}\ndescription: Test skill.\n---\n\n${body}`,
  )
}

function command(commandName, args, paths, expectedStatus = 0, env = {}) {
  const result = spawnSync(commandName, args, {
    encoding: 'utf8',
    env: {
      ...process.env,
      GIT_CONFIG_NOSYSTEM: '1',
      GIT_CONFIG_GLOBAL: paths.globalConfig,
      ...env,
    },
  })
  assert.equal(
    result.status,
    expectedStatus,
    `command: ${commandName} ${args.join(' ')}\n` +
      `stdout:\n${result.stdout}\nstderr:\n${result.stderr}`,
  )
  return result
}

function git(paths, args, expectedStatus = 0, env = {}) {
  return command('git', ['-C', paths.repoRoot, ...args], paths, expectedStatus, env)
}

function gitValue(paths, key) {
  const result = spawnSync(
    'git',
    ['-C', paths.repoRoot, 'config', '--local', '--get', key],
    {
      encoding: 'utf8',
      env: {
        ...process.env,
        GIT_CONFIG_NOSYSTEM: '1',
        GIT_CONFIG_GLOBAL: paths.globalConfig,
      },
    },
  )
  assert.ok(
    result.status === 0 || result.status === 1,
    `git config failed: ${result.stderr}`,
  )
  return result.status === 0 ? result.stdout.trim() : null
}

function run(
  commandName,
  paths,
  {
    expectedStatus = 0,
    source = paths.sourceRoot,
    target = paths.targetRoot,
    state = paths.stateFile,
    hooks = false,
    ifInstalled = false,
    quiet = false,
  } = {},
) {
  const args = [script, commandName]
  if (source !== null) {
    args.push('--source', source)
  }
  if (target !== null) {
    args.push('--target', target)
  }
  if (state !== null) {
    args.push('--state', state)
  }
  if (!hooks) {
    args.push('--no-hooks')
  }
  if (ifInstalled) {
    args.push('--if-installed')
  }
  if (quiet) {
    args.push('--quiet')
  }
  return command(
    process.execPath,
    args,
    paths,
    expectedStatus,
    { JUNERDD_SKILL_LINKS_REPO_ROOT: paths.repoRoot },
  )
}

function fixture({ skills = ['alpha'], initializeTarget = true } = {}) {
  const root = mkdtempSync(join(tmpdir(), 'junerdd-skill-links-'))
  const paths = {
    root,
    repoRoot: join(root, 'repo'),
    targetRoot: join(root, 'home/.agents/skills'),
    stateFile: join(root, 'state/link-install.json'),
    globalConfig: join(root, 'global.gitconfig'),
  }
  paths.sourceRoot = join(paths.repoRoot, 'skills')
  mkdirSync(paths.repoRoot, { recursive: true })
  writeFileSync(paths.globalConfig, '')
  command('git', ['init', '-b', 'main', paths.repoRoot], paths)
  git(paths, ['config', 'user.name', 'Skill Link Tests'])
  git(paths, ['config', 'user.email', 'skill-links@example.invalid'])
  mkdirSync(paths.sourceRoot, { recursive: true })
  if (initializeTarget) {
    mkdirSync(paths.targetRoot, { recursive: true })
  }
  for (const name of skills) {
    writeSkill(paths.sourceRoot, name)
  }
  return paths
}

function cleanup(t, ...paths) {
  for (const path of paths) {
    t.after(() => rmSync(path.root, { recursive: true, force: true }))
  }
}

test('install, sync, doctor, and uninstall manage a flat live link farm', (t) => {
  const paths = fixture({ skills: ['alpha', 'beta'] })
  cleanup(t, paths)
  mkdirSync(join(paths.targetRoot, 'unmanaged'))
  symlinkSync(paths.sourceRoot, join(paths.targetRoot, 'junerdd-skill'), 'dir')

  const installed = run('install', paths)
  assert.match(installed.stdout, /Synchronized 2 skill links/)
  assert.equal(
    realpathSync(join(paths.targetRoot, 'alpha')),
    realpathSync(join(paths.sourceRoot, 'alpha')),
  )
  assert.equal(lstatSync(join(paths.targetRoot, 'unmanaged')).isDirectory(), true)
  assert.equal(exists(join(paths.targetRoot, 'junerdd-skill')), false)

  writeSkill(paths.sourceRoot, 'alpha', '# Alpha v2\n')
  assert.match(
    readFileSync(join(paths.targetRoot, 'alpha/SKILL.md'), 'utf8'),
    /Alpha v2/,
  )

  writeSkill(paths.sourceRoot, 'gamma')
  rmSync(join(paths.sourceRoot, 'beta'), { recursive: true })
  const synced = run('sync', paths)
  assert.match(synced.stdout, /Created: gamma/)
  assert.match(synced.stdout, /Removed stale links: beta/)
  assert.equal(exists(join(paths.targetRoot, 'beta')), false)

  run('doctor', paths)
  const uninstalled = run('uninstall', paths)
  assert.match(uninstalled.stdout, /Removed 2 managed skill links/)
  assert.equal(lstatSync(join(paths.targetRoot, 'unmanaged')).isDirectory(), true)
  assert.equal(exists(paths.stateFile), false)
  assert.equal(gitValue(paths, 'junerdd.skillLinksRepositoryId'), null)
  assert.equal(gitValue(paths, 'junerdd.skillLinksState'), null)
})

test('install refuses to replace an unmanaged name collision', (t) => {
  const paths = fixture()
  cleanup(t, paths)
  mkdirSync(join(paths.targetRoot, 'alpha'))
  writeFileSync(join(paths.targetRoot, 'alpha/owner.txt'), 'someone else\n')

  const result = run('install', paths, { expectedStatus: 1 })
  assert.match(result.stderr, /Refusing to replace unmanaged skill entries/)
  assert.equal(
    readFileSync(join(paths.targetRoot, 'alpha/owner.txt'), 'utf8'),
    'someone else\n',
  )
  assert.equal(exists(paths.stateFile), false)
  assert.equal(gitValue(paths, 'junerdd.skillLinksRepositoryId'), null)
})

test('sync preserves a former managed path after the user replaces it', (t) => {
  const paths = fixture({ skills: ['alpha', 'beta'] })
  cleanup(t, paths)
  run('install', paths)

  rmSync(join(paths.targetRoot, 'beta'))
  mkdirSync(join(paths.targetRoot, 'beta'))
  writeFileSync(join(paths.targetRoot, 'beta/owner.txt'), 'user-owned\n')
  rmSync(join(paths.sourceRoot, 'beta'), { recursive: true })

  const result = run('sync', paths)
  assert.match(result.stderr, /preserved changed or unowned former link/)
  assert.equal(
    readFileSync(join(paths.targetRoot, 'beta/owner.txt'), 'utf8'),
    'user-owned\n',
  )
})

test('sync recreates a missing target and uninstall tolerates missing trees', async (t) => {
  await t.test('sync recreates the discovery directory', () => {
    const paths = fixture()
    t.after(() => rmSync(paths.root, { recursive: true, force: true }))
    run('install', paths)
    rmSync(paths.targetRoot, { recursive: true })

    run('sync', paths, { source: null, target: null })
    assert.equal(
      realpathSync(join(paths.targetRoot, 'alpha')),
      realpathSync(join(paths.sourceRoot, 'alpha')),
    )
  })

  await t.test('uninstall still cleans metadata', () => {
    const paths = fixture()
    t.after(() => rmSync(paths.root, { recursive: true, force: true }))
    run('install', paths)
    rmSync(paths.targetRoot, { recursive: true })
    rmSync(paths.sourceRoot, { recursive: true })

    run('uninstall', paths, { source: null, target: null })
    assert.equal(exists(paths.stateFile), false)
    assert.equal(gitValue(paths, 'junerdd.skillLinksRepositoryId'), null)
    assert.equal(gitValue(paths, 'junerdd.skillLinksState'), null)
  })
})

test('equivalent target aliases retain desired links', (t) => {
  const paths = fixture({ initializeTarget: false })
  cleanup(t, paths)
  const physicalParent = join(paths.root, 'physical')
  const aliasParent = join(paths.root, 'alias')
  mkdirSync(physicalParent)
  symlinkSync(physicalParent, aliasParent, 'dir')
  const aliasedTarget = join(aliasParent, 'skills')
  const physicalTarget = join(physicalParent, 'skills')

  run('install', paths, { target: aliasedTarget })
  run('install', paths, { target: physicalTarget })

  assert.equal(
    realpathSync(join(physicalTarget, 'alpha')),
    realpathSync(join(paths.sourceRoot, 'alpha')),
  )
  const state = JSON.parse(readFileSync(paths.stateFile, 'utf8'))
  assert.equal(state.targetRoot, realpathSync(physicalTarget))
})

test('state write failures roll back install and sync link mutations', (t) => {
  if (typeof process.getuid === 'function' && process.getuid() === 0) {
    t.skip('permission failure fixture requires a non-root user')
    return
  }
  const paths = fixture()
  cleanup(t, paths)
  const stateDirectory = dirname(paths.stateFile)
  mkdirSync(stateDirectory, { recursive: true })
  chmodSync(stateDirectory, 0o500)

  const failedInstall = run('install', paths, { expectedStatus: 1 })
  assert.match(failedInstall.stderr, /(EACCES|permission denied)/i)
  assert.equal(exists(join(paths.targetRoot, 'alpha')), false)
  assert.equal(exists(paths.stateFile), false)
  assert.equal(gitValue(paths, 'junerdd.skillLinksRepositoryId'), null)

  chmodSync(stateDirectory, 0o700)
  run('install', paths)
  writeSkill(paths.sourceRoot, 'beta')
  chmodSync(stateDirectory, 0o500)
  const failedSync = run('sync', paths, { expectedStatus: 1 })
  assert.match(failedSync.stderr, /(EACCES|permission denied)/i)
  assert.equal(exists(join(paths.targetRoot, 'beta')), false)
  const state = JSON.parse(readFileSync(paths.stateFile, 'utf8'))
  assert.deepEqual(state.links, ['alpha'])
  chmodSync(stateDirectory, 0o700)
})

test('managed hook snapshot is branch-independent and self-diagnosing', (t) => {
  const paths = fixture()
  cleanup(t, paths)
  git(paths, ['add', 'skills'])
  git(paths, ['commit', '-m', 'safe'])
  git(paths, ['switch', '-c', 'attacker'])
  writeSkill(paths.sourceRoot, 'beta')
  const marker = join(paths.root, 'attacker-hook-ran')
  const attackerHook = join(paths.repoRoot, '.githooks/post-checkout')
  mkdirSync(dirname(attackerHook), { recursive: true })
  writeFileSync(attackerHook, `#!/bin/sh\n: > '${marker}'\n`, { mode: 0o700 })
  git(paths, ['add', 'skills', '.githooks'])
  git(paths, ['commit', '-m', 'attacker'])
  git(paths, ['switch', 'main'])

  run('install', paths, { hooks: true, source: null })
  const hooksPath = gitValue(paths, 'core.hooksPath')
  assert.ok(hooksPath)
  assert.equal(hooksPath.startsWith(paths.repoRoot), false)
  assert.equal(exists(join(hooksPath, 'post-checkout')), true)

  git(paths, ['switch', 'attacker'])
  assert.equal(exists(marker), false)
  assert.equal(
    realpathSync(join(paths.targetRoot, 'beta')),
    realpathSync(join(paths.sourceRoot, 'beta')),
  )
  run('doctor', paths, { hooks: true, source: null })

  rmSync(join(hooksPath, 'post-merge'))
  const unhealthy = run('doctor', paths, {
    hooks: true,
    source: null,
    expectedStatus: 1,
  })
  assert.match(unhealthy.stderr, /Managed Git hook is missing/)
  run('install', paths, { hooks: true, source: null })

  const assetsRoot = JSON.parse(readFileSync(paths.stateFile, 'utf8')).hooks.assetsRoot
  run('uninstall', paths, { hooks: true, source: null })
  assert.equal(gitValue(paths, 'core.hooksPath'), null)
  assert.equal(exists(assetsRoot), false)
})

test('legacy worktree hooks migrate to the managed snapshot', (t) => {
  const paths = fixture()
  cleanup(t, paths)
  symlinkSync(
    join(paths.sourceRoot, 'alpha'),
    join(paths.targetRoot, 'alpha'),
    'dir',
  )
  const legacyState = {
    schemaVersion: 1,
    collection: 'JUNERDD/skills',
    repoRoot: paths.repoRoot,
    sourceRoot: paths.sourceRoot,
    targetRoot: paths.targetRoot,
    links: ['alpha'],
    hooks: {
      path: '.githooks',
      repoRoot: paths.repoRoot,
      configuredByInstaller: true,
      previousPath: null,
      metadataConfiguredByInstaller: true,
      nodePath: process.execPath,
      stateFile: paths.stateFile,
      previousNodePath: null,
      previousStateFile: null,
    },
    updatedAt: new Date().toISOString(),
  }
  mkdirSync(dirname(paths.stateFile), { recursive: true })
  writeFileSync(paths.stateFile, JSON.stringify(legacyState))
  git(paths, ['config', '--local', 'core.hooksPath', '.githooks'])
  git(paths, ['config', '--local', 'junerdd.skillLinksNode', process.execPath])
  git(paths, ['config', '--local', 'junerdd.skillLinksState', paths.stateFile])

  run('install', paths, { hooks: true, source: null })
  const migrated = JSON.parse(readFileSync(paths.stateFile, 'utf8'))
  assert.ok(migrated.installation.repositoryId)
  assert.equal(migrated.hooks.path.startsWith(paths.repoRoot), false)
  assert.equal(gitValue(paths, 'core.hooksPath'), migrated.hooks.path)
  run('doctor', paths, { hooks: true, source: null })

  run('uninstall', paths, { hooks: true, source: null })
  assert.equal(gitValue(paths, 'core.hooksPath'), null)
  assert.equal(gitValue(paths, 'junerdd.skillLinksNode'), null)
  assert.equal(gitValue(paths, 'junerdd.skillLinksRepositoryId'), null)
  assert.equal(gitValue(paths, 'junerdd.skillLinksState'), null)
})

test('effective custom hook configuration is preserved across scopes', async (t) => {
  await t.test('global scope', () => {
    const paths = fixture()
    t.after(() => rmSync(paths.root, { recursive: true, force: true }))
    command(
      'git',
      ['config', '--file', paths.globalConfig, 'core.hooksPath', 'global-hooks'],
      paths,
    )
    const result = run('install', paths, { hooks: true, expectedStatus: 1 })
    assert.match(result.stderr, /core\.hooksPath is already set to global-hooks/)
    assert.equal(gitValue(paths, 'core.hooksPath'), null)
    assert.equal(exists(join(paths.targetRoot, 'alpha')), false)
  })

  await t.test('worktree scope', () => {
    const paths = fixture()
    t.after(() => rmSync(paths.root, { recursive: true, force: true }))
    git(paths, ['config', 'extensions.worktreeConfig', 'true'])
    git(paths, ['config', '--worktree', 'core.hooksPath', 'worktree-hooks'])
    const result = run('install', paths, { hooks: true, expectedStatus: 1 })
    assert.match(result.stderr, /core\.hooksPath is already set to worktree-hooks/)
    assert.equal(exists(join(paths.targetRoot, 'alpha')), false)
  })

  await t.test('explicit empty local value', () => {
    const paths = fixture()
    t.after(() => rmSync(paths.root, { recursive: true, force: true }))
    git(paths, ['config', '--local', 'core.hooksPath', ''])
    const result = run('install', paths, { hooks: true, expectedStatus: 1 })
    assert.match(result.stderr, /core\.hooksPath is already set to <empty>/)
    assert.equal(gitValue(paths, 'core.hooksPath'), '')
    assert.equal(exists(join(paths.targetRoot, 'alpha')), false)
  })
})

test('symlinked default hook directories are inspected and preserved', (t) => {
  const paths = fixture()
  cleanup(t, paths)
  const defaultHooks = join(paths.repoRoot, '.git/hooks')
  const sharedHooks = join(paths.root, 'shared-hooks')
  rmSync(defaultHooks, { recursive: true, force: true })
  mkdirSync(sharedHooks)
  writeFileSync(join(sharedHooks, 'post-commit'), '#!/bin/sh\nexit 0\n', { mode: 0o700 })
  symlinkSync(sharedHooks, defaultHooks, 'dir')

  const result = run('install', paths, { hooks: true, expectedStatus: 1 })
  assert.match(result.stderr, /Refusing to hide active hooks in \.git\/hooks: post-commit/)
  assert.equal(gitValue(paths, 'core.hooksPath'), null)
  assert.equal(exists(join(paths.targetRoot, 'alpha')), false)
})

test('automatic hooks synchronize a custom source', (t) => {
  const paths = fixture()
  cleanup(t, paths)
  const customSource = join(paths.root, 'external-skills')
  mkdirSync(customSource)
  writeSkill(customSource, 'custom-alpha')

  run('install', paths, { hooks: true, source: customSource })
  writeSkill(customSource, 'custom-beta')
  git(paths, ['hook', 'run', 'post-commit'])

  assert.equal(
    realpathSync(join(paths.targetRoot, 'custom-beta')),
    realpathSync(join(customSource, 'custom-beta')),
  )
  run('doctor', paths, { hooks: true, source: null })
  run('uninstall', paths, { hooks: true, source: null })
})

test('uninstall refuses state owned by another checkout', (t) => {
  const first = fixture()
  const second = fixture()
  cleanup(t, first, second)
  run('install', first)

  run('uninstall', second, {
    state: first.stateFile,
    target: first.targetRoot,
    ifInstalled: true,
  })
  assert.equal(exists(join(first.targetRoot, 'alpha')), true)
  assert.equal(exists(first.stateFile), true)

  const refused = run('uninstall', second, {
    state: first.stateFile,
    target: first.targetRoot,
    expectedStatus: 1,
  })
  assert.match(refused.stderr, /belongs to another checkout/)
  assert.equal(exists(join(first.targetRoot, 'alpha')), true)
  run('uninstall', first)
})

test('repository and state path migrations retain cleanup ownership', async (t) => {
  await t.test('moved checkout', () => {
    const paths = fixture()
    t.after(() => rmSync(paths.root, { recursive: true, force: true }))
    run('install', paths, { source: null })
    const movedRoot = join(paths.root, 'repo-moved')
    renameSync(paths.repoRoot, movedRoot)
    paths.repoRoot = movedRoot
    paths.sourceRoot = join(movedRoot, 'skills')

    run('sync', paths, { source: null })
    assert.equal(
      realpathSync(join(paths.targetRoot, 'alpha')),
      realpathSync(join(paths.sourceRoot, 'alpha')),
    )
    run('install', paths, { source: null })
    run('uninstall', paths, { source: null })
    assert.equal(gitValue(paths, 'junerdd.skillLinksRepositoryId'), null)
    assert.equal(gitValue(paths, 'junerdd.skillLinksState'), null)
  })

  await t.test('relocated state', () => {
    const paths = fixture()
    t.after(() => rmSync(paths.root, { recursive: true, force: true }))
    const firstState = paths.stateFile
    run('install', paths, { hooks: true })
    const firstAssets = JSON.parse(readFileSync(firstState, 'utf8')).hooks.assetsRoot
    const secondState = join(paths.root, 'relocated/install.json')

    run('install', paths, { hooks: true, state: secondState })
    assert.equal(exists(firstState), false)
    assert.equal(exists(firstAssets), false)
    assert.equal(gitValue(paths, 'junerdd.skillLinksState'), secondState)

    run('uninstall', paths, { hooks: true, state: secondState })
    assert.equal(gitValue(paths, 'core.hooksPath'), null)
    assert.equal(gitValue(paths, 'junerdd.skillLinksNode'), null)
    assert.equal(gitValue(paths, 'junerdd.skillLinksRepositoryId'), null)
    assert.equal(gitValue(paths, 'junerdd.skillLinksState'), null)
  })
})

test('state paths inside source or target are rejected before mutation', async (t) => {
  await t.test('below a managed link', () => {
    const paths = fixture()
    t.after(() => rmSync(paths.root, { recursive: true, force: true }))
    const unsafeState = join(paths.targetRoot, 'alpha/install.json')
    const result = run('install', paths, { state: unsafeState, expectedStatus: 1 })
    assert.match(result.stderr, /must be outside the repository, source, and target trees/)
    assert.equal(exists(join(paths.targetRoot, 'alpha')), false)
    assert.equal(exists(join(paths.sourceRoot, 'alpha/install.json')), false)
    assert.equal(gitValue(paths, 'junerdd.skillLinksRepositoryId'), null)
  })

  await t.test('inside the source tree', () => {
    const paths = fixture()
    t.after(() => rmSync(paths.root, { recursive: true, force: true }))
    const unsafeState = join(paths.sourceRoot, 'install.json')
    const result = run('install', paths, { state: unsafeState, expectedStatus: 1 })
    assert.match(result.stderr, /must be outside the repository, source, and target trees/)
    assert.equal(exists(unsafeState), false)
    assert.equal(exists(join(paths.targetRoot, 'alpha')), false)
  })

  await t.test('inside the repository outside skills', () => {
    const paths = fixture()
    t.after(() => rmSync(paths.root, { recursive: true, force: true }))
    const unsafeState = join(paths.repoRoot, '.state/install.json')
    const result = run('install', paths, {
      hooks: true,
      state: unsafeState,
      expectedStatus: 1,
    })
    assert.match(result.stderr, /must be outside the repository, source, and target trees/)
    assert.equal(exists(unsafeState), false)
    assert.equal(gitValue(paths, 'core.hooksPath'), null)
  })
})
