#!/usr/bin/env node
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const changelogFile = resolve(root, 'CHANGELOG.md')
const semverPattern = /^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$/

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function normalizeVersion(rawVersion) {
  const version = String(rawVersion || '').trim().replace(/^v/, '')
  if (!semverPattern.test(version)) {
    throw new Error(`Release version must be SemVer, received: ${rawVersion}`)
  }
  return version
}

const version = normalizeVersion(process.argv[2])
const changelog = readFileSync(changelogFile, 'utf8')
const headingPattern = new RegExp(`^## \\[${escapeRegExp(version)}\\] - .+$`, 'm')
const headingMatch = changelog.match(headingPattern)

if (!headingMatch || headingMatch.index === undefined) {
  throw new Error(`CHANGELOG.md does not contain a ${version} release entry`)
}

const entryStart = headingMatch.index + headingMatch[0].length
const remaining = changelog.slice(entryStart)
const nextEntryMatch = remaining.match(/^## \[/m)
const entryBody = nextEntryMatch
  ? remaining.slice(0, nextEntryMatch.index)
  : remaining
const notes = entryBody.trim()

if (!notes) {
  throw new Error(`CHANGELOG.md release entry for ${version} is empty`)
}

process.stdout.write(`${notes}\n`)
