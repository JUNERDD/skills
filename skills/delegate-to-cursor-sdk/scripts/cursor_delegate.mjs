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
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";

const DEFAULT_MODEL_PROFILE_NAME = "grok-4.5-high";
const DEFAULT_MODEL_PROFILE = Object.freeze({ target: "grok-4.5", effort: "high" });
const DEFAULT_MODEL_LABEL = "Grok 4.5 High";
const DEFAULT_MODEL_PARAMS_MARKER = "catalog-resolved-high-default-speed";
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
const SENSITIVE_ASSIGNMENT_RE = /(token|secret|api[_-]?key|authorization|cookie|password|credential|private[_-]?key)(\s*[:=]\s*)(?:"[^"\r\n]*"|'[^'\r\n]*'|[^\r\n,;}]+)/gi;

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

function maskNonNewlineCharacters(value) {
  return value.replace(/[^\r\n]/g, " ");
}

function isEscapedCharacter(value, index) {
  let slashes = 0;
  for (let cursor = index - 1; cursor >= 0 && value[cursor] === "\\"; cursor -= 1) slashes += 1;
  return slashes % 2 === 1;
}

function nextUnescapedBacktick(value, fromIndex) {
  let index = value.indexOf("`", fromIndex);
  while (index !== -1 && isEscapedCharacter(value, index)) index = value.indexOf("`", index + 1);
  return index;
}

function backtickRunLength(value, start) {
  let end = start;
  while (value[end] === "`") end += 1;
  return end - start;
}

function matchingBacktickRun(value, start, length) {
  let candidate = value.indexOf("`", start + length);
  while (candidate !== -1) {
    const candidateLength = backtickRunLength(value, candidate);
    if (candidateLength === length) return candidate;
    candidate = value.indexOf("`", candidate + candidateLength);
  }
  return -1;
}

