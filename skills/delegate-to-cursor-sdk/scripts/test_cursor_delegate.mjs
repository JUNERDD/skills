#!/usr/bin/env node
import assert from "node:assert/strict";
import fs from "node:fs";
import fsp from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import {
  assertNoEscapingSymlinks,
  isDirectInvocation,
  modelSelectionFromArgs,
  modelSelectionsEqual,
  redactText,
  removeReadonlyCopySync,
  resolveModelInfoFromCatalog,
  updateStatusFromEvent,
  validateTaskPacketModel,
  verifyResolvedModel,
} from "./cursor_delegate.mjs";

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

function taskPacket({ authority = "Master Direct Implementation Instructions", model = "Grok 4.5 High", modelParams, profile, body = "Inspect only." } = {}) {
  const isDefault = model === "Grok 4.5 High";
  const lines = [
    "# Cursor Direct Implementation Task Packet",
    "",
    "## Cursor Model",
  ];
  lines.push(`- Wrapper profile: \`${profile || (isDefault ? "grok-4.5-high" : "explicit")}\``);
  lines.push(
    `- Model: \`${model}\``,
    `- Model params: \`${modelParams || (isDefault ? "catalog-resolved-high-default-speed" : "none")}\``,
    "",
    `## ${authority}`,
    body,
    "",
  );
  return lines.join("\n");
}

await withTempDir(async (tempDir) => {
  const workspace = path.join(tempDir, "repo");
  await fsp.mkdir(workspace);
  await fsp.writeFile(path.join(workspace, "README.md"), "# repo\n", "utf8");
  const taskFile = path.join(tempDir, "task.md");
  await fsp.writeFile(taskFile, taskPacket(), "utf8");

  const result = run([
    "--workspace", workspace,
    "--task-file", taskFile,
    "--dry-run",
    "--inspect-only",
  ]);

  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /Cursor SDK dispatch dry run/);
  assert.match(result.stdout, /"workspaceCopy": true/);
  assert.match(result.stdout, /"target": "grok-4\.5"/);
  assert.match(result.stdout, /"effort": "high"/);
  assert.doesNotMatch(result.stdout, /"fast":/);
  assert.match(result.stdout, /"modelLabel": "Grok 4\.5 High"/);
  assert.match(result.stdout, /"modelCatalogValidation": "deferred until authorized live dispatch"/);
  assert.match(result.stdout, /--- BEGIN BOUNDED TASK PACKET ---/);
});

await withTempDir(async (tempDir) => {
  const workspace = path.join(tempDir, "repo");
  await fsp.mkdir(workspace);
  const taskFile = path.join(tempDir, "task.md");
  await fsp.writeFile(taskFile, taskPacket({ model: "other-model", body: "Implement." }), "utf8");

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
  await fsp.writeFile(taskFile, taskPacket({ model: "grok-4.5", modelParams: "reasoning=medium" }), "utf8");

  const result = run([
    "--workspace", workspace,
    "--task-file", taskFile,
    "--dry-run",
    "--model", "grok-4.5",
    "--model-param", "reasoning=medium",
  ]);

  assert.equal(result.status, 2);
  assert.match(result.stderr, /Refusing Cursor model override/);
});

await withTempDir(async (tempDir) => {
  const workspace = path.join(tempDir, "repo");
  await fsp.mkdir(workspace);
  const taskFile = path.join(tempDir, "task.md");
  await fsp.writeFile(taskFile, taskPacket({ model: "other-model" }), "utf8");

  const result = run([
    "--workspace", workspace,
    "--task-file", taskFile,
    "--dry-run",
    "--model", "other-model",
    "--user-authorized-model",
    "--override-reason", "The user requested this model.",
  ]);

  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /"modelLabel": "other-model"/);
});

