#!/usr/bin/env node
/**
 * Dispatch a bounded task packet to Cursor through the official @cursor/sdk package.
 *
 * This wrapper intentionally keeps API keys out of argv, logs, prompt files, and
 * metadata. Prefer CURSOR_API_KEY. When a key is missing or rejected and stdin is
 * interactive, the wrapper requests authorization with hidden terminal input.
 */

import { spawnSync } from "node:child_process";
import crypto from "node:crypto";
import fs from "node:fs";
import fsp from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { parseArgs } from "node:util";

const DEFAULT_MODEL_ALIAS = "composer-2.5-fast";
const DEFAULT_MODEL_ID = "composer-2.5";
const DEFAULT_FAST_PARAM = { id: "fast", value: "true" };
const STATUS_TEXT_LIMIT = 800;
const RECENT_TOOL_LIMIT = 12;
const RECENT_SUBAGENT_LIMIT = 12;

const AUTHORITY_HEADINGS = new Map([
  ["master-direct", "Master Direct Implementation Instructions"],
  ["non-cursor-planning-subagent", "Approved Upstream Plan"],
  ["orchestrator-subagent", "Approved Local Plan"],
  ["user-provided-plan", "User-Provided Approved Plan"],
  ["follow-up", "Cursor Follow-up Task Packet"],
]);
const FOLLOW_UP_REQUIRED_HEADINGS = ["Original Authority", "Review Findings to Address"];
const PLANNING_SOURCE_CHOICES = new Set(["auto", ...AUTHORITY_HEADINGS.keys()]);
const HEADING_RE = /^[ \t]{0,3}#{1,6}[ \t]+(.+?)[ \t]*#*[ \t]*$/gm;
const PLACEHOLDER_RE = /<([^>\n]{1,160})>/g;
const PLACEHOLDER_LEAD_WORDS = new Set([
  "accepted", "allowed", "api", "approved", "branch", "command", "concrete", "condition",
  "criterion", "description", "disabled", "exact", "explicit", "id", "item", "known",
  "log-dir", "local", "master-direct", "mode", "none", "non-goal", "one", "owner",
  "path", "purpose", "repo", "stable", "status", "step", "summarize", "user",
  "workspace", "0-2", "0-4",
]);
const SENSITIVE_KEY_RE = /(token|secret|api[_-]?key|authorization|cookie|password|credential|private[_-]?key)/i;
const SENSITIVE_ASSIGNMENT_RE = /(token|secret|api[_-]?key|authorization|cookie|password|credential|private[_-]?key)(\s*[:=]\s*)([^\s,;]+)/gi;

class UserFacingError extends Error {
  constructor(message, code = 2) {
    super(message);
    this.name = "UserFacingError";
    this.exitCode = code;
  }
}

function utcNow() {
  return new Date().toISOString();
}

function redactText(value, limit = STATUS_TEXT_LIMIT) {
  if (value === undefined || value === null) return undefined;
  const text = String(value).replace(SENSITIVE_ASSIGNMENT_RE, (_m, key, sep) => `${key}${sep}<redacted>`);
  return text.length <= limit ? text : `${text.slice(0, Math.max(0, limit - 1))}…`;
}

function redactUrl(value) {
  const text = String(value);
  try {
    const parsed = new URL(text);
    parsed.search = "";
    parsed.hash = "";
    parsed.username = "";
    parsed.password = "";
    return redactText(parsed.toString(), 240);
  } catch {
    return redactText(text, 240);
  }
}

function safeJson(value) {
  return JSON.stringify(value, (_key, item) => {
    if (typeof item === "bigint") return item.toString();
    return item;
  });
}

async function writeJson(file, data) {
  await fsp.mkdir(path.dirname(file), { recursive: true, mode: 0o700 });
  const tmp = `${file}.tmp`;
  await fsp.writeFile(tmp, `${JSON.stringify(data, null, 2)}\n`, "utf8");
  await fsp.rename(tmp, file);
}

function normalizeArray(value) {
  if (value === undefined) return [];
  return Array.isArray(value) ? value : [value];
}

