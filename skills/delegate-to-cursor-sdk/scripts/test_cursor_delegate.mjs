#!/usr/bin/env node
import assert from "node:assert/strict";
import fs from "node:fs";
import fsp from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";

const skillRoot = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const repoRoot = path.resolve(skillRoot, "../..");
const script = path.join(skillRoot, "scripts", "cursor_delegate.mjs");

function run(args, options = {}) {
  return spawnSync(process.execPath, [script, ...args], {
    cwd: skillRoot,
    encoding: "utf8",
    env: { ...process.env, ...options.env },
  });
}

async function withTempDir(fn) {
  const dir = await fsp.mkdtemp(path.join(os.tmpdir(), "cursor-sdk-delegate-test-"));
  try {
    await fn(dir);
  } finally {
    await fsp.rm(dir, { recursive: true, force: true });
  }
}

await withTempDir(async (tempDir) => {
  const workspace = path.join(tempDir, "repo");
  await fsp.mkdir(workspace);
  await fsp.writeFile(path.join(workspace, "README.md"), "# repo\n", "utf8");
  const taskFile = path.join(tempDir, "task.md");
  await fsp.writeFile(taskFile, [
    "# Cursor Direct Implementation Task Packet",
    "",
    "## Master Direct Implementation Instructions",
    "Inspect only.",
    "",
  ].join("\n"), "utf8");

  const result = run([
    "--workspace", workspace,
    "--task-file", taskFile,
    "--dry-run",
    "--inspect-only",
  ]);

  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /Cursor SDK dispatch dry run/);
  assert.match(result.stdout, /"workspaceCopy": true/);
  assert.match(result.stdout, /"modelLabel": "composer-2\.5 fast=true"/);
  assert.match(result.stdout, /--- BEGIN BOUNDED TASK PACKET ---/);
});

await withTempDir(async (tempDir) => {
  const workspace = path.join(tempDir, "repo");
  await fsp.mkdir(workspace);
  const taskFile = path.join(tempDir, "task.md");
  await fsp.writeFile(taskFile, [
    "# Cursor Direct Implementation Task Packet",
    "",
    "## Master Direct Implementation Instructions",
    "Implement.",
    "",
  ].join("\n"), "utf8");

  const result = run([
    "--workspace", workspace,
    "--task-file", taskFile,
    "--dry-run",
    "--model", "other-model",
  ]);

  assert.equal(result.status, 2);
  assert.match(result.stderr, /Refusing Cursor model override/);
});

await withTempDir(async (tempDir) => {
  const workspace = path.join(tempDir, "repo");
  await fsp.mkdir(workspace);
  const taskFile = path.join(tempDir, "task.md");
  await fsp.writeFile(taskFile, [
    "# Cursor Direct Implementation Task Packet",
    "",
    "No authority section.",
    "",
  ].join("\n"), "utf8");

  const result = run([
    "--workspace", workspace,
    "--task-file", taskFile,
    "--dry-run",
  ]);

  assert.equal(result.status, 2);
  assert.match(result.stderr, /Refusing dispatch/);
});

{
  const skillMd = await fsp.readFile(path.join(skillRoot, "SKILL.md"), "utf8");
  const openaiYaml = await fsp.readFile(path.join(skillRoot, "agents", "openai.yaml"), "utf8");
  const packageJson = await fsp.readFile(path.join(skillRoot, "package.json"), "utf8");
  const readme = await fsp.readFile(path.join(repoRoot, "README.md"), "utf8");
  const webData = await fsp.readFile(path.join(repoRoot, "web", "src", "lib", "skills-data.ts"), "utf8");
  const wrapper = await fsp.readFile(script, "utf8");
  const checkedText = [skillMd, openaiYaml, packageJson, readme, webData, wrapper].join("\n");

  assert.match(skillMd, /^name: delegate-to-cursor-sdk$/m);
  assert.match(openaiYaml, /\$delegate-to-cursor-sdk/);
  assert.match(packageJson, /"name": "delegate-to-cursor-sdk-skill"/);
  assert.match(readme, /skills\/delegate-to-cursor-sdk\/scripts\/cursor_delegate\.mjs/);
  assert.match(webData, /skills\/delegate-to-cursor-sdk\/scripts\/cursor_delegate\.mjs/);
  assert.doesNotMatch(checkedText, /delegate-to-cursor-composer|cursor_delegate\.py|Cursor CLI|Cursor Composer|stream-json|headless/);

  const sdkImportIndex = wrapper.indexOf("const sdk = await importCursorSdk();");
  const logDirIndex = wrapper.indexOf("const runDir = await makeLogDir(logBase);");
  const authIndex = wrapper.indexOf('apiKey = await resolveApiKey(args, "missing");');
  assert.ok(sdkImportIndex > -1, "wrapper imports @cursor/sdk before dispatch");
  assert.ok(sdkImportIndex < logDirIndex, "SDK dependency preflight should happen before log setup");
  assert.ok(sdkImportIndex < authIndex, "SDK dependency preflight should happen before API-key authorization");
}

console.log("cursor_delegate.mjs offline tests passed");
