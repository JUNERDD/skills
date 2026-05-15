#!/usr/bin/env node
import { readFileSync, writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const versionFile = resolve(root, 'VERSION')
const readmeFile = resolve(root, 'README.md')
const urlsFile = resolve(root, 'web/src/lib/content/urls.ts')
const semverPattern = /^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$/

function readText(path) {
  return readFileSync(path, 'utf8')
}

function writeText(path, content) {
  writeFileSync(path, content)
}

function replaceRequired(content, pattern, replacement, path) {
  if (!pattern.test(content)) {
    throw new Error(`Expected version pattern not found in ${path}`)
  }
  return content.replace(pattern, replacement)
}

function getVersion() {
  const version = readText(versionFile).trim()
  if (!semverPattern.test(version)) {
    throw new Error(`VERSION must be SemVer, received: ${version}`)
  }
  return version
}

function syncVersion(version) {
  const readme = replaceRequired(
    readText(readmeFile),
    /Current collection version: \[`[^`]+`\]\(\.\/VERSION\)\./,
    `Current collection version: [\`${version}\`](./VERSION).`,
    readmeFile,
  )
  writeText(readmeFile, readme)

  const urls = replaceRequired(
    readText(urlsFile),
    /export const COLLECTION_VERSION = "[^"]+";/,
    `export const COLLECTION_VERSION = "${version}";`,
    urlsFile,
  )
  writeText(urlsFile, urls)
}

syncVersion(getVersion())