await withTempDir(async (tempDir) => {
  const workspace = path.join(tempDir, "repo");
  await fsp.mkdir(workspace);
  const taskFile = path.join(tempDir, "task.md");
  await fsp.writeFile(taskFile, [
    "# Cursor Direct Implementation Task Packet",
    "",
    "## Cursor Model",
    "- Wrapper profile: `grok-4.5-high`",
    "- Model: `Grok 4.5 High`",
    "- Model params: `catalog-resolved-high-default-speed`",
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

const catalog = [{
  id: "grok-4.5",
  displayName: "Cursor Grok 4.5",
  aliases: ["grok-4-5"],
  parameters: [
    { id: "reasoning", displayName: "Reasoning", values: [{ value: "low" }, { value: "high", displayName: "High" }] },
    { id: "fast", displayName: "Fast", values: [{ value: "false" }, { value: "true", displayName: "Fast" }] },
  ],
  variants: [
    { displayName: "High", params: [{ id: "reasoning", value: "high" }] },
    { displayName: "High Fast", params: [{ id: "reasoning", value: "high" }, { id: "fast", value: "true" }] },
  ],
}];

{
  const requested = modelSelectionFromArgs({});
  const resolved = resolveModelInfoFromCatalog(catalog, requested);
  assert.deepEqual(resolved.selection, {
    id: "grok-4.5",
    params: [{ id: "reasoning", value: "high" }],
  });
  assert.equal(resolved.label, "Grok 4.5 High");
  assert.equal(resolved.catalogVerified, true);
  assert.deepEqual(resolved.allowedObservedSpeedParams, [{ id: "fast", values: ["false", "true"] }]);
  assert.equal(modelSelectionsEqual(resolved.selection, {
    id: "grok-4.5",
    params: [{ id: "reasoning", value: "high" }],
  }), true);
  assert.equal(modelSelectionsEqual(resolved.selection, {
    id: "grok-4.5",
    params: [{ id: "reasoning", value: "high" }, { id: "fast", value: "false" }],
  }), false);
}

{
  const resolved = resolveModelInfoFromCatalog([{
  ...catalog[0],
  parameters: [
    catalog[0].parameters[0],
    { id: "fast", displayName: "Fast", values: [{ value: "true", displayName: "Fast" }] },
  ],
  variants: [catalog[0].variants[1]],
  }], modelSelectionFromArgs({}));
  assert.deepEqual(resolved.selection.params, [{ id: "reasoning", value: "high" }]);
  assert.deepEqual(resolved.allowedObservedSpeedParams, [{ id: "fast", values: ["true"] }]);
}

{
  const wrongCollision = { ...catalog[0], id: "grok45", displayName: "Wrong collision" };
  const resolved = resolveModelInfoFromCatalog([wrongCollision, catalog[0]], modelSelectionFromArgs({}));
  assert.equal(resolved.selection.id, "grok-4.5");
}

{
  const resolved = resolveModelInfoFromCatalog([{
    id: "grok-4.5",
    displayName: "Grok 4.5",
    parameters: [
      catalog[0].parameters[0],
      { id: "fast_cache", displayName: "Fast cache", values: [{ value: "off" }, { value: "on" }] },
      { id: "fast", displayName: "Fast", values: [{ value: "true", displayName: "Fast" }, { value: "false", displayName: "Standard" }] },
    ],
    variants: [{ displayName: "High", params: [{ id: "reasoning", value: "high" }] }],
  }], modelSelectionFromArgs({}));
  assert.deepEqual(resolved.selection.params, [{ id: "reasoning", value: "high" }]);
  assert.deepEqual(resolved.allowedObservedSpeedParams, [{ id: "fast", values: ["false", "true"] }]);
}

{
  const resolved = resolveModelInfoFromCatalog([{
    id: "grok-4.5",
    displayName: "Grok 4.5",
    parameters: [
      { id: "reasoning_cache", displayName: "Reasoning cache", values: [{ value: "low" }, { value: "high" }] },
      catalog[0].parameters[0],
      catalog[0].parameters[1],
    ],
    variants: [{ displayName: "High", params: [] }],
  }], modelSelectionFromArgs({}));
  assert.deepEqual(resolved.selection.params, [{ id: "reasoning", value: "high" }]);
}

assert.throws(() => resolveModelInfoFromCatalog([{
  ...catalog[0],
  variants: [{
    displayName: "High",
    params: [
      { id: "reasoning", value: "high" },
      { id: "fast", value: "false" },
      { id: "fast", value: "true" },
    ],
  }],
}], modelSelectionFromArgs({})), /duplicate model parameter id fast/);

{
  const resolved = resolveModelInfoFromCatalog([{
    ...catalog[0],
    variants: [
      { displayName: "High", params: [{ id: "reasoning", value: "high" }, { id: "fast", value: "true" }] },
      { displayName: "High", params: [{ id: "reasoning", value: "high" }, { id: "fast", value: "false" }] },
    ],
  }], modelSelectionFromArgs({}));
  assert.deepEqual(resolved.selection.params, [{ id: "reasoning", value: "high" }]);
  assert.deepEqual(resolved.allowedObservedSpeedParams, [{ id: "fast", values: ["false", "true"] }]);
}

{
  const resolved = resolveModelInfoFromCatalog([{
    id: "grok-4.5",
    displayName: "Grok 4.5",
    parameters: [
      { id: "reasoning", values: [{ value: "high" }] },
      {
        id: "speed_tier",
        displayName: "Speed tier",
        values: [
          { value: "turbo", displayName: "Fast" },
          { value: "standard", displayName: "Standard" },
        ],
      },
    ],
  }], modelSelectionFromArgs({}));
  assert.deepEqual(resolved.selection.params, [{ id: "reasoning", value: "high" }]);
  assert.deepEqual(resolved.allowedObservedSpeedParams, [{ id: "speed_tier", values: ["standard", "turbo"] }]);
}

for (const params of [
  [{ id: "reasoning", value: "high" }, { id: "is_fast", value: "true" }],
  [{ id: "reasoning", value: "high" }, { id: "use_fast", value: "true" }],
  [{ id: "reasoning", value: "high" }, { id: "fast_enabled", value: "true" }],
  [{ id: "reasoning", value: "high" }, { id: "speed_tier", value: "fast" }],
  [{ id: "reasoning", value: "high" }, { id: "latency", value: "fast" }],
]) {
  const resolved = resolveModelInfoFromCatalog([{
    id: "grok-4.5",
    displayName: "Grok 4.5",
    variants: [{ displayName: "High Fast", params }],
  }], modelSelectionFromArgs({}));
  assert.deepEqual(resolved.selection.params, [{ id: "reasoning", value: "high" }]);
}

for (const params of [
  [{ id: "reasoning_mode", value: "medium" }, { id: "fast", value: "false" }],
  [{ id: "thinking_effort", value: "medium" }, { id: "fast", value: "false" }],
]) {
  assert.throws(() => resolveModelInfoFromCatalog([{
    id: "grok-4.5",
    displayName: "Grok 4.5",
    variants: [{ displayName: "High", params }],
  }], modelSelectionFromArgs({})), /no unambiguous High parameter/);
}

for (const displayName of ["High No Fast", "High (Fast false)", "High Nonfast", "High Without Fast", "Deep"]) {
  const resolved = resolveModelInfoFromCatalog([{
    ...catalog[0],
    variants: [{
      displayName,
      params: [{ id: "reasoning", value: "high" }, { id: "fast", value: "false" }],
    }],
  }], modelSelectionFromArgs({}));
  assert.deepEqual(resolved.selection.params, [{ id: "reasoning", value: "high" }]);
}

{
  const resolved = resolveModelInfoFromCatalog([{
    id: "grok-4.5",
    displayName: "Grok 4.5",
    variants: [
      { displayName: "High", params: [{ id: "reasoning", value: "high" }, { id: "fast", value: "false" }] },
      { displayName: "High Fast", params: [{ id: "reasoning", value: "high" }, { id: "fast", value: "true" }] },
    ],
  }], modelSelectionFromArgs({}));
  assert.deepEqual(resolved.selection.params, [{ id: "reasoning", value: "high" }]);
}

assert.throws(() => resolveModelInfoFromCatalog([{
  id: "grok-4.5",
  displayName: "Grok 4.5",
  variants: [{ displayName: "High", params: [] }],
}], modelSelectionFromArgs({})), /no unambiguous High parameter/);

{
  const resolved = resolveModelInfoFromCatalog([{
    id: "grok-4.5",
    displayName: "Grok 4.5",
    parameters: [
      catalog[0].parameters[0],
      { id: "fast_network", values: [{ value: "false" }, { value: "true" }] },
      { id: "fast_mode", values: [{ value: "false" }, { value: "true" }] },
    ],
    variants: [{ displayName: "High", params: [{ id: "reasoning", value: "high" }] }],
  }], modelSelectionFromArgs({}));
  assert.deepEqual(resolved.selection.params, [{ id: "reasoning", value: "high" }]);
}

assert.throws(() => resolveModelInfoFromCatalog([{
  aliases: ["grok-4.5"],
  displayName: "Missing id",
  parameters: catalog[0].parameters,
  variants: catalog[0].variants,
}], modelSelectionFromArgs({})), /without a valid id/);

assert.match(validateTaskPacketModel(taskPacket(), modelSelectionFromArgs({})).message, /accepted/);
assert.equal(validateTaskPacketModel(taskPacket({ model: "Composer 2.5 Fast" }), modelSelectionFromArgs({})).ok, false);
assert.equal(validateTaskPacketModel(`${taskPacket()}\n## Cursor Model\n- Wrapper profile: \`grok-4.5-high\`\n- Model: \`Grok 4.5 High\`\n- Model params: \`catalog-resolved-high-default-speed\`\n`, modelSelectionFromArgs({})).ok, false);
assert.equal(validateTaskPacketModel(taskPacket({
  profile: "grok-4.5-high",
  model: "Grok 4.5 Medium",
  modelParams: "catalog-resolved-high-default-speed",
  body: "High risk; keep default speed.",
}), modelSelectionFromArgs({})).ok, false);
assert.equal(validateTaskPacketModel(taskPacket({ model: "gpt-5.4" }), modelSelectionFromArgs({ model: "gpt-5" })).ok, false);
assert.equal(validateTaskPacketModel(taskPacket({ model: "gpt-5", modelParams: "reasoning=low", body: "high" }), modelSelectionFromArgs({ model: "gpt-5", modelParam: ["reasoning=high"] })).ok, false);
assert.equal(validateTaskPacketModel([
  "# Cursor Direct Implementation Task Packet",
  "",
  "```markdown",
  "## Cursor Model",
  "- Wrapper profile: `grok-4.5-high`",
  "- Model: `Grok 4.5 High`",
  "- Model params: `catalog-resolved-high-default-speed`",
  "```",
  "",
  "## Master Direct Implementation Instructions",
  "Use a legacy model; the fenced block is only an example.",
].join("\n"), modelSelectionFromArgs({})).ok, false);
assert.equal(validateTaskPacketModel([
  "<!--",
  "## Cursor Model",
  "- Wrapper profile: `grok-4.5-high`",
  "- Model: `Grok 4.5 High`",
  "- Model params: `catalog-resolved-high-default-speed`",
  "-->",
  "## Master Direct Implementation Instructions",
  "Inspect only.",
].join("\n"), modelSelectionFromArgs({})).ok, false);
assert.equal(validateTaskPacketModel(`<!--\n\`\`\`markdown\n-->\n${taskPacket()}`, modelSelectionFromArgs({})).ok, true);
assert.equal(validateTaskPacketModel(`\`\`\`text\n<!--\n\`\`\`\n${taskPacket()}`, modelSelectionFromArgs({})).ok, true);
assert.equal(validateTaskPacketModel(`\`\`\`visible inline code\`\`\`\n${taskPacket()}`, modelSelectionFromArgs({})).ok, true);
assert.equal(validateTaskPacketModel(`\`<!--\`\n${taskPacket()}`, modelSelectionFromArgs({})).ok, true);
assert.equal(validateTaskPacketModel(`\`C:\\\`\n${taskPacket()}`, modelSelectionFromArgs({})).ok, true);
assert.throws(() => validateTaskPacketModel(`<script>\n${taskPacket()}\n</script>`, modelSelectionFromArgs({})), /raw HTML block/);
assert.throws(() => validateTaskPacketModel(`<script\n>\n${taskPacket()}`, modelSelectionFromArgs({})), /raw HTML block/);
assert.throws(() => validateTaskPacketModel(`\`\n${taskPacket()}\n\``, modelSelectionFromArgs({})), /multiline inline-code span/);

{
  const verified = verifyResolvedModel(
    { id: "grok-4.5", params: [{ id: "reasoning", value: "high" }, { id: "fast", value: "false" }] },
    { id: "grok-4.5", params: [{ id: "fast", value: "false" }, { id: "reasoning", value: "high" }] },
    { id: "grok-4.5", params: [{ id: "reasoning", value: "high" }, { id: "fast", value: "false" }] },
  );
  assert.equal(verified.verified, true);
  assert.equal(verifyResolvedModel({ id: "grok-4.5" }, undefined, { id: "grok-4.5" }).status, "unavailable");
  assert.equal(verifyResolvedModel({ id: "grok-4.5" }, { id: "other" }, { id: "grok-4.5" }).status, "mismatched");
  const defaultSpeedVerified = verifyResolvedModel(
    { id: "grok-4.5", params: [{ id: "reasoning", value: "high" }] },
    { id: "grok-4.5", params: [{ id: "reasoning", value: "high" }, { id: "fast", value: "true" }] },
    { id: "grok-4.5", params: [{ id: "reasoning", value: "high" }, { id: "speed_tier", value: "turbo" }] },
    {
      allowedAdditionalParams: [
        { id: "fast", values: ["false", "true"] },
        { id: "speed_tier", values: ["standard", "turbo"] },
      ],
    },
  );
  assert.equal(defaultSpeedVerified.verified, true);
  assert.equal(defaultSpeedVerified.scope, "requested_high_with_catalog_speed_defaults");
  assert.equal(verifyResolvedModel(
    { id: "grok-4.5", params: [{ id: "reasoning", value: "high" }] },
    { id: "grok-4.5", params: [{ id: "reasoning", value: "medium" }, { id: "fast", value: "true" }] },
    { id: "grok-4.5", params: [{ id: "reasoning", value: "high" }] },
    { allowedAdditionalParams: [{ id: "fast", values: ["false", "true"] }] },
  ).verified, false);
  assert.equal(verifyResolvedModel(
    { id: "grok-4.5", params: [{ id: "reasoning", value: "high" }] },
    { id: "grok-4.5", params: [{ id: "reasoning", value: "high" }, { id: "unrelated", value: "unsafe" }] },
    { id: "grok-4.5", params: [{ id: "reasoning", value: "high" }] },
    { allowedAdditionalParams: [{ id: "fast", values: ["false", "true"] }] },
  ).verified, false);
  assert.equal(verifyResolvedModel(
    { id: "grok-4.5", params: [{ id: "reasoning", value: "high" }] },
    { id: "grok-4.5", params: [{ id: "reasoning", value: "high" }, { id: "thinking_effort", value: "low" }] },
    { id: "grok-4.5", params: [{ id: "reasoning", value: "high" }] },
    { allowedAdditionalParams: [{ id: "fast", values: ["false", "true"] }] },
  ).verified, false);
  assert.equal(verifyResolvedModel(
    { id: "grok-4.5", params: [{ id: "reasoning", value: "high" }] },
    { id: "grok-4.5", params: [{ id: "reasoning", value: "high" }, { id: "fast", value: "maybe" }] },
    { id: "grok-4.5", params: [{ id: "reasoning", value: "high" }] },
    { allowedAdditionalParams: [{ id: "fast", values: ["false", "true"] }] },
  ).verified, false);
  assert.equal(verifyResolvedModel(
    { id: "grok-4.5", params: [{ id: "reasoning", value: "high" }] },
    { id: "grok-4.5", params: [{ id: "reasoning", value: "high" }, { id: "fast", value: "true" }] },
    { id: "grok-4.5", params: [{ id: "reasoning", value: "high" }, { id: "fast", value: "true" }] },
  ).verified, false);
  assert.equal(verifyResolvedModel(
    { id: "grok-4.5", params: [{ id: "fast", value: "false" }] },
    { id: "grok-4.5", params: [{ id: "fast", value: "true" }, { id: "fast", value: "false" }] },
    { id: "grok-4.5", params: [{ id: "fast", value: "true" }, { id: "fast", value: "false" }] },
  ).verified, false);
  for (const malformed of [
    { id: "grok-4.5", params: [{ id: "reasoning", value: "high" }, { id: "unrelated", value: 123 }] },
    { id: "grok-4.5", params: [{ id: "reasoning", value: "high" }, { id: "fast", value: true }] },
    { id: "grok-4.5", params: [{ id: "reasoning", value: "high" }, { id: null, value: "unsafe" }] },
    { id: "grok-4.5", params: { reasoning: "high" } },
  ]) {
    const malformedVerification = verifyResolvedModel(
      { id: "grok-4.5", params: [{ id: "reasoning", value: "high" }] },
      malformed,
      malformed,
      { allowedAdditionalParams: [{ id: "fast", values: ["false", "true"] }] },
    );
    assert.equal(malformedVerification.verified, false);
    assert.equal(malformedVerification.status, "mismatched");
  }
}

{
  const redacted = redactText("authorization: Bearer top-secret\napi_key=another-secret\nok=true");
  assert.doesNotMatch(redacted, /top-secret|another-secret/);
  assert.match(redacted, /authorization: <redacted>/);
  assert.match(redacted, /api_key=<redacted>/);
}

await withTempDir(async (tempDir) => {
  const workspace = path.join(tempDir, "repo");
  await fsp.mkdir(path.join(workspace, "internal"), { recursive: true });
  await fsp.symlink("internal", path.join(workspace, "safe-link"));
  assert.doesNotThrow(() => assertNoEscapingSymlinks(workspace));
  await fsp.symlink("..", path.join(workspace, "escape-link"));
  assert.throws(() => assertNoEscapingSymlinks(workspace), /symlink that can escape/);
});

await withTempDir(async (tempDir) => {
  const workspace = path.join(tempDir, "repo");
  await fsp.mkdir(workspace);
  await fsp.writeFile(path.join(workspace, "file.txt"), "source\n", "utf8");
  const reenteringTarget = path.join("..", "..", path.basename(tempDir), "repo", "file.txt");
  await fsp.symlink(reenteringTarget, path.join(workspace, "reentering-link"));
  assert.throws(() => assertNoEscapingSymlinks(workspace), /symlink that can escape/);
});

await withTempDir(async (tempDir) => {
  const copyRoot = path.join(tempDir, "copy");
  const nested = path.join(copyRoot, "nested");
  await fsp.mkdir(nested, { recursive: true });
  await fsp.writeFile(path.join(nested, "file.txt"), "readonly\n", "utf8");
  await fsp.chmod(path.join(nested, "file.txt"), 0o444);
  await fsp.chmod(nested, 0o555);
  await fsp.chmod(copyRoot, 0o555);
  removeReadonlyCopySync(copyRoot);
  assert.equal(fs.existsSync(copyRoot), false);
});

await withTempDir(async (tempDir) => {
  const symlink = path.join(tempDir, "delegate.mjs");
  await fsp.symlink(script, symlink);
  assert.equal(isDirectInvocation(symlink), true);
  const result = spawnSync(process.execPath, [symlink, "--help"], { encoding: "utf8" });
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /Usage: node scripts\/cursor_delegate\.mjs/);
});

await withTempDir(async (tempDir) => {
  const workspace = path.join(tempDir, "repo");
  const tmp = path.join(tempDir, "tmp");
  await fsp.mkdir(workspace);
  await fsp.mkdir(tmp);
  await fsp.writeFile(path.join(workspace, "README.md"), "# repo\n", "utf8");
  const taskFile = path.join(tempDir, "task.md");
  await fsp.writeFile(taskFile, taskPacket(), "utf8");
  const result = run([
    "--workspace", workspace,
    "--task-file", taskFile,
    "--inspect-only",
    "--auth-mode", "fail",
  ], { env: { TMPDIR: tmp, CURSOR_API_KEY: "" } });
  assert.notEqual(result.status, 0);
  const leftovers = (await fsp.readdir(tmp)).filter((name) => name.startsWith("cursor-sdk-delegate-readonly-"));
  assert.deepEqual(leftovers, []);
});

{
  const status = { active_subagents: {}, recent_subagents: [], recent_tool_calls: [], events_seen: 0 };
  updateStatusFromEvent(status, {
    type: "system",
    agent_id: "agent-root",
    run_id: "run-1",
    model: { id: "grok-4.5", params: [{ id: "reasoning", value: "high" }, { id: "fast", value: "false" }] },
  });
  assert.deepEqual(status.system_model_selection, {
    id: "grok-4.5",
    params: [{ id: "reasoning", value: "high" }, { id: "fast", value: "false" }],
  });
  updateStatusFromEvent(status, {
    type: "tool_call",
    call_id: "task-1",
    name: "task",
    status: "running",
    args: { description: "Review", model: "inherit" },
  });
  updateStatusFromEvent(status, {
    type: "tool_call",
    call_id: "task-1",
    name: "task",
    status: "completed",
    result: { status: "success", value: { agentId: "agent-1", isBackground: false, durationMs: 42 } },
  });
  assert.equal(status.active_subagents["task-1"], undefined);
  assert.deepEqual(status.recent_subagents.at(-1).result, {
    status: "success",
    agentId: "agent-1",
    isBackground: false,
    durationMs: 42,
  });
}

{
  const skillMd = await fsp.readFile(path.join(skillRoot, "SKILL.md"), "utf8");
  const openaiYaml = await fsp.readFile(path.join(skillRoot, "agents", "openai.yaml"), "utf8");
  const packageJson = await fsp.readFile(path.join(skillRoot, "package.json"), "utf8");
  const readme = await fsp.readFile(path.join(repoRoot, "README.md"), "utf8");
  const webData = await fsp.readFile(path.join(repoRoot, "web", "src", "lib", "skills-data.ts"), "utf8");
  const wrapper = await fsp.readFile(script, "utf8");
  const referenceDir = path.join(skillRoot, "references");
  const referenceFiles = (await fsp.readdir(referenceDir)).filter((file) => file.endsWith(".md")).sort();
  const references = await Promise.all(referenceFiles.map((file) => fsp.readFile(path.join(referenceDir, file), "utf8")));
  const readmeStart = readme.indexOf("### `delegate-to-cursor-sdk`");
  const readmeEnd = readme.indexOf("### `plan-mode`", readmeStart);
  const readmeEntry = readme.slice(readmeStart, readmeEnd);
  const webStart = webData.indexOf('slug: "delegate-to-cursor-sdk"');
  const webEnd = webData.indexOf('slug: "plan-mode"', webStart);
  const webEntry = webData.slice(webStart, webEnd);
  const skillSurface = [skillMd, openaiYaml, wrapper, ...references].join("\n");
  const publicSurface = [readmeEntry, webEntry].join("\n");

  assert.match(skillMd, /^name: delegate-to-cursor-sdk$/m);
  assert.match(openaiYaml, /\$delegate-to-cursor-sdk/);
  assert.match(openaiYaml, /allow_implicit_invocation: false/);
  assert.match(packageJson, /"name": "delegate-to-cursor-sdk-skill"/);
  assert.match(readmeEntry, /skills\/delegate-to-cursor-sdk\/scripts\/cursor_delegate\.mjs/);
  assert.match(webEntry, /skills\/delegate-to-cursor-sdk\/scripts\/cursor_delegate\.mjs/);
  assert.doesNotMatch(skillSurface, /composer[ -]?2\.5/i);
  assert.doesNotMatch(publicSurface, /composer[ -]?2\.5/i);
  assert.match(skillSurface, /grok-4\.5-high/i);
  assert.match(publicSurface, /Grok 4\.5 High/i);
  assert.doesNotMatch([skillSurface, publicSurface].join("\n"), /fast disabled|high non-fast|catalog-resolved-high-non-fast/i);
  assert.doesNotMatch([skillSurface, publicSurface].join("\n"), /delegate-to-cursor-composer|cursor_delegate\.py|Cursor CLI|Cursor Composer|stream-json/);

  const taskTemplates = referenceFiles.filter((file) => file.startsWith("task-"));
  for (const file of taskTemplates) {
    const text = await fsp.readFile(path.join(referenceDir, file), "utf8");
    assert.match(text, /Wrapper profile: `grok-4\.5-high`/, `${file} must use the default wrapper profile`);
    assert.match(text, /Model params: `catalog-resolved-high-default-speed`/, `${file} must declare High with Cursor-default speed`);
    assert.match(text, /speed parameter is omitted/i, `${file} must leave speed to Cursor`);
    assert.match(text, /exact High parameters are unverified/, `${file} must not overclaim internal-subagent model parameters`);
  }

  assert.match(wrapper, /Cursor\.models\.list/);
  assert.match(wrapper, /Agent\.resume\(args\.resumeAgentId, agentOptions\)/);
  assert.match(wrapper, /model: modelInfo\.selection, mode: sdkMode/);
  assert.match(wrapper, /result\.model/);

  const sdkImportIndex = wrapper.indexOf("const sdk = await importCursorSdk();");
  const logDirIndex = wrapper.indexOf("const runDir = await makeLogDir(logBase);");
  const authIndex = wrapper.indexOf('apiKey = await resolveApiKey(args, "missing");');
  assert.ok(sdkImportIndex > -1, "wrapper imports @cursor/sdk before dispatch");
  assert.ok(sdkImportIndex < logDirIndex, "SDK dependency preflight should happen before log setup");
  assert.ok(sdkImportIndex < authIndex, "SDK dependency preflight should happen before API-key authorization");
}

console.log("cursor_delegate.mjs offline tests passed");