function markdownHeadings(taskText) {
  const headings = [];
  HEADING_RE.lastIndex = 0;
  let match;
  while ((match = HEADING_RE.exec(taskText)) !== null) {
    const heading = match[1].trim().replace(/#+$/, "").trim();
    if (heading) headings.push(heading);
  }
  return headings;
}

function sectionBody(taskText, heading) {
  HEADING_RE.lastIndex = 0;
  const matches = [...taskText.matchAll(HEADING_RE)];
  for (let index = 0; index < matches.length; index += 1) {
    const match = matches[index];
    const current = match[1].trim().replace(/#+$/, "").trim();
    if (current !== heading) continue;
    const marker = match[0].trimStart();
    const level = marker.length - marker.replace(/^#+/, "").length;
    const start = match.index + match[0].length;
    let end = taskText.length;
    for (const nextMatch of matches.slice(index + 1)) {
      const nextMarker = nextMatch[0].trimStart();
      const nextLevel = nextMarker.length - nextMarker.replace(/^#+/, "").length;
      if (nextLevel <= level) {
        end = nextMatch.index;
        break;
      }
    }
    return taskText.slice(start, end).trim();
  }
  return "";
}

function looksLikeTemplatePlaceholder(token) {
  const normalized = token.trim().toLowerCase();
  if (!normalized) return false;
  if (/^\/[a-z][a-z0-9:-]*$/.test(normalized)) return false;
  if ([" ", "|", " or ", " if ", "/", "`"].some((separator) => normalized.includes(separator))) return true;
  const firstWord = normalized.split(/[^a-z0-9-]+/, 1)[0];
  return PLACEHOLDER_LEAD_WORDS.has(firstWord);
}

function placeholderTokens(taskText) {
  const found = new Set();
  PLACEHOLDER_RE.lastIndex = 0;
  let match;
  while ((match = PLACEHOLDER_RE.exec(taskText)) !== null) {
    if (looksLikeTemplatePlaceholder(match[1])) found.add(match[0]);
  }
  return [...found].sort();
}

function authoritySources(taskText) {
  const headings = markdownHeadings(taskText);
  const counts = new Map();
  for (const heading of headings) counts.set(heading, (counts.get(heading) || 0) + 1);
  return [...AUTHORITY_HEADINGS.entries()]
    .filter(([_source, heading]) => (counts.get(heading) || 0) > 0)
    .map(([source]) => source);
}

function validateAuthority(taskText, expected, allowPlaceholders) {
  const placeholders = placeholderTokens(taskText);
  if (placeholders.length > 0 && !allowPlaceholders) {
    return { ok: false, detected: undefined, message: `task packet contains ${placeholders.length} unresolved placeholder token(s)` };
  }

  const headings = markdownHeadings(taskText);
  const counts = new Map();
  for (const heading of headings) counts.set(heading, (counts.get(heading) || 0) + 1);
  for (const heading of AUTHORITY_HEADINGS.values()) {
    if ((counts.get(heading) || 0) > 1) {
      return { ok: false, detected: undefined, message: `authority heading appears more than once: ${heading}` };
    }
  }

  const sources = authoritySources(taskText);
  let detected;
  if (expected !== "auto") {
    if (sources.length !== 1 || sources[0] !== expected) {
      return { ok: false, detected: undefined, message: `expected exactly ${expected}; found ${sources.length ? JSON.stringify(sources) : "['none']"}` };
    }
    detected = expected;
  } else {
    if (sources.length !== 1) {
      return { ok: false, detected: undefined, message: `expected exactly one authority heading; found ${sources.length ? JSON.stringify(sources) : "['none']"}` };
    }
    [detected] = sources;
  }

  const authorityHeading = AUTHORITY_HEADINGS.get(detected);
  if (!sectionBody(taskText, authorityHeading)) {
    return { ok: false, detected: undefined, message: `authority section is empty: ${authorityHeading}` };
  }

  if (detected === "follow-up") {
    for (const required of FOLLOW_UP_REQUIRED_HEADINGS) {
      if (!sectionBody(taskText, required)) {
        return { ok: false, detected: undefined, message: `follow-up packet requires non-empty section: ${required}` };
      }
    }
  }
  return { ok: true, detected, message: "authority accepted" };
}

function describeAuthority(source) {
  const descriptions = {
    "master-direct": "The Master Direct Implementation Instructions section is the source of truth.",
    "non-cursor-planning-subagent": "The Approved Upstream Plan section is the source of truth after upstream review.",
    "orchestrator-subagent": "The Approved Local Plan section is the source of truth within its workstream contract.",
    "user-provided-plan": "The User-Provided Approved Plan section is the source of truth after upstream acceptance.",
    "follow-up": "The Cursor Follow-up Task Packet section is the source of truth for a narrow follow-up loop.",
  };
  return descriptions[source];
}

function parseKeyValue(input, optionName) {
  const index = input.indexOf("=");
  if (index <= 0) throw new UserFacingError(`${optionName} must use key=value syntax: ${input}`);
  return { id: input.slice(0, index), value: input.slice(index + 1) };
}

function modelSelectionFromArgs(args) {
  const modelInput = args.model || DEFAULT_MODEL_ALIAS;
  const params = normalizeArray(args.modelParam).map((item) => parseKeyValue(String(item), "--model-param"));
  let selection;
  let label;

  if (modelInput === "composer-2.5-fast") {
    selection = { id: DEFAULT_MODEL_ID, params: [DEFAULT_FAST_PARAM, ...params.filter((param) => param.id !== "fast")] };
    label = "composer-2.5 fast=true";
  } else {
    selection = params.length ? { id: modelInput, params } : { id: modelInput };
    label = params.length ? `${modelInput} ${params.map((p) => `${p.id}=${p.value}`).join(" ")}` : modelInput;
  }
  const isDefault = selection.id === DEFAULT_MODEL_ID && Array.isArray(selection.params) && selection.params.some((param) => param.id === "fast" && param.value === "true");
  return { selection, label, isDefault };
}

function parseSettingSources(values) {
  const allowed = new Set(["project", "user", "team", "mdm", "plugins", "all"]);
  const sources = normalizeArray(values);
  for (const source of sources) {
    if (!allowed.has(source)) throw new UserFacingError(`Invalid --setting-source ${source}`);
  }
  return sources.length ? sources : ["project"];
}

function parseRepoSpecs(values) {
  const repos = [];
  for (const value of normalizeArray(values)) {
    const [url, startingRef] = String(value).split("#", 2);
    if (!url) throw new UserFacingError("--repo-url cannot be empty");
    repos.push(startingRef ? { url, startingRef } : { url });
  }
  return repos;
}

function ensureDirWorkspace(workspace) {
  if (!fs.existsSync(workspace) || !fs.statSync(workspace).isDirectory()) {
    throw new UserFacingError(`Workspace does not exist or is not a directory: ${workspace}`);
  }
}

function runGitStatus(workspace) {
  const result = spawnSync("git", ["-C", workspace, "status", "--porcelain=v1"], { encoding: "utf8" });
  if (result.status !== 0) return { isGit: false, lines: [], error: (result.stderr || "").trim() };
  return { isGit: true, lines: result.stdout.split(/\r?\n/).filter((line) => line.trim()), error: "" };
}

function statusPath(line) {
  let value = line.length > 3 ? line.slice(3).trim() : "";
  if (value.includes(" -> ")) value = value.split(" -> ").at(-1);
  return value;
}

function relativeToWorkspace(file, workspace) {
  const rel = path.relative(fs.realpathSync(workspace), fs.realpathSync(file));
  return rel && !rel.startsWith("..") && !path.isAbsolute(rel) ? rel : undefined;
}

function filterIgnorableStatus(lines, workspace, taskFile) {
  let taskRel;
  try {
    taskRel = relativeToWorkspace(taskFile, workspace);
  } catch {
    taskRel = undefined;
  }
  return lines.filter((line) => {
    const candidate = statusPath(line);
    if (line.startsWith("??") && taskRel && candidate === taskRel) return false;
    if (line.startsWith("??") && candidate.startsWith(".agent/delegations/")) return false;
    return true;
  });
}

function collectUnsafeOverrides(args, modelInfo) {
  const flags = [];
  if (args.allowMissingAuthority) flags.push("--allow-missing-authority");
  if (args.allowPlaceholders) flags.push("--allow-placeholders");
  if (args.allowDirty) flags.push("--allow-dirty");
  if (args.allowNonGit) flags.push("--allow-non-git");
  if (args.sandbox === "disabled") flags.push("--sandbox disabled");
  if (args.workspaceCopy === "never" && !args.apply && args.runtime === "local") flags.push("--workspace-copy never");
  if (args.includeRawEvents) flags.push("--include-raw-events");
  if (args.keepWorkspaceCopy) flags.push("--keep-workspace-copy");
  if (!modelInfo.isDefault && args.userAuthorizedModel) flags.push("--user-authorized-model");
  return flags;
}

function copyIgnore(src) {
  const base = path.basename(src);
  return !new Set([
    ".git", ".agent", "node_modules", ".venv", "venv", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".next", "dist", "build",
  ]).has(base);
}

function chmodReadOnlyRecursive(root) {
  const entries = fs.readdirSync(root, { withFileTypes: true });
  for (const entry of entries) {
    const child = path.join(root, entry.name);
    if (entry.isSymbolicLink()) continue;
    if (entry.isDirectory()) chmodReadOnlyRecursive(child);
    try {
      const mode = fs.statSync(child).mode & 0o777;
      fs.chmodSync(child, mode & ~0o222);
    } catch {
      // Best-effort hardening only.
    }
  }
  try {
    const mode = fs.statSync(root).mode & 0o777;
    fs.chmodSync(root, mode & ~0o222);
  } catch {
    // Best-effort hardening only.
  }
}

function makeReadonlyCopy(workspace) {
  const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), "cursor-sdk-delegate-readonly-"));
  const target = path.join(tempRoot, path.basename(workspace));
  fs.cpSync(workspace, target, { recursive: true, dereference: false, filter: copyIgnore });
  chmodReadOnlyRecursive(target);
  return target;
}

function primitiveSummary(data, keys) {
  const summary = {};
  if (!data || typeof data !== "object") return summary;
  for (const key of keys) {
    if (!(key in data) || SENSITIVE_KEY_RE.test(key)) continue;
    const value = data[key];
    if (value === undefined || value === null) continue;
    if (typeof value === "string") summary[key] = key === "url" ? redactUrl(value) : redactText(value, 240);
    else if (["number", "boolean"].includes(typeof value)) summary[key] = value;
  }
  return summary;
}

function summarizeCommand(data) {
  const command = data?.command || data?.cmd;
  if (typeof command !== "string" || !command.trim()) return {};
  const first = command.trim().split(/\s+/, 1)[0];
  return { command_present: true, command_kind: redactText(first, 80) };
}

function safeToolArgs(event) {
  const args = event?.args;
  if (!args || typeof args !== "object") return {};
  if (event.name === "task" || event.name === "taskToolCall" || event.name === "Agent") {
    const summary = primitiveSummary(args, ["description", "model", "agentId", "mode", "environment", "readonly", "run_in_background"]);
    const attachments = args.attachments || args.file_attachments;
    if (Array.isArray(attachments)) summary.attachments_count = attachments.length;
    return summary;
  }
  return { ...primitiveSummary(args, ["path", "cwd", "pattern", "query", "url", "name"]), ...summarizeCommand(args) };
}

function safeToolResult(event) {
  const result = event?.result;
  if (!result || typeof result !== "object") return {};
  if (result.success && typeof result.success === "object") {
    const keys = (event.name === "task" || event.name === "taskToolCall" || event.name === "Agent")
      ? ["agentId", "isBackground", "durationMs"]
      : ["path", "linesCreated", "linesModified", "fileSize", "totalLines", "totalChars", "isEmpty", "exceededLimit"];
    return { status: "success", ...primitiveSummary(result.success, keys) };
  }
  if (result.error && typeof result.error === "object") {
    return { status: "error", ...primitiveSummary(result.error, ["message", "code"]) };
  }
  return primitiveSummary(result, ["status", "message", "path", "agentId"]);
}

function assistantText(event) {
  const content = event?.message?.content;
  if (!Array.isArray(content)) return undefined;
  const parts = content
    .filter((block) => block && typeof block === "object" && block.type === "text" && typeof block.text === "string")
    .map((block) => block.text);
  return parts.length ? parts.join("") : undefined;
}

function appendRecent(status, key, entry, limit) {
  if (!Array.isArray(status[key])) status[key] = [];
  status[key].push(entry);
  status[key] = status[key].slice(-limit);
}

function updateStatusFromEvent(status, event) {
  const eventType = event?.type;
  status.updated_at_utc = utcNow();
  status.events_seen = Number(status.events_seen || 0) + 1;
  status.last_event_type = redactText(eventType, 80);

  if (event?.agent_id) status.agent_id = redactText(event.agent_id, 120);
  if (event?.run_id) status.run_id = redactText(event.run_id, 120);

  if (eventType === "system") {
    status.state = "running";
    if (event.model) status.resolved_model = redactText(JSON.stringify(event.model), 240);
    if (Array.isArray(event.tools)) status.tools_count = event.tools.length;
    return;
  }

  if (eventType === "assistant") {
    const text = assistantText(event);
    if (text) status.last_assistant_text = redactText(text);
    return;
  }

  if (eventType === "thinking") {
    if (event.text) status.last_thinking_text = redactText(event.text);
    if (event.thinking_duration_ms) status.last_thinking_duration_ms = event.thinking_duration_ms;
    return;
  }

  if (eventType === "tool_call") {
    const entry = {
      at_utc: status.updated_at_utc,
      call_id: redactText(event.call_id, 120),
      tool: redactText(event.name, 120),
      status: redactText(event.status, 80),
      args: safeToolArgs(event),
    };
    if (event.status === "running") {
      status.current_tool_call = entry;
      if (event.name === "task" || event.name === "taskToolCall" || event.name === "Agent") {
        status.active_subagents[String(event.call_id)] = entry;
      }
    } else {
      entry.result = safeToolResult(event);
      if (status.current_tool_call?.call_id === entry.call_id) status.current_tool_call = null;
      if (event.name === "task" || event.name === "taskToolCall" || event.name === "Agent") {
        delete status.active_subagents[String(event.call_id)];
        appendRecent(status, "recent_subagents", entry, RECENT_SUBAGENT_LIMIT);
      }
    }
    appendRecent(status, "recent_tool_calls", entry, RECENT_TOOL_LIMIT);
    return;
  }

  if (eventType === "status") {
    status.cursor_status = redactText(event.status, 80);
    if (event.message) status.cursor_status_message = redactText(event.message);
    if (["FINISHED"].includes(event.status)) status.state = "succeeded";
    if (["ERROR", "CANCELLED", "EXPIRED"].includes(event.status)) status.state = event.status === "CANCELLED" ? "cancelled" : "failed";
    return;
  }

  if (eventType === "task") {
    if (event.status) status.last_task_status = redactText(event.status, 80);
    if (event.text) status.last_task_text = redactText(event.text);
    return;
  }

  if (eventType === "request") {
    status.state = "needs_input";
    status.request_id = redactText(event.request_id, 160);
    return;
  }

  if (eventType === "usage") {
    status.last_usage = event.usage;
  }
}

function buildPrompt({ taskFile, taskText, args, detectedSource, activeWorkspace, originalWorkspace, modelInfo, sdkMode }) {
  const mode = args.apply ? "apply" : (args.inspectOnly ? "inspect-only" : "proposal");
  const lines = [
    `You are Cursor's coding agent running through the official @cursor/sdk as the downstream implementation executor for an upstream delegation/review agent.`,
    describeAuthority(detectedSource),
    `Delegation mode: ${mode}.`,
    `SDK conversation mode: ${sdkMode}.`,
    `Cursor SDK model selection: ${modelInfo.label}.`,
    `Active workspace: ${activeWorkspace || "cloud workspace"}`,
    `Original workspace: ${originalWorkspace || "not local"}`,
    "Do not switch or infer a different Cursor model; only an explicit user instruction to Cursor may authorize a model override.",
    `If the task packet allows Cursor internal subagents / task tool calls, request model \`${modelInfo.label}\` for every internal subagent unless the packet quotes an explicit user Cursor-model override.`,
    "Do not launch Cursor internal subagents unless the task packet includes a Cursor Internal Subagent Policy that permits them.",
    "Do not create a competing architecture plan. Do not broaden scope.",
    "Do not commit, push, deploy, rotate credentials, alter billing, run destructive commands, or modify unrelated files.",
    "Leave changes unstaged for upstream review when apply mode is used.",
    "If the task requires a new dependency, breaking API change, migration, credential access, external service change, destructive command, billing change, deployment action, or scope expansion not listed in the packet, stop and report instead of improvising.",
  ];
  if (activeWorkspace && originalWorkspace && activeWorkspace !== originalWorkspace) {
    lines.push("This run uses a read-only workspace copy. Do not claim edits were applied to the original workspace. Report proposed edits and blockers only.");
  }
  if (args.inspectOnly) {
    lines.push("Inspect feasibility and blockers only. Do not edit files. Report repository-reality conflicts, missing context, and exact questions for the upstream reviewer.");
  } else if (args.apply) {
    lines.push("Implement the task with the smallest coherent diff that satisfies the authority section and acceptance criteria.");
  } else {
    lines.push("Analyze implementation feasibility and report proposed edits. Do not rely on direct file modification; this run may use a read-only workspace copy.");
  }
  if (args.delegationOwner) lines.push(`Upstream delegation owner: ${args.delegationOwner}.`);
  if (args.workstreamId) lines.push(`Workstream ID: ${args.workstreamId}.`);
  for (const instruction of normalizeArray(args.extraInstruction)) {
    lines.push(`Additional upstream instruction: ${instruction}`);
  }
  lines.push(
    "End with a completion report containing: Summary, Files Touched, Verification, Internal Subagents, Deviations, Risks/Follow-ups, and Notes for Upstream Reviewer.",
    "",
    `Task packet path for audit: ${taskFile}`,
    "",
    "--- BEGIN BOUNDED TASK PACKET ---",
    taskText.trim(),
    "--- END BOUNDED TASK PACKET ---",
  );
  return lines.join("\n");
}

async function makeLogDir(base) {
  await fsp.mkdir(base, { recursive: true, mode: 0o700 });
  try { await fsp.chmod(base, 0o700); } catch {}
  const stamp = new Date().toISOString().replace(/[-:.]/g, "").replace("T", "T").replace("Z", "Z");
  const runDir = path.join(base, `${stamp}-${crypto.randomBytes(4).toString("hex")}`);
  await fsp.mkdir(runDir, { mode: 0o700 });
  return runDir;
}

function authInstructions(envName) {
  return [
    "Cursor SDK authorization is required.",
    `Preferred: create a Cursor user API key from Cursor Dashboard → API Keys, then run: export ${envName}=\"<key>\"`,
    "For organization automation, use a Cursor service account API key from Team settings.",
    "Do not paste API keys into task packets, prompts, logs, issue comments, or chat transcripts. The wrapper can prompt in a local TTY with hidden input and will not save the key.",
  ].join("\n");
}

async function promptHidden(query) {
  if (!process.stdin.isTTY || !process.stdout.isTTY) throw new UserFacingError("Cannot request API key interactively because stdin/stdout is not a TTY.");
  process.stdout.write(query);
  const stdin = process.stdin;
  const wasRaw = stdin.isRaw;
  stdin.setEncoding("utf8");
  stdin.setRawMode(true);
  stdin.resume();
  let value = "";
  return await new Promise((resolve, reject) => {
    const cleanup = () => {
      stdin.off("data", onData);
      if (!wasRaw) stdin.setRawMode(false);
      stdin.pause();
      process.stdout.write("\n");
    };
    const onData = (char) => {
      if (char === "\u0003") {
        cleanup();
        reject(new UserFacingError("Authorization prompt cancelled."));
      } else if (char === "\r" || char === "\n") {
        cleanup();
        resolve(value.trim());
      } else if (char === "\u007f" || char === "\b") {
        value = value.slice(0, -1);
      } else {
        value += char;
      }
    };
    stdin.on("data", onData);
  });
}

async function resolveApiKey(args, reason = "missing") {
  const envName = args.apiKeyEnv || "CURSOR_API_KEY";
  const existing = process.env[envName];
  if (existing && existing.trim()) return existing.trim();

  if (args.authMode === "fail") {
    throw new UserFacingError(authInstructions(envName));
  }
  if ((args.authMode === "auto" || args.authMode === "prompt") && process.stdin.isTTY && process.stdout.isTTY) {
    const prefix = reason === "invalid"
      ? "Cursor rejected the API key. Enter a valid Cursor API key (hidden; not saved): "
      : "Enter Cursor API key for this SDK run (hidden; not saved): ";
    process.stderr.write(`${authInstructions(envName)}\n`);
    const key = await promptHidden(prefix);
    if (!key) throw new UserFacingError("No Cursor API key entered.");
    return key;
  }
  throw new UserFacingError(`${authInstructions(envName)}\nNon-interactive run: set ${envName} in the process environment, then retry.`);
}

function isAuthenticationError(err) {
  const name = err?.name || err?.constructor?.name;
  const code = String(err?.code || "").toLowerCase();
  const message = String(err?.message || "").toLowerCase();
  return name === "AuthenticationError" || err?.status === 401 || code.includes("auth") || message.includes("api key") || message.includes("unauthorized") || message.includes("invalid api key");
}

async function importCursorSdk() {
  try {
    return await import("@cursor/sdk");
  } catch (err) {
    if (err?.code === "ERR_MODULE_NOT_FOUND" || String(err?.message || "").includes("@cursor/sdk")) {
      throw new UserFacingError("Missing @cursor/sdk dependency. From this skill directory, run `npm install` before dispatching Cursor SDK agents.");
    }
    throw err;
  }
}

function createAgentOptions({ args, apiKey, activeWorkspace, modelInfo, sdkMode }) {
  const base = {
    apiKey,
    model: modelInfo.selection,
    mode: sdkMode,
    name: args.name || "delegate-to-cursor-sdk",
  };
  if (args.runtime === "cloud") {
    const repos = parseRepoSpecs(args.repoUrl);
    base.cloud = {
      repos: repos.length ? repos : undefined,
      autoCreatePR: Boolean(args.autoCreatePr),
      workOnCurrentBranch: Boolean(args.workOnCurrentBranch),
      skipReviewerRequest: Boolean(args.skipReviewerRequest),
    };
    Object.keys(base.cloud).forEach((key) => base.cloud[key] === undefined && delete base.cloud[key]);
    return base;
  }
  base.local = {
    cwd: activeWorkspace,
    sandboxOptions: { enabled: args.sandbox !== "disabled" },
    autoReview: Boolean(args.autoReview),
    settingSources: parseSettingSources(args.settingSource),
  };
  return base;
}

function createSendOptions(args) {
  const options = {};
  if (args.idempotencyKey) options.idempotencyKey = args.idempotencyKey;
  return options;
}

async function streamRun({ run, status, statusFile, rawEventsFile }) {
  if (run.supports && !run.supports("stream")) {
    status.stream_supported = false;
    status.stream_unsupported_reason = redactText(run.unsupportedReason?.("stream"), 240);
    await writeJson(statusFile, status);
    return;
  }
  status.stream_supported = true;
  for await (const event of run.stream()) {
    updateStatusFromEvent(status, event);
    if (rawEventsFile) await fsp.appendFile(rawEventsFile, `${safeJson(event)}\n`, "utf8");
    await writeJson(statusFile, status);
    if (event.type === "assistant") {
      const text = assistantText(event);
      if (text) process.stdout.write(text);
    } else if (event.type === "status" && event.message) {
      process.stderr.write(`[cursor:${event.status}] ${event.message}\n`);
    }
  }
}

async function dispatchOnce({ sdk, args, apiKey, activeWorkspace, modelInfo, prompt, status, statusFile, rawEventsFile, metadata, metadataFile }) {
  const { Agent } = sdk;
  const sdkMode = args.sdkMode || (args.apply ? "agent" : "plan");
  let agent;
  try {
    const agentOptions = createAgentOptions({ args, apiKey, activeWorkspace, modelInfo, sdkMode });
    metadata.agent_options_summary = {
      runtime: args.runtime,
      mode: sdkMode,
      model: modelInfo.label,
      local: agentOptions.local ? {
        cwd: agentOptions.local.cwd,
        sandbox_enabled: agentOptions.local.sandboxOptions.enabled,
        auto_review: agentOptions.local.autoReview,
        setting_sources: agentOptions.local.settingSources,
      } : undefined,
      cloud: agentOptions.cloud ? {
        repos_count: agentOptions.cloud.repos?.length || 0,
        auto_create_pr: Boolean(agentOptions.cloud.autoCreatePR),
        work_on_current_branch: Boolean(agentOptions.cloud.workOnCurrentBranch),
      } : undefined,
    };
    await writeJson(metadataFile, metadata);

    agent = args.resumeAgentId
      ? await Agent.resume(args.resumeAgentId, { apiKey })
      : await Agent.create(agentOptions);
    status.agent_id = redactText(agent.agentId, 120);
    status.state = "running";
    await writeJson(statusFile, status);

    const run = await agent.send(prompt, createSendOptions(args));
    status.run_id = redactText(run.id, 120);
    if (run.requestId) status.request_id = redactText(run.requestId, 160);
    await writeJson(statusFile, status);

    await streamRun({ run, status, statusFile, rawEventsFile });
    const result = await run.wait();
    status.state = result.status === "finished" ? "succeeded" : result.status;
    status.result = {
      status: result.status,
      request_id: redactText(result.requestId, 160),
      duration_ms: result.durationMs,
      text: redactText(result.result),
      error: result.error ? { message: redactText(result.error.message), code: redactText(result.error.code, 120) } : undefined,
      usage: result.usage,
      git: result.git ? { branches_count: result.git.branches?.length || 0 } : undefined,
    };
    metadata.finished_at_utc = utcNow();
    metadata.result_status = result.status;
    metadata.request_id = redactText(result.requestId, 160);
    metadata.duration_ms = result.durationMs;
    metadata.usage = result.usage;
    await writeJson(statusFile, status);
    await writeJson(metadataFile, metadata);
    if (status.stream_supported === false && result.result) process.stdout.write(`\n${result.result}\n`);
    return result.status === "finished" ? 0 : 1;
  } finally {
    if (agent) {
      if (typeof agent[Symbol.asyncDispose] === "function") await agent[Symbol.asyncDispose]();
      else if (typeof agent.close === "function") agent.close();
    }
  }
}

function parseCli() {
  const { values } = parseArgs({
    allowPositionals: false,
    options: {
      workspace: { type: "string", default: "." },
      "task-file": { type: "string" },
      runtime: { type: "string", default: "local" },
      "repo-url": { type: "string", multiple: true },
      "auto-create-pr": { type: "boolean", default: false },
      "work-on-current-branch": { type: "boolean", default: false },
      "skip-reviewer-request": { type: "boolean", default: false },
      "planning-source": { type: "string", default: "auto" },
      model: { type: "string", default: DEFAULT_MODEL_ALIAS },
      "model-param": { type: "string", multiple: true },
      "user-authorized-model": { type: "boolean", default: false },
      apply: { type: "boolean", default: false },
      "inspect-only": { type: "boolean", default: false },
      "sdk-mode": { type: "string" },
      sandbox: { type: "string", default: "enabled" },
      "auto-review": { type: "boolean", default: false },
      "setting-source": { type: "string", multiple: true },
      "allow-missing-authority": { type: "boolean", default: false },
      "allow-placeholders": { type: "boolean", default: false },
      "allow-dirty": { type: "boolean", default: false },
      "allow-non-git": { type: "boolean", default: false },
      "override-reason": { type: "string" },
      "workspace-copy": { type: "string", default: "auto" },
      "delegation-owner": { type: "string" },
      "workstream-id": { type: "string" },
      name: { type: "string" },
      "log-dir": { type: "string" },
      "extra-instruction": { type: "string", multiple: true },
      "include-raw-events": { type: "boolean", default: false },
      "keep-workspace-copy": { type: "boolean", default: false },
      "api-key-env": { type: "string", default: "CURSOR_API_KEY" },
      "auth-mode": { type: "string", default: "auto" },
      "auth-retries": { type: "string", default: "1" },
      "resume-agent-id": { type: "string" },
      "idempotency-key": { type: "string" },
      "dry-run": { type: "boolean", default: false },
      help: { type: "boolean", short: "h", default: false },
    },
  });
  if (values.help) {
    console.log(`Usage: node scripts/cursor_delegate.mjs --workspace <repo> --task-file <packet.md> [--apply|--inspect-only]\n\nAuthorization: set CURSOR_API_KEY, or run in a TTY and let --auth-mode auto request a hidden key.\nInstall dependency first: npm install`);
    process.exit(0);
  }
  const camel = {};
  for (const [key, value] of Object.entries(values)) {
    camel[key.replace(/-([a-z])/g, (_m, char) => char.toUpperCase())] = value;
  }
  if (!camel.taskFile) throw new UserFacingError("--task-file is required");
  if (!new Set(["local", "cloud"]).has(camel.runtime)) throw new UserFacingError("--runtime must be local or cloud");
  if (!PLANNING_SOURCE_CHOICES.has(camel.planningSource)) throw new UserFacingError(`--planning-source must be one of: ${[...PLANNING_SOURCE_CHOICES].join(", ")}`);
  if (camel.apply && camel.inspectOnly) throw new UserFacingError("--apply and --inspect-only are mutually exclusive");
  if (!new Set(["enabled", "disabled"]).has(camel.sandbox)) throw new UserFacingError("--sandbox must be enabled or disabled");
  if (!new Set(["auto", "always", "never"]).has(camel.workspaceCopy)) throw new UserFacingError("--workspace-copy must be auto, always, or never");
  if (!new Set(["auto", "prompt", "fail"]).has(camel.authMode)) throw new UserFacingError("--auth-mode must be auto, prompt, or fail");
  if (camel.sdkMode && !new Set(["plan", "agent"]).has(camel.sdkMode)) throw new UserFacingError("--sdk-mode must be plan or agent");
  camel.authRetries = Number.parseInt(camel.authRetries, 10);
  if (!Number.isFinite(camel.authRetries) || camel.authRetries < 0) throw new UserFacingError("--auth-retries must be a non-negative integer");
  return camel;
}

async function main() {
  const args = parseCli();
  const workspace = path.resolve(args.workspace);
  const taskFile = path.resolve(args.taskFile);
  const taskText = await fsp.readFile(taskFile, "utf8").catch(() => { throw new UserFacingError(`Task file does not exist: ${taskFile}`); });
  const modelInfo = modelSelectionFromArgs(args);

  if (!modelInfo.isDefault && !args.userAuthorizedModel) {
    throw new UserFacingError(`Refusing Cursor model override ${args.model}. Default to ${DEFAULT_MODEL_ALIAS} (SDK: composer-2.5 fast=true) unless the user explicitly directed Cursor to use a different model.`);
  }
  if (args.apply && args.workspaceCopy === "always") throw new UserFacingError("--workspace-copy always is not compatible with --apply");
  if (args.runtime === "cloud" && args.workspaceCopy !== "auto") throw new UserFacingError("--workspace-copy applies only to local runtime");

  if (args.runtime === "local") ensureDirWorkspace(workspace);
  const authority = validateAuthority(taskText, args.planningSource, args.allowPlaceholders);
  let detectedSource = authority.detected;
  if (!authority.ok) {
    const missingOnly = authority.message.includes("found ['none']");
    if (!(args.allowMissingAuthority && missingOnly)) throw new UserFacingError(`Refusing dispatch: ${authority.message}`);
    detectedSource = args.planningSource !== "auto" ? args.planningSource : "master-direct";
  }

  const unsafeOverrides = collectUnsafeOverrides(args, modelInfo);
  if (unsafeOverrides.length && !args.overrideReason) {
    throw new UserFacingError(`Unsafe override flags require --override-reason: ${unsafeOverrides.join(", ")}`);
  }

  if (args.runtime === "local" && args.apply) {
    const git = runGitStatus(workspace);
    if (!git.isGit && !args.allowNonGit) {
      throw new UserFacingError(`Apply mode requires a git workspace for review/revert safety.${git.error ? `\ngit status error: ${git.error}` : ""}`);
    }
    if (git.isGit && !args.allowDirty) {
      const dirty = filterIgnorableStatus(git.lines, workspace, taskFile);
      if (dirty.length) throw new UserFacingError(`Refusing apply mode because the workspace has existing git changes.\n${dirty.join("\n")}`);
    }
  }

  const useCopy = args.runtime === "local" && (args.workspaceCopy === "always" || (args.workspaceCopy === "auto" && !args.apply));
  const activeWorkspace = useCopy && !args.dryRun ? makeReadonlyCopy(workspace) : workspace;
  const workspaceCopyRoot = useCopy && !args.dryRun ? path.dirname(activeWorkspace) : undefined;
  let workspaceCopyCleaned = false;
  function cleanupWorkspaceCopySync() {
    if (workspaceCopyRoot && !args.keepWorkspaceCopy && !workspaceCopyCleaned) {
      try { fs.rmSync(workspaceCopyRoot, { recursive: true, force: true }); } catch {}
      workspaceCopyCleaned = true;
    }
  }
  if (workspaceCopyRoot) {
    process.once("exit", cleanupWorkspaceCopySync);
    process.once("SIGINT", () => { cleanupWorkspaceCopySync(); process.exit(130); });
    process.once("SIGTERM", () => { cleanupWorkspaceCopySync(); process.exit(143); });
  }
  const sdkMode = args.sdkMode || (args.apply ? "agent" : "plan");
  const prompt = buildPrompt({ taskFile, taskText, args, detectedSource, activeWorkspace: args.runtime === "local" ? activeWorkspace : undefined, originalWorkspace: args.runtime === "local" ? workspace : undefined, modelInfo, sdkMode });
  const logBase = path.resolve(args.logDir || path.join(workspace, ".agent", "delegations"));

  if (args.dryRun) {
    console.log("Cursor SDK dispatch dry run");
    console.log(JSON.stringify({
      runtime: args.runtime,
      mode: args.apply ? "apply" : (args.inspectOnly ? "inspect-only" : "proposal"),
      sdkMode,
      model: modelInfo.selection,
      modelLabel: modelInfo.label,
      detectedAuthoritySource: detectedSource,
      authorityValidation: authority.message,
      workspaceCopy: useCopy,
      keepWorkspaceCopy: Boolean(args.keepWorkspaceCopy),
      sandbox: args.sandbox,
      settingSources: args.runtime === "local" ? parseSettingSources(args.settingSource) : undefined,
      logBase,
      auth: `env:${args.apiKeyEnv || "CURSOR_API_KEY"}; prompt:${args.authMode}`,
    }, null, 2));
    console.log("\nPrompt:\n");
    console.log(prompt);
    return 0;
  }

  const sdk = await importCursorSdk();
  const runDir = await makeLogDir(logBase);
  const statusFile = path.join(runDir, "status.json");
  const metadataFile = path.join(runDir, "metadata.json");
  const promptFile = path.join(runDir, "prompt.txt");
  const rawEventsFile = args.includeRawEvents ? path.join(runDir, "events.ndjson") : undefined;
  await fsp.writeFile(path.join(logBase, "latest"), `${runDir}\n`, "utf8");
  await fsp.writeFile(promptFile, prompt, "utf8");

  const startedAt = utcNow();
  const metadata = {
    implementation: "@cursor/sdk",
    workspace,
    active_workspace: args.runtime === "local" ? activeWorkspace : undefined,
    workspace_copy_used: args.runtime === "local" && activeWorkspace !== workspace,
    workspace_copy_cleanup: args.keepWorkspaceCopy ? "kept_by_override" : (args.runtime === "local" && activeWorkspace !== workspace ? "remove_on_exit" : "not_applicable"),
    task_file: taskFile,
    detected_authority_source: detectedSource,
    authority_validation: authority.message,
    runtime: args.runtime,
    mode: args.apply ? "apply" : (args.inspectOnly ? "inspect-only" : "proposal"),
    sdk_mode: sdkMode,
    model: modelInfo.label,
    user_authorized_model_override: Boolean(args.userAuthorizedModel),
    raw_events_enabled: Boolean(rawEventsFile),
    unsafe_overrides: unsafeOverrides.map((flag) => ({ flag, reason: args.overrideReason })),
    prompt_file: promptFile,
    status_file: statusFile,
    events_log: rawEventsFile,
    started_at_utc: startedAt,
  };
  const status = {
    state: "starting",
    implementation: "@cursor/sdk",
    workspace,
    active_workspace: args.runtime === "local" ? activeWorkspace : undefined,
    workspace_copy_used: args.runtime === "local" && activeWorkspace !== workspace,
    workspace_copy_cleanup: args.keepWorkspaceCopy ? "kept_by_override" : (args.runtime === "local" && activeWorkspace !== workspace ? "remove_on_exit" : "not_applicable"),
    task_file: taskFile,
    run_dir: runDir,
    metadata_file: metadataFile,
    prompt_file: promptFile,
    events_log: rawEventsFile,
    runtime: args.runtime,
    mode: metadata.mode,
    sdk_mode: sdkMode,
    model: modelInfo.label,
    sandbox_enabled: args.runtime === "local" ? args.sandbox !== "disabled" : undefined,
    started_at_utc: startedAt,
    updated_at_utc: startedAt,
    events_seen: 0,
    current_tool_call: null,
    recent_tool_calls: [],
    active_subagents: {},
    recent_subagents: [],
  };
  await writeJson(metadataFile, metadata);
  await writeJson(statusFile, status);

  console.error(`Running Cursor SDK agent. Logs: ${runDir}`);
  console.error(`Live status: ${statusFile}`);

  let apiKey;
  try {
    apiKey = await resolveApiKey(args, "missing");
  } catch (err) {
    status.state = "needs_authorization";
    status.authorization = { required: true, reason: redactText(err.message) };
    await writeJson(statusFile, status);
    throw err;
  }

  let attempts = 0;
  while (true) {
    try {
      return await dispatchOnce({ sdk, args, apiKey, activeWorkspace, modelInfo, prompt, status, statusFile, rawEventsFile, metadata, metadataFile });
    } catch (err) {
      if (isAuthenticationError(err) && attempts < args.authRetries && (args.authMode === "auto" || args.authMode === "prompt")) {
        attempts += 1;
        status.state = "needs_authorization";
        status.authorization = { required: true, reason: "missing_or_invalid_cursor_api_key", attempts };
        await writeJson(statusFile, status);
        apiKey = await resolveApiKey({ ...args, authMode: "prompt" }, "invalid");
        continue;
      }
      status.state = isAuthenticationError(err) ? "needs_authorization" : "failed";
      status.error = {
        name: redactText(err?.name || err?.constructor?.name, 120),
        message: redactText(err?.message),
        code: redactText(err?.code, 120),
        status: err?.status,
        request_id: redactText(err?.requestId, 160),
        help_url: err?.helpUrl ? redactUrl(err.helpUrl) : undefined,
      };
      metadata.finished_at_utc = utcNow();
      metadata.error = status.error;
      await writeJson(statusFile, status);
      await writeJson(metadataFile, metadata);
      throw err;
    }
  }
}

main().then((code) => {
  process.exitCode = code;
}).catch((err) => {
  const code = err?.exitCode || (isAuthenticationError(err) ? 2 : 1);
  const helpUrl = err?.helpUrl ? `\nHelp URL: ${redactUrl(err.helpUrl)}` : "";
  console.error(`${err?.message || err}${helpUrl}`);
  process.exitCode = code;
});
