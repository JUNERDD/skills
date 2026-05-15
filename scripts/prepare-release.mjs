#!/usr/bin/env node
import { readFileSync, writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const versionFile = resolve(root, 'VERSION')
const changelogFile = resolve(root, 'CHANGELOG.md')
const semverPattern = /^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$/

function readText(path) {
  return readFileSync(path, 'utf8')
}

function writeText(path, content) {
  writeFileSync(path, content)
}

function normalizeVersion(rawVersion) {
  const version = String(rawVersion || '').trim().replace(/^v/, '')
  if (!semverPattern.test(version)) {
    throw new Error(`Release version must be SemVer, received: ${rawVersion}`)
  }
  return version
}

function releaseDate() {
  return (
    process.env.RELEASE_DATE ||
    new Date().toISOString().slice(0, 10)
  )
}

function releaseNotes() {
  const notes = String(process.env.RELEASE_NOTES || '').trim()
  if (!notes) {
    throw new Error('RELEASE_NOTES is required')
  }

  return notes
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => (line.startsWith('- ') ? line : `- ${line}`))
    .join('\n')
}

function addChangelogEntry(version) {
  const changelog = readText(changelogFile)
  const heading = `## [${version}]`
  if (changelog.includes(heading)) {
    throw new Error(`CHANGELOG.md already contains ${heading}`)
  }

  const insertionPoint = changelog.search(/^## \[/m)
  if (insertionPoint === -1) {
    throw new Error('Could not find first release heading in CHANGELOG.md')
  }

  const entry = `## [${version}] - ${releaseDate()}\n\n### Changed\n\n${releaseNotes()}\n\n`
  writeText(
    changelogFile,
    `${changelog.slice(0, insertionPoint)}${entry}${changelog.slice(insertionPoint)}`,
  )
}

function run(command, args) {
  const result = spawnSync(command, args, {
    cwd: root,
    stdio: 'inherit',
  })
  if (result.status !== 0) {
    throw new Error(`${command} ${args.join(' ')} failed`)
  }
}

const version = normalizeVersion(process.argv[2])
writeText(versionFile, `${version}\n`)
run('node', ['scripts/sync-version.mjs'])
addChangelogEntry(version)