function maskMarkdownNonContent(taskText) {
  const parts = String(taskText).split(/(\r\n|\n|\r)/);
  let fence;
  let inHtmlComment = false;
  for (let index = 0; index < parts.length; index += 2) {
    const line = parts[index];
    if (fence) {
      const closing = new RegExp(`^[ \\t]{0,3}\\${fence.character}{${fence.length},}[ \\t]*$`);
      if (closing.test(line)) fence = undefined;
      parts[index] = maskNonNewlineCharacters(line);
      continue;
    }
    if (!inHtmlComment) {
      const opening = /^[ \t]{0,3}(`{3,}|~{3,})/.exec(line);
      const info = opening ? line.slice(opening[0].length) : "";
      const validOpening = opening && (opening[1][0] !== "`" || !info.includes("`"));
      if (validOpening) {
        fence = { character: opening[1][0], length: opening[1].length };
        parts[index] = maskNonNewlineCharacters(line);
        continue;
      }
    }

    const outputCharacters = line.split("");
    const structuralCharacters = line.split("");
    let cursor = 0;
    while (cursor < line.length) {
      if (inHtmlComment) {
        const end = line.indexOf("-->", cursor);
        const maskedEnd = end === -1 ? line.length : end + 3;
        for (let position = cursor; position < maskedEnd; position += 1) {
          outputCharacters[position] = " ";
          structuralCharacters[position] = " ";
        }
        if (end === -1) break;
        inHtmlComment = false;
        cursor = maskedEnd;
        continue;
      }
      const commentStart = line.indexOf("<!--", cursor);
      const codeStart = nextUnescapedBacktick(line, cursor);
      if (codeStart !== -1 && (commentStart === -1 || codeStart < commentStart)) {
        const runLength = backtickRunLength(line, codeStart);
        const codeEnd = matchingBacktickRun(line, codeStart, runLength);
        if (codeEnd === -1) {
          throw new UserFacingError("Task packet uses an unclosed or multiline inline-code span; use a fenced code block so authority and model sections remain unambiguous.");
        }
        for (let position = codeStart; position < codeEnd + runLength; position += 1) structuralCharacters[position] = " ";
        cursor = codeEnd + runLength;
        continue;
      }
      if (commentStart === -1) break;
      const commentEnd = line.indexOf("-->", commentStart + 4);
      const maskedEnd = commentEnd === -1 ? line.length : commentEnd + 3;
      for (let position = commentStart; position < maskedEnd; position += 1) {
        outputCharacters[position] = " ";
        structuralCharacters[position] = " ";
      }
      inHtmlComment = commentEnd === -1;
      if (commentEnd === -1) break;
      cursor = maskedEnd;
    }
    const structuralLine = structuralCharacters.join("");
    if (/^[ \t]{0,3}<(?:\/?[A-Za-z][A-Za-z0-9-]*(?:[ \t]|\/?>|$)|\?|![A-Z]|!\[CDATA\[)/.test(structuralLine)) {
      throw new UserFacingError("Task packet uses a raw HTML block; fence HTML examples so authority and model sections remain unambiguous.");
    }
    parts[index] = outputCharacters.join("");
  }
  return parts.join("");
}

function markdownHeadings(taskText) {
  const validationText = maskMarkdownNonContent(taskText);
  const headings = [];
  HEADING_RE.lastIndex = 0;
  let match;
  while ((match = HEADING_RE.exec(validationText)) !== null) {
    const heading = match[1].trim().replace(/#+$/, "").trim();
    if (heading) headings.push(heading);
  }
  return headings;
}

function sectionBody(taskText, heading) {
  const validationText = maskMarkdownNonContent(taskText);
  HEADING_RE.lastIndex = 0;
  const matches = [...validationText.matchAll(HEADING_RE)];
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
  const id = input.slice(0, index).trim();
  const value = input.slice(index + 1).trim();
  if (!id || !value) throw new UserFacingError(`${optionName} must use non-empty key=value syntax: ${input}`);
  return { id, value };
}

function modelSelectionFromArgs(args) {
  const modelInput = args.model || DEFAULT_MODEL_PROFILE_NAME;
  const params = normalizeArray(args.modelParam).map((item) => parseKeyValue(String(item), "--model-param"));
  const seen = new Set();
  for (const param of params) {
    if (seen.has(param.id)) throw new UserFacingError(`Duplicate --model-param id: ${param.id}`);
    seen.add(param.id);
  }

  if (modelInput === DEFAULT_MODEL_PROFILE_NAME) {
    if (params.length) {
      throw new UserFacingError(`--model-param cannot modify the logical default profile ${DEFAULT_MODEL_PROFILE_NAME}. Specify an explicit --model together with --user-authorized-model and --override-reason.`);
    }
    return {
      input: modelInput,
      profile: DEFAULT_MODEL_PROFILE,
      selection: undefined,
      label: DEFAULT_MODEL_LABEL,
      isDefault: true,
      catalogVerified: false,
    };
  }

  const selection = params.length ? { id: modelInput, params } : { id: modelInput };
  const label = params.length ? `${modelInput} ${params.map((param) => `${param.id}=${param.value}`).join(" ")}` : modelInput;
  return { input: modelInput, profile: undefined, selection, label, isDefault: false, catalogVerified: false };
}

function normalizeCatalogText(value) {
  return String(value || "").trim().toLowerCase().replace(/[_./-]+/g, " ").replace(/\s+/g, " ");
}

function uniqueCatalogModel(matches, target, tier) {
  if (matches.length > 1) {
    throw new UserFacingError(`Cursor model catalog is ambiguous for ${target}: ${matches.length} models match by ${tier}.`);
  }
  return matches[0];
}

function catalogModelFor(catalog, target, allowNormalized) {
  const exactIds = catalog.filter((model) => model?.id === target);
  if (exactIds.length) return uniqueCatalogModel(exactIds, target, "exact id");
  const exactAliases = catalog.filter((model) => normalizeArray(model?.aliases).some((alias) => alias === target));
  if (exactAliases.length) return uniqueCatalogModel(exactAliases, target, "exact alias");
  if (!allowNormalized) return undefined;

  const normalizedTarget = normalizeCatalogText(target);
  const normalizedIds = catalog.filter((model) => normalizeCatalogText(model?.id) === normalizedTarget);
  if (normalizedIds.length) return uniqueCatalogModel(normalizedIds, target, "normalized id");
  const normalizedAliases = catalog.filter((model) => normalizeArray(model?.aliases)
    .some((alias) => normalizeCatalogText(alias) === normalizedTarget));
  return normalizedAliases.length ? uniqueCatalogModel(normalizedAliases, target, "normalized alias") : undefined;
}

function uniqueParameterDefinition(matches, model, purpose, tier) {
  if (matches.length > 1) {
    throw new UserFacingError(`Cursor model ${model.id} has ambiguous ${purpose} parameters at ${tier}: ${matches.map((definition) => definition.id).join(", ")}.`);
  }
  return matches[0];
}

function hasHighValue(definition) {
  return normalizeArray(definition?.values).some((entry) => normalizeCatalogText(entry?.value) === "high" || normalizeCatalogText(entry?.displayName) === "high");
}

function isEffortParameterName(value) {
  const text = normalizeCatalogText(value);
  if (!text || /(cache|cached|prefix|storage)/.test(text)) return false;
  const exact = new Set([
    "reasoning", "reasoning effort", "reasoning level", "reasoning mode",
    "effort", "thinking", "thinking level", "thinking effort", "thinking mode",
  ]);
  return exact.has(text) || /(^| )(reasoning|effort|thinking)( |$)/.test(text);
}

function isSpeedParameterName(value) {
  const text = normalizeCatalogText(value);
  if (!text || /(cache|cached|prefix|storage|reasoning|thinking|effort)/.test(text)) return false;
  const exact = new Set([
    "fast", "fast mode", "is fast", "use fast", "fast enabled",
    "speed", "speed mode", "speed tier",
    "latency", "latency mode", "latency tier",
  ]);
  const compact = new Set(["fastmode", "isfast", "usefast", "fastenabled", "speedmode", "speedtier", "latencymode", "latencytier"]);
  return exact.has(text) || compact.has(text.replace(/ /g, "")) || /(^| )(fast|speed|latency)( |$)/.test(text);
}

function parameterDefinitionForHigh(model) {
  const definitions = normalizeArray(model?.parameters);
  const semanticNames = new Set([
    "reasoning", "reasoning effort", "reasoning level", "reasoning mode",
    "effort", "thinking", "thinking level", "thinking effort", "thinking mode",
  ]);
  const exactIds = definitions.filter((definition) => semanticNames.has(normalizeCatalogText(definition?.id)) && hasHighValue(definition));
  if (exactIds.length) return uniqueParameterDefinition(exactIds, model, "High effort", "exact id");
  const exactDisplays = definitions.filter((definition) => semanticNames.has(normalizeCatalogText(definition?.displayName)) && hasHighValue(definition));
  if (exactDisplays.length) return uniqueParameterDefinition(exactDisplays, model, "High effort", "exact display name");
  const fuzzy = definitions.filter((definition) => isEffortParameterName(`${definition?.id || ""} ${definition?.displayName || ""}`) && hasHighValue(definition));
  return fuzzy.length ? uniqueParameterDefinition(fuzzy, model, "High effort", "unique semantic match") : undefined;
}

function highParameterValue(definition) {
  const values = normalizeArray(definition?.values);
  const tiers = [
    ["exact value", (entry) => normalizeCatalogText(entry?.value) === "high"],
    ["exact display name", (entry) => normalizeCatalogText(entry?.displayName) === "high"],
  ];
  for (const [tier, predicate] of tiers) {
    const matches = values.filter(predicate);
    if (matches.length > 1) {
      throw new UserFacingError(`Cursor parameter ${definition.id} has ambiguous High values at ${tier}.`);
    }
    if (matches.length === 1) return matches[0];
  }
  return undefined;
}

function isHighVariantLabel(variant) {
  const label = normalizeCatalogText(variant?.displayName);
  if (!label || label.includes("xhigh") || label.includes("extra high") || label.includes("max")) return false;
  return label === "high" || /(^| )high( |$)/.test(label);
}

function parameterMap(params) {
  const map = new Map();
  for (const param of normalizeArray(params)) map.set(String(param.id), String(param.value));
  return map;
}

function assertUniqueParameterIds(params, context) {
  const seen = new Set();
  for (const param of normalizeArray(params)) {
    if (!param || typeof param.id !== "string" || typeof param.value !== "string") {
      throw new UserFacingError(`${context} contains a malformed model parameter.`);
    }
    if (seen.has(param.id)) throw new UserFacingError(`${context} contains duplicate model parameter id ${param.id}.`);
    seen.add(param.id);
  }
}

function validateCatalogModelShape(model) {
  if (!model || typeof model.id !== "string" || !model.id) {
    throw new UserFacingError("Cursor model catalog contains a selected entry without a valid id.");
  }
  const definitionIds = new Set();
  for (const definition of normalizeArray(model?.parameters)) {
    if (!definition || typeof definition.id !== "string" || !definition.id) {
      throw new UserFacingError(`Cursor model ${model.id} contains a malformed parameter definition.`);
    }
    if (definitionIds.has(definition.id)) throw new UserFacingError(`Cursor model ${model.id} contains duplicate parameter definition id ${definition.id}.`);
    definitionIds.add(definition.id);
    const values = new Set();
    for (const entry of normalizeArray(definition.values)) {
      if (!entry || typeof entry.value !== "string" || !entry.value) {
        throw new UserFacingError(`Cursor model ${model.id} parameter ${definition.id} contains a malformed value.`);
      }
      if (values.has(entry.value)) throw new UserFacingError(`Cursor model ${model.id} parameter ${definition.id} contains duplicate value ${entry.value}.`);
      values.add(entry.value);
    }
  }
  for (const variant of normalizeArray(model?.variants)) {
    assertUniqueParameterIds(variant?.params, `Cursor catalog variant ${variant?.displayName || "<unnamed>"}`);
  }
}

function safeModelSelection(selection) {
  if (!selection || typeof selection !== "object" || typeof selection.id !== "string" || !selection.id) return undefined;
  if (selection.params !== undefined && !Array.isArray(selection.params)) return undefined;
  const params = selection.params || [];
  if (params.some((param) => !param
    || typeof param.id !== "string"
    || !param.id
    || typeof param.value !== "string"
    || !param.value)) return undefined;
  return params.length ? { id: selection.id, params } : { id: selection.id };
}

function catalogSpeedObservationPolicy(model) {
  const allowed = new Map();
  const definitions = new Map(normalizeArray(model?.parameters).map((definition) => [definition.id, definition]));
  const add = (id, value) => {
    if (typeof id !== "string" || typeof value !== "string") return;
    if (!allowed.has(id)) allowed.set(id, new Set());
    allowed.get(id).add(value);
  };

  for (const definition of definitions.values()) {
    if (!isSpeedParameterName(`${definition.id || ""} ${definition.displayName || ""}`)) continue;
    for (const entry of normalizeArray(definition.values)) add(definition.id, entry?.value);
  }
  for (const variant of normalizeArray(model?.variants)) {
    for (const param of normalizeArray(variant?.params)) {
      const definition = definitions.get(param?.id);
      if (!isSpeedParameterName(`${param?.id || ""} ${definition?.displayName || ""}`)) continue;
      add(param.id, param.value);
    }
  }

  return [...allowed]
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([id, values]) => ({ id, values: [...values].sort() }));
}

function additionalParameterPolicyMap(policy) {
  const map = new Map();
  for (const entry of normalizeArray(policy)) {
    if (!entry || typeof entry.id !== "string") continue;
    map.set(entry.id, new Set(normalizeArray(entry.values).map(String)));
  }
  return map;
}

function modelSelectionsMatch(left, right, allowedAdditionalParams) {
  if (!left || !right || left.id !== right.id) return false;
  const leftValues = normalizeArray(left.params);
  const rightValues = normalizeArray(right.params);
  const leftParams = parameterMap(leftValues);
  const rightParams = parameterMap(rightValues);
  if (leftParams.size !== leftValues.length || rightParams.size !== rightValues.length) return false;
  if (![...leftParams].every(([id, value]) => rightParams.get(id) === value)) return false;
  if (!Array.isArray(allowedAdditionalParams)) return leftParams.size === rightParams.size;

  const allowed = additionalParameterPolicyMap(allowedAdditionalParams);
  for (const [id, value] of rightParams) {
    if (leftParams.has(id)) continue;
    if (!allowed.get(id)?.has(value)) return false;
  }
  return true;
}

function modelSelectionsEqual(left, right) {
  return modelSelectionsMatch(left, right, false);
}

function verifyResolvedModel(requested, systemModel, resultModel, { allowedAdditionalParams } = {}) {
  const safeSystemModel = safeModelSelection(systemModel);
  const safeResultModel = safeModelSelection(resultModel);
  const systemWasReported = systemModel !== undefined && systemModel !== null;
  const resultWasReported = resultModel !== undefined && resultModel !== null;
  const systemMatchesRequested = safeSystemModel
    ? modelSelectionsMatch(requested, safeSystemModel, allowedAdditionalParams)
    : (systemWasReported ? false : undefined);
  const resultMatchesRequested = safeResultModel
    ? modelSelectionsMatch(requested, safeResultModel, allowedAdditionalParams)
    : (resultWasReported ? false : undefined);
  const verified = systemMatchesRequested === true && resultMatchesRequested === true;
  const mismatch = systemMatchesRequested === false || resultMatchesRequested === false;
  return {
    verified,
    mismatch,
    status: verified ? "matched" : (mismatch ? "mismatched" : "unavailable"),
    systemModel: safeSystemModel,
    resultModel: safeResultModel,
    systemMatchesRequested,
    resultMatchesRequested,
    scope: Array.isArray(allowedAdditionalParams) ? "requested_high_with_catalog_speed_defaults" : "exact",
  };
}

function validateSelectionAgainstCatalogModel(model, selection) {
  assertUniqueParameterIds(selection.params, `Cursor model selection ${selection.id}`);
  for (const param of normalizeArray(selection.params)) {
    const definition = normalizeArray(model?.parameters).find((candidate) => candidate?.id === param.id);
    const variantSupports = normalizeArray(model?.variants).some((variant) => normalizeArray(variant?.params)
      .some((candidate) => candidate?.id === param.id && String(candidate?.value) === String(param.value)));
    const definitionSupports = normalizeArray(definition?.values).some((candidate) => String(candidate?.value) === String(param.value));
    if (!definitionSupports && !variantSupports) {
      throw new UserFacingError(`Cursor model catalog does not support ${model.id} parameter ${param.id}=${param.value}.`);
    }
  }
}

function selectionFromHighVariant(model, variant) {
  const params = normalizeArray(variant.params).map((param) => ({ id: String(param.id), value: String(param.value) }));
  assertUniqueParameterIds(params, `Cursor catalog variant ${variant.displayName}`);
  const effortParams = params.filter((param) => isEffortParameterName(param.id));
  if (effortParams.length !== 1 || normalizeCatalogText(effortParams[0].value) !== "high") {
    throw new UserFacingError(`Cursor catalog variant ${variant.displayName} does not expose one unambiguous High effort parameter.`);
  }
  const selection = { id: model.id, params: [effortParams[0]] };
  validateSelectionAgainstCatalogModel(model, selection);
  return selection;
}

function variantExposesHighEffort(variant) {
  const effortParams = normalizeArray(variant?.params).filter((param) => isEffortParameterName(param?.id));
  return effortParams.length === 1 && normalizeCatalogText(effortParams[0]?.value) === "high";
}

function selectionKey(selection) {
  const params = normalizeArray(selection.params)
    .map((param) => [String(param.id), String(param.value)])
    .sort(([left], [right]) => left.localeCompare(right));
  return JSON.stringify([selection.id, params]);
}

function chooseVariantSelection(model, records) {
  const unique = new Map();
  for (const record of records) {
    const key = selectionKey(record.selection);
    if (!unique.has(key)) unique.set(key, record);
  }
  if (unique.size === 1) return unique.values().next().value.selection;
  const defaults = records.filter((record) => record.variant?.isDefault);
  const uniqueDefaults = new Map(defaults.map((record) => [selectionKey(record.selection), record]));
  if (uniqueDefaults.size === 1) return uniqueDefaults.values().next().value.selection;
  throw new UserFacingError(`Cursor model ${model.id} has multiple distinct valid High selections; refusing to choose arbitrarily.`);
}

function resolveDefaultProfile(model) {
  validateCatalogModelShape(model);
  const effortDefinition = parameterDefinitionForHigh(model);
  const highValue = effortDefinition ? highParameterValue(effortDefinition) : undefined;
  if (effortDefinition && highValue) {
    const selection = { id: model.id, params: [{ id: effortDefinition.id, value: String(highValue.value) }] };
    validateSelectionAgainstCatalogModel(model, selection);
    return selection;
  }

  const variants = normalizeArray(model?.variants);
  const variantRecords = [];
  for (const variant of variants.filter((variant) => isHighVariantLabel(variant) || variantExposesHighEffort(variant))) {
    try {
      variantRecords.push({
        variant,
        selection: selectionFromHighVariant(model, variant),
      });
    } catch (err) {
      if (!(err instanceof UserFacingError)) throw err;
    }
  }
  if (variantRecords.length) return chooseVariantSelection(model, variantRecords);

  const available = variants.map((variant) => variant?.displayName).filter(Boolean).join(", ") || "none";
  throw new UserFacingError(`Cursor model ${model.id} has no unambiguous High parameter selection. Available variants: ${available}`);
}

function resolveModelInfoFromCatalog(catalog, modelInfo) {
  if (!Array.isArray(catalog) || catalog.length === 0) throw new UserFacingError("Cursor.models.list() returned no available models.");
  const target = modelInfo.profile?.target || modelInfo.selection?.id;
  const model = catalogModelFor(catalog, target, modelInfo.isDefault);
  if (!model) throw new UserFacingError(`Cursor model catalog does not contain requested model ${target}.`);
  validateCatalogModelShape(model);
  const selection = modelInfo.isDefault
    ? resolveDefaultProfile(model)
    : { ...modelInfo.selection, id: model.id };
  if (!modelInfo.isDefault) validateSelectionAgainstCatalogModel(model, selection);
  return {
    ...modelInfo,
    selection,
    allowedObservedSpeedParams: modelInfo.isDefault ? catalogSpeedObservationPolicy(model) : undefined,
    label: modelInfo.isDefault ? DEFAULT_MODEL_LABEL : (selection.params?.length ? `${selection.id} ${selection.params.map((param) => `${param.id}=${param.value}`).join(" ")}` : selection.id),
    catalogVerified: true,
    catalogModelId: model.id,
  };
}

async function resolveModelInfoWithSdk(sdk, apiKey, modelInfo) {
  if (!sdk?.Cursor?.models?.list) throw new UserFacingError("Installed @cursor/sdk does not expose Cursor.models.list(); upgrade the SDK before dispatch.");
  const catalog = await sdk.Cursor.models.list({ apiKey });
  return resolveModelInfoFromCatalog(catalog, modelInfo);
}

function taskPacketFieldValues(section, label) {
  const validationSection = maskMarkdownNonContent(section);
  const escaped = label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const regex = new RegExp(`^[ \\t]{0,3}-[ \\t]+${escaped}:[ \\t]*(.+?)[ \\t]*$`, "gmi");
  return [...validationSection.matchAll(regex)].map((match) => {
    const value = match[1].trim();
    return value.startsWith("`") && value.endsWith("`") ? value.slice(1, -1).trim() : value;
  });
}

function parsePacketModelParams(value) {
  if (value === "none") return [];
  const params = value.split(",").map((part) => parseKeyValue(part.trim(), "Model params"));
  const ids = new Set();
  for (const param of params) {
    if (ids.has(param.id)) throw new UserFacingError(`Duplicate Model params id: ${param.id}`);
    ids.add(param.id);
  }
  return params;
}

function validateTaskPacketModel(taskText, modelInfo) {
  const modelHeadingCount = markdownHeadings(taskText).filter((heading) => heading === "Cursor Model").length;
  if (modelHeadingCount !== 1) return { ok: false, message: `task packet requires exactly one Cursor Model section; found ${modelHeadingCount}` };
  const modelSection = sectionBody(taskText, "Cursor Model");
  if (!modelSection) return { ok: false, message: "task packet requires a non-empty Cursor Model section" };
  const profiles = taskPacketFieldValues(modelSection, "Wrapper profile");
  const models = taskPacketFieldValues(modelSection, "Model");
  const modelParams = taskPacketFieldValues(modelSection, "Model params");
  if (profiles.length !== 1 || models.length !== 1 || modelParams.length !== 1) {
    return { ok: false, message: "Cursor Model section requires exactly one Wrapper profile, Model, and Model params field" };
  }
  if (modelInfo.isDefault) {
    if (profiles[0] !== DEFAULT_MODEL_PROFILE_NAME || models[0] !== DEFAULT_MODEL_LABEL || modelParams[0] !== DEFAULT_MODEL_PARAMS_MARKER) {
      return { ok: false, message: `Cursor Model section must declare ${DEFAULT_MODEL_LABEL}` };
    }
  } else {
    if (profiles[0] !== "explicit" || models[0] !== modelInfo.selection.id) {
      return { ok: false, message: `Cursor Model section does not exclusively match requested model ${modelInfo.selection.id}` };
    }
    try {
      const packetSelection = { id: models[0], params: parsePacketModelParams(modelParams[0]) };
      const requestedSelection = { id: modelInfo.selection.id, params: normalizeArray(modelInfo.selection.params) };
      if (!modelSelectionsEqual(packetSelection, requestedSelection)) {
        return { ok: false, message: "Cursor Model section Model params do not exactly match wrapper arguments" };
      }
    } catch (err) {
      return { ok: false, message: err.message };
    }
  }
  return { ok: true, message: "task packet model accepted" };
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
  if (args.autoCreatePr) flags.push("--auto-create-pr");
  if (args.workOnCurrentBranch) flags.push("--work-on-current-branch");
  if (args.skipReviewerRequest) flags.push("--skip-reviewer-request");
  if (args.sdkMode === "agent" && !args.apply) flags.push("--sdk-mode agent outside apply mode");
  if (normalizeArray(args.settingSource).some((source) => source !== "project")) flags.push("non-project --setting-source");
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

function assertNoEscapingSymlinks(root, current = root) {
  for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
    const child = path.join(current, entry.name);
    if (!copyIgnore(child)) continue;
    if (entry.isSymbolicLink()) {
      const target = fs.readlinkSync(child);
      const linkDirectory = path.relative(root, path.dirname(child));
      const relocatedTarget = path.normalize(path.join(linkDirectory, target));
      const escapes = path.isAbsolute(target)
        || path.isAbsolute(relocatedTarget)
        || relocatedTarget === ".."
        || relocatedTarget.startsWith(`..${path.sep}`);
      if (!escapes) continue;
      throw new UserFacingError(`Read-only workspace copy refuses symlink that can escape the copy: ${path.relative(root, child)}`);
    }
    if (entry.isDirectory()) assertNoEscapingSymlinks(root, child);
  }
}

function chmodOwnerWritableRecursive(root) {
  if (!fs.existsSync(root)) return;
  const stat = fs.lstatSync(root);
  if (stat.isSymbolicLink()) return;
  const mode = stat.mode & 0o777;
  fs.chmodSync(root, stat.isDirectory() ? (mode | 0o700) : (mode | 0o600));
  if (!stat.isDirectory()) return;
  for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
    chmodOwnerWritableRecursive(path.join(root, entry.name));
  }
}

function removeReadonlyCopySync(root) {
  if (!root || !fs.existsSync(root)) return;
  chmodOwnerWritableRecursive(root);
  fs.rmSync(root, { recursive: true, force: true });
  if (fs.existsSync(root)) throw new UserFacingError(`Failed to remove read-only workspace copy: ${root}`);
}

function makeReadonlyCopy(workspace) {
  assertNoEscapingSymlinks(workspace);
  const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), "cursor-sdk-delegate-readonly-"));
  const target = path.join(tempRoot, path.basename(workspace));
  try {
    fs.cpSync(workspace, target, { recursive: true, dereference: false, filter: copyIgnore });
    assertNoEscapingSymlinks(target);
    chmodReadOnlyRecursive(target);
    return target;
  } catch (err) {
    removeReadonlyCopySync(tempRoot);
    throw err;
  }
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
  const successPayload = result.status === "success" && result.value && typeof result.value === "object"
    ? result.value
    : (result.success && typeof result.success === "object" ? result.success : undefined);
  if (successPayload) {
    const keys = (event.name === "task" || event.name === "taskToolCall" || event.name === "Agent")
      ? ["agentId", "isBackground", "durationMs"]
      : ["path", "linesCreated", "linesModified", "fileSize", "totalLines", "totalChars", "isEmpty", "exceededLimit"];
    return { status: "success", ...primitiveSummary(successPayload, keys) };
  }
  if ((result.status === "error" || result.error) && result.error && typeof result.error === "object") {
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
    if (event.model) {
      status.system_model_selection = safeModelSelection(event.model);
      status.resolved_model = redactText(JSON.stringify(status.system_model_selection || event.model), 240);
    }
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
    "The SDK internal task/Agent-tool model field is string-only; report that child model as requested or observed, never as verified High effort unless structured SDK evidence is available.",
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

function createSendOptions(args, modelInfo, sdkMode) {
  const options = { model: modelInfo.selection, mode: sdkMode };
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

async function dispatchOnce({ sdk, args, apiKey, activeWorkspace, modelInfo, prompt, status, statusFile, rawEventsFile, metadata, metadataFile, runtimeControl }) {
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
      ? await Agent.resume(args.resumeAgentId, agentOptions)
      : await Agent.create(agentOptions);
    runtimeControl.agent = agent;
    status.agent_id = redactText(agent.agentId, 120);
    status.state = "running";
    await writeJson(statusFile, status);

    const run = await agent.send(prompt, createSendOptions(args, modelInfo, sdkMode));
    runtimeControl.run = run;
    status.run_id = redactText(run.id, 120);
    if (run.requestId) status.request_id = redactText(run.requestId, 160);
    await writeJson(statusFile, status);

    await streamRun({ run, status, statusFile, rawEventsFile });
    const result = await run.wait();
    const modelVerification = verifyResolvedModel(
      modelInfo.selection,
      status.system_model_selection,
      result.model,
      { allowedAdditionalParams: modelInfo.allowedObservedSpeedParams },
    );
    status.state = result.status === "finished" ? (modelVerification.verified ? "succeeded" : "failed") : result.status;
    status.result = {
      status: result.status,
      request_id: redactText(result.requestId, 160),
      duration_ms: result.durationMs,
      text: redactText(result.result),
      error: result.error ? { message: redactText(result.error.message), code: redactText(result.error.code, 120) } : undefined,
      usage: result.usage,
      model: modelVerification.resultModel,
      system_model: modelVerification.systemModel,
      result_model_matches_requested: modelVerification.resultMatchesRequested,
      system_model_matches_requested: modelVerification.systemMatchesRequested,
      model_verification: modelVerification.status,
      model_verification_scope: modelVerification.scope,
      git: result.git ? { branches_count: result.git.branches?.length || 0 } : undefined,
    };
    metadata.finished_at_utc = utcNow();
    metadata.result_status = result.status;
    metadata.request_id = redactText(result.requestId, 160);
    metadata.duration_ms = result.durationMs;
    metadata.usage = result.usage;
    metadata.result_model = modelVerification.resultModel;
    metadata.system_model = modelVerification.systemModel;
    metadata.result_model_matches_requested = modelVerification.resultMatchesRequested;
    metadata.system_model_matches_requested = modelVerification.systemMatchesRequested;
    metadata.model_verification = modelVerification.status;
    metadata.model_verification_scope = modelVerification.scope;
    await writeJson(statusFile, status);
    await writeJson(metadataFile, metadata);
    if (status.stream_supported === false && result.result) process.stdout.write(`\n${result.result}\n`);
    return result.status === "finished" && modelVerification.verified ? 0 : 1;
  } finally {
    runtimeControl.run = undefined;
    if (agent) {
      if (typeof agent[Symbol.asyncDispose] === "function") await agent[Symbol.asyncDispose]();
      else if (typeof agent.close === "function") agent.close();
    }
    runtimeControl.agent = undefined;
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
      model: { type: "string", default: DEFAULT_MODEL_PROFILE_NAME },
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
  const requestedModelInfo = modelSelectionFromArgs(args);

  if (!requestedModelInfo.isDefault && !args.userAuthorizedModel) {
    throw new UserFacingError(`Refusing Cursor model override ${args.model}. Default to logical profile ${DEFAULT_MODEL_PROFILE_NAME} (${DEFAULT_MODEL_LABEL}) unless the user explicitly directed Cursor to use a different model.`);
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
  const packetModel = validateTaskPacketModel(taskText, requestedModelInfo);
  if (!packetModel.ok) throw new UserFacingError(`Refusing dispatch: ${packetModel.message}`);

  const unsafeOverrides = collectUnsafeOverrides(args, requestedModelInfo);
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
  if (args.resumeAgentId && useCopy) {
    throw new UserFacingError("--resume-agent-id cannot use a new read-only workspace copy because local agent state is workspace-scoped. Use the original workspace with --workspace-copy never and an explicit --override-reason, or start a new inspect/proposal agent.");
  }
  const activeWorkspace = useCopy && !args.dryRun ? makeReadonlyCopy(workspace) : workspace;
  const workspaceCopyRoot = useCopy && !args.dryRun ? path.dirname(activeWorkspace) : undefined;
  let workspaceCopyCleaned = false;
  function cleanupWorkspaceCopySync() {
    if (workspaceCopyRoot && !args.keepWorkspaceCopy && !workspaceCopyCleaned) {
      try {
        removeReadonlyCopySync(workspaceCopyRoot);
        workspaceCopyCleaned = !fs.existsSync(workspaceCopyRoot);
      } catch (err) {
        process.stderr.write(`Failed to clean read-only workspace copy: ${redactText(err?.message || err)}\n`);
      }
    }
  }
  if (workspaceCopyRoot) process.once("exit", cleanupWorkspaceCopySync);
  const runtimeControl = {
    run: undefined,
    agent: undefined,
    status: undefined,
    statusFile: undefined,
    metadata: undefined,
    metadataFile: undefined,
    stopping: false,
  };
  async function stopForSignal(signal, exitCode) {
    if (runtimeControl.stopping) return;
    runtimeControl.stopping = true;
    try {
      if (runtimeControl.run && typeof runtimeControl.run.cancel === "function") {
        await Promise.race([
          runtimeControl.run.cancel(),
          new Promise((resolve) => setTimeout(resolve, 5000)),
        ]);
      }
      const activeAgent = runtimeControl.agent;
      if (activeAgent && typeof activeAgent[Symbol.asyncDispose] === "function") await activeAgent[Symbol.asyncDispose]();
      else if (activeAgent && typeof activeAgent.close === "function") activeAgent.close();
    } catch (err) {
      process.stderr.write(`Failed to stop Cursor SDK run cleanly after ${signal}: ${redactText(err?.message || err)}\n`);
    } finally {
      try {
        const finishedAt = utcNow();
        if (runtimeControl.status && runtimeControl.statusFile) {
          runtimeControl.status.state = "cancelled";
          runtimeControl.status.signal = signal;
          runtimeControl.status.updated_at_utc = finishedAt;
          runtimeControl.status.current_tool_call = null;
          await writeJson(runtimeControl.statusFile, runtimeControl.status);
        }
        if (runtimeControl.metadata && runtimeControl.metadataFile) {
          runtimeControl.metadata.finished_at_utc = finishedAt;
          runtimeControl.metadata.result_status = "cancelled";
          runtimeControl.metadata.signal = signal;
          await writeJson(runtimeControl.metadataFile, runtimeControl.metadata);
        }
      } catch (err) {
        process.stderr.write(`Failed to persist cancelled Cursor SDK status after ${signal}: ${redactText(err?.message || err)}\n`);
      }
      cleanupWorkspaceCopySync();
      process.exit(exitCode);
    }
  }
  process.once("SIGINT", () => { void stopForSignal("SIGINT", 130); });
  process.once("SIGTERM", () => { void stopForSignal("SIGTERM", 143); });
  const sdkMode = args.sdkMode || (args.apply ? "agent" : "plan");
  let prompt = buildPrompt({ taskFile, taskText, args, detectedSource, activeWorkspace: args.runtime === "local" ? activeWorkspace : undefined, originalWorkspace: args.runtime === "local" ? workspace : undefined, modelInfo: requestedModelInfo, sdkMode });
  const logBase = path.resolve(args.logDir || path.join(workspace, ".agent", "delegations"));

  if (args.dryRun) {
    console.log("Cursor SDK dispatch dry run");
    console.log(JSON.stringify({
      runtime: args.runtime,
      mode: args.apply ? "apply" : (args.inspectOnly ? "inspect-only" : "proposal"),
      sdkMode,
      modelProfile: requestedModelInfo.profile,
      model: requestedModelInfo.selection,
      modelLabel: requestedModelInfo.label,
      modelCatalogValidation: "deferred until authorized live dispatch",
      detectedAuthoritySource: detectedSource,
      authorityValidation: authority.message,
      taskPacketModelValidation: packetModel.message,
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
    task_packet_model_validation: packetModel.message,
    runtime: args.runtime,
    mode: args.apply ? "apply" : (args.inspectOnly ? "inspect-only" : "proposal"),
    sdk_mode: sdkMode,
    model_profile: requestedModelInfo.profile,
    model: requestedModelInfo.label,
    model_catalog_verified: false,
    user_authorized_model_override: Boolean(args.userAuthorizedModel),
    raw_events_enabled: Boolean(rawEventsFile),
    unsafe_overrides: unsafeOverrides.map((flag) => ({ flag, reason: redactText(args.overrideReason) })),
    delegation_owner: redactText(args.delegationOwner, 160),
    workstream_id: redactText(args.workstreamId, 160),
    idempotency_key_sha256: args.idempotencyKey ? crypto.createHash("sha256").update(args.idempotencyKey).digest("hex") : undefined,
    task_packet_sha256: crypto.createHash("sha256").update(taskText).digest("hex"),
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
    model_profile: requestedModelInfo.profile,
    model: requestedModelInfo.label,
    model_catalog_verified: false,
    delegation_owner: redactText(args.delegationOwner, 160),
    workstream_id: redactText(args.workstreamId, 160),
    idempotency_key_sha256: metadata.idempotency_key_sha256,
    task_packet_sha256: metadata.task_packet_sha256,
    sandbox_enabled: args.runtime === "local" ? args.sandbox !== "disabled" : undefined,
    started_at_utc: startedAt,
    updated_at_utc: startedAt,
    events_seen: 0,
    current_tool_call: null,
    recent_tool_calls: [],
    active_subagents: {},
    recent_subagents: [],
  };
  runtimeControl.status = status;
  runtimeControl.statusFile = statusFile;
  runtimeControl.metadata = metadata;
  runtimeControl.metadataFile = metadataFile;
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
      const modelInfo = await resolveModelInfoWithSdk(sdk, apiKey, requestedModelInfo);
      prompt = buildPrompt({ taskFile, taskText, args, detectedSource, activeWorkspace: args.runtime === "local" ? activeWorkspace : undefined, originalWorkspace: args.runtime === "local" ? workspace : undefined, modelInfo, sdkMode });
      await fsp.writeFile(promptFile, prompt, "utf8");
      metadata.model = modelInfo.label;
      metadata.model_selection = modelInfo.selection;
      metadata.model_allowed_observed_speed_params = modelInfo.allowedObservedSpeedParams;
      metadata.model_catalog_verified = true;
      metadata.catalog_model_id = modelInfo.catalogModelId;
      status.model = modelInfo.label;
      status.model_selection = modelInfo.selection;
      status.model_allowed_observed_speed_params = modelInfo.allowedObservedSpeedParams;
      status.model_catalog_verified = true;
      await writeJson(metadataFile, metadata);
      await writeJson(statusFile, status);
      return await dispatchOnce({ sdk, args, apiKey, activeWorkspace, modelInfo, prompt, status, statusFile, rawEventsFile, metadata, metadataFile, runtimeControl });
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

function isDirectInvocation(argvPath = process.argv[1]) {
  if (!argvPath) return false;
  const modulePath = fileURLToPath(import.meta.url);
  try {
    return fs.realpathSync(argvPath) === fs.realpathSync(modulePath);
  } catch {
    return path.resolve(argvPath) === modulePath;
  }
}

if (isDirectInvocation()) {
  main().then((code) => {
    process.exitCode = code;
  }).catch((err) => {
    const code = err?.exitCode || (isAuthenticationError(err) ? 2 : 1);
    const helpUrl = err?.helpUrl ? `\nHelp URL: ${redactUrl(err.helpUrl)}` : "";
    console.error(`${err?.message || err}${helpUrl}`);
    process.exitCode = code;
  });
}

export {
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
};
