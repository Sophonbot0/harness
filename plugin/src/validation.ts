import * as fs from "node:fs";
import * as path from "node:path";
import * as os from "node:os";
import type {
  ChallengeContractDocument,
  ContractItem,
  DodItem,
  EvalContractDocument,
  Feature,
  PlanContractDocument,
} from "./state.js";

// ─── Parameter Validation Helpers (HIGH 1) ───

export function readStringParam(params: Record<string, unknown>, key: string): string {
  const val = params[key];
  if (val === undefined || val === null) {
    throw new Error(`Missing required parameter: ${key}`);
  }
  if (typeof val !== "string") {
    throw new Error(`Parameter '${key}' must be a string, got ${typeof val}`);
  }
  const trimmed = val.trim();
  if (trimmed.length === 0) {
    throw new Error(`Parameter '${key}' must not be empty`);
  }
  return trimmed;
}

export function readOptionalStringParam(params: Record<string, unknown>, key: string): string | undefined {
  const val = params[key];
  if (val === undefined || val === null) return undefined;
  if (typeof val !== "string") {
    throw new Error(`Parameter '${key}' must be a string, got ${typeof val}`);
  }
  const trimmed = val.trim();
  return trimmed.length === 0 ? undefined : trimmed;
}

export function readStringArrayParam(params: Record<string, unknown>, key: string): string[] {
  const val = params[key];
  if (val === undefined || val === null) {
    throw new Error(`Missing required parameter: ${key}`);
  }
  if (!Array.isArray(val)) {
    throw new Error(`Parameter '${key}' must be an array, got ${typeof val}`);
  }
  for (let i = 0; i < val.length; i++) {
    if (typeof val[i] !== "string") {
      throw new Error(`Parameter '${key}[${i}]' must be a string, got ${typeof val[i]}`);
    }
  }
  return val as string[];
}

/** Validate and sanitize a file path. Rejects traversal and paths outside allowed directories. */
export function sanitizePath(filePath: string, paramName: string): string {
  const resolved = path.resolve(filePath);
  if (filePath.includes("..")) {
    throw new Error(`Parameter '${paramName}' must not contain '..' path traversal`);
  }
  const home = os.homedir();
  const allowedPrefixes = [
    path.join(home, ".openclaw"),
    path.join(home, "Projects"),
  ];
  const isAllowed = allowedPrefixes.some(prefix => resolved.startsWith(prefix));
  if (!isAllowed) {
    throw new Error(`Parameter '${paramName}' must be under ~/.openclaw or ~/Projects (got: ${resolved})`);
  }
  return resolved;
}

// ─── DoD Extraction (MEDIUM 4) ───

/** Extract DoD items (checkbox lines) from markdown content.
 *  Supports `- [ ]`, `* [ ]`, indented checkboxes.
 *  Ignores checkboxes inside fenced code blocks.
 */
export function extractDodItems(content: string): DodItem[] {
  const lines = content.split("\n");
  const items: DodItem[] = [];
  let inCodeBlock = false;

  for (const line of lines) {
    // Track fenced code blocks
    if (/^\s*```/.test(line)) {
      inCodeBlock = !inCodeBlock;
      continue;
    }
    if (inCodeBlock) continue;

    const trimmed = line.trim();
    // Match - [ ], - [x], * [ ], * [x] with optional leading whitespace (already trimmed)
    const m = trimmed.match(/^[-*]\s+\[([ xX])\]\s+(.*)/);
    if (m) {
      const checked = m[1].toLowerCase() === "x";
      items.push({ text: m[2], checked });
    }
  }
  return items;
}

/** Read a file safely, returning null on error. */
export function safeReadFile(filePath: string): string | null {
  try {
    if (!fs.existsSync(filePath)) return null;
    return fs.readFileSync(filePath, "utf-8");
  } catch {
    return null;
  }
}

/** Read JSON safely, returning null on error. */
export function safeReadJson<T = unknown>(filePath: string): T | null {
  try {
    if (!fs.existsSync(filePath)) return null;
    return JSON.parse(fs.readFileSync(filePath, "utf-8")) as T;
  } catch {
    return null;
  }
}

/** Check if eval report contains "Overall: PASS". Returns { passed, reason }. */
export function checkEvalReport(content: string): { passed: boolean; reason: string } {
  const passPattern = /overall\s*:\s*pass/i;
  const failPattern = /overall\s*:\s*fail/i;
  if (passPattern.test(content)) {
    return { passed: true, reason: "Eval report indicates PASS" };
  }
  if (failPattern.test(content)) {
    const lines = content.split("\n");
    const failLine = lines.find((l) => failPattern.test(l));
    return { passed: false, reason: `Eval report indicates FAIL: ${failLine?.trim() ?? "no details"}` };
  }
  return { passed: false, reason: "Eval report does not contain 'Overall: PASS' — cannot verify passing grade" };
}

function firstMeaningfulParagraph(content: string): string {
  for (const rawLine of content.split("\n")) {
    const line = rawLine.trim();
    if (!line) continue;
    if (line.startsWith("#")) continue;
    if (/^overall\s*:/i.test(line)) continue;
    if (/^confidence(?:\s+rating|\s+assessment)?\s*:/i.test(line)) continue;
    return line;
  }
  return "No summary provided.";
}

function parseConfidenceRating(content: string): number | undefined {
  const match = content.match(/confidence(?:\s+rating|\s+assessment)?[^\d]{0,12}([1-5])\b/i);
  if (!match) return undefined;
  return Number.parseInt(match[1], 10);
}

function extractSectionBullets(content: string, sectionNames: string[]): string[] {
  const wanted = sectionNames.map((name) => name.toLowerCase());
  const lines = content.split("\n");
  const bullets: string[] = [];
  let capture = false;

  for (const rawLine of lines) {
    const headingMatch = rawLine.match(/^#{2,6}\s+(.*)$/);
    if (headingMatch) {
      const heading = headingMatch[1].toLowerCase();
      capture = wanted.some((name) => heading.includes(name));
      continue;
    }
    if (!capture) continue;
    const bulletMatch = rawLine.trim().match(/^[-*]\s+(.*)$/);
    if (bulletMatch && bulletMatch[1].trim().length > 0) {
      bullets.push(bulletMatch[1].trim());
    }
  }

  return bullets;
}

function buildSyntheticDodVerdict(overall: "PASS" | "FAIL", summary: string): EvalContractDocument["dodVerdicts"] {
  return [{
    description: `Overall evaluator verdict: ${overall}`,
    verdict: overall,
    evidence: summary,
  }];
}

function extractEvalDodVerdicts(content: string, overall: "PASS" | "FAIL", summary: string): NonNullable<EvalContractDocument["dodVerdicts"]> {
  const verdicts: NonNullable<EvalContractDocument["dodVerdicts"]> = [];
  for (const rawLine of content.split("\n")) {
    const line = rawLine.trim();
    if (!line || /^overall\s*:/i.test(line)) continue;
    const verdictMatch = line.match(/\b(BONUS PASS|BONUS FAIL|PASS|FAIL)\b/i);
    if (!verdictMatch) continue;
    const verdictToken = verdictMatch[1].toUpperCase().replace(/\s+/g, "_") as NonNullable<EvalContractDocument["dodVerdicts"]>[number]["verdict"];
    const cleaned = line
      .replace(/^[-*]\s+/, "")
      .replace(/^\d+[.)]\s+/, "")
      .trim();
    verdicts.push({
      description: cleaned,
      verdict: verdictToken,
      evidence: cleaned,
    });
  }
  return verdicts.length > 0 ? verdicts : buildSyntheticDodVerdict(overall, summary);
}

function extractEvalChallengeVerdicts(content: string): NonNullable<EvalContractDocument["challengeVerdicts"]> {
  const verdicts: NonNullable<EvalContractDocument["challengeVerdicts"]> = [];
  for (const rawLine of content.split("\n")) {
    const line = rawLine.trim();
    if (!line) continue;
    const challengeIdMatch = line.match(/\b(crit-\d+|challenge[-_a-z0-9]+)\b/i);
    if (!challengeIdMatch) continue;
    const dispositionMatch = line.match(/\b(CONFIRMED|DISMISSED|PASS|FAIL)\b/i);
    if (!dispositionMatch) continue;
    const token = dispositionMatch[1].toUpperCase();
    verdicts.push({
      challengeId: challengeIdMatch[1],
      disposition: token === "CONFIRMED" || token === "FAIL" ? "CONFIRMED" : "DISMISSED",
      evidence: line,
    });
  }
  return verdicts;
}

export function buildEvalContract(
  runId: string,
  reportPath: string,
  content: string,
): EvalContractDocument {
  const overallMatch = content.match(/overall\s*:\s*(pass|fail)\b/i);
  if (!overallMatch) {
    throw new Error("Eval report is missing a machine-checkable 'Overall: PASS|FAIL' marker.");
  }

  const overall = overallMatch[1].toUpperCase() as "PASS" | "FAIL";
  const summary = firstMeaningfulParagraph(content);
  const unresolvedCriticalChallengeIds = extractSectionBullets(content, ["unresolved critical challenges"])
    .map((line) => {
      const match = line.match(/\b(crit-\d+|challenge[-_a-z0-9]+)\b/i);
      return match?.[1];
    })
    .filter((value): value is string => Boolean(value));

  return {
    schemaVersion: "harness.phase1.v1",
    kind: "eval_contract",
    runId,
    createdAt: new Date().toISOString(),
    reportPath,
    overall,
    grade: overall,
    summary,
    confidence: parseConfidenceRating(content),
    rationale: summary,
    dodVerdicts: extractEvalDodVerdicts(content, overall, summary),
    challengeVerdicts: extractEvalChallengeVerdicts(content),
    unresolvedCriticalChallengeIds,
  };
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function isValidIsoTimestamp(value: unknown): value is string {
  return isNonEmptyString(value) && !Number.isNaN(Date.parse(value));
}

function detectDependencyCycle(items: ContractItem[]): string | null {
  const graph = new Map<string, string[]>();
  for (const item of items) {
    graph.set(item.id, Array.isArray(item.dependsOn) ? item.dependsOn : []);
  }

  const visiting = new Set<string>();
  const visited = new Set<string>();

  function visit(node: string, trail: string[]): string | null {
    if (visiting.has(node)) return [...trail, node].join(" -> ");
    if (visited.has(node)) return null;
    visiting.add(node);
    for (const dep of graph.get(node) ?? []) {
      const cycle = visit(dep, [...trail, node]);
      if (cycle) return cycle;
    }
    visiting.delete(node);
    visited.add(node);
    return null;
  }

  for (const item of items) {
    const cycle = visit(item.id, []);
    if (cycle) return cycle;
  }
  return null;
}

function normalizeEvalGrade(value: string): string {
  return value.trim().toUpperCase().replace(/\s+/g, "_");
}

export function validateEvalContract(doc: EvalContractDocument): string[] {
  const errors: string[] = [];
  if (doc.schemaVersion !== "harness.phase1.v1") errors.push("eval_contract.schemaVersion must be harness.phase1.v1");
  if (doc.kind !== "eval_contract") errors.push("eval_contract.kind must be eval_contract");
  if (!isNonEmptyString(doc.runId)) errors.push("eval_contract.runId is required");
  if (!isValidIsoTimestamp(doc.createdAt)) errors.push("eval_contract.createdAt must be a valid ISO timestamp");
  if (!isNonEmptyString(doc.reportPath)) errors.push("eval_contract.reportPath is required");
  if (isNonEmptyString(doc.reportPath) && !path.isAbsolute(doc.reportPath)) errors.push("eval_contract.reportPath must be an absolute path");
  if (doc.overall !== "PASS" && doc.overall !== "FAIL") errors.push("eval_contract.overall must be PASS or FAIL");
  if (!isNonEmptyString(doc.grade)) errors.push("eval_contract.grade is required");
  if (isNonEmptyString(doc.grade) && normalizeEvalGrade(doc.grade) !== doc.overall) errors.push("eval_contract.grade must match overall");
  if (!isNonEmptyString(doc.summary)) errors.push("eval_contract.summary is required");
  if (doc.confidence !== undefined && (!Number.isFinite(doc.confidence) || doc.confidence < 1 || doc.confidence > 5)) {
    errors.push("eval_contract.confidence must be between 1 and 5 when provided");
  }
  if (doc.rationale !== undefined && !isNonEmptyString(doc.rationale)) {
    errors.push("eval_contract.rationale must be a non-empty string when provided");
  }

  if (doc.dodVerdicts !== undefined) {
    if (!Array.isArray(doc.dodVerdicts)) {
      errors.push("eval_contract.dodVerdicts must be an array when provided");
    } else if (doc.dodVerdicts.length === 0) {
      errors.push("eval_contract.dodVerdicts must not be empty when provided");
    } else {
      let coreFails = 0;
      doc.dodVerdicts.forEach((verdict, index) => {
        if (verdict.itemId !== undefined && !isNonEmptyString(verdict.itemId)) {
          errors.push(`eval_contract.dodVerdicts[${index}].itemId must be a non-empty string when provided`);
        }
        if (!isNonEmptyString(verdict?.description)) {
          errors.push(`eval_contract.dodVerdicts[${index}].description must be a non-empty string`);
        }
        if (!["PASS", "FAIL", "BONUS_PASS", "BONUS_FAIL"].includes(String(verdict?.verdict))) {
          errors.push(`eval_contract.dodVerdicts[${index}].verdict must be PASS|FAIL|BONUS_PASS|BONUS_FAIL`);
        }
        if (!isNonEmptyString(verdict?.evidence)) {
          errors.push(`eval_contract.dodVerdicts[${index}].evidence must be a non-empty string`);
        }
        if (verdict?.verdict === "FAIL") coreFails += 1;
      });
      if (doc.overall === "PASS" && coreFails > 0) {
        errors.push("eval_contract.overall must be FAIL when any core DoD verdict is FAIL");
      }
      if (doc.overall === "FAIL" && coreFails === 0 && (!doc.unresolvedCriticalChallengeIds || doc.unresolvedCriticalChallengeIds.length === 0)) {
        errors.push("eval_contract.FAIL must include either a FAIL DoD verdict or unresolved critical challenges");
      }
    }
  }

  if (doc.challengeVerdicts !== undefined) {
    if (!Array.isArray(doc.challengeVerdicts)) {
      errors.push("eval_contract.challengeVerdicts must be an array when provided");
    } else {
      const ids = new Set<string>();
      doc.challengeVerdicts.forEach((verdict, index) => {
        if (!isNonEmptyString(verdict?.challengeId)) {
          errors.push(`eval_contract.challengeVerdicts[${index}].challengeId must be a non-empty string`);
        } else if (ids.has(verdict.challengeId)) {
          errors.push(`eval_contract.challengeVerdicts has duplicate challengeId '${verdict.challengeId}'`);
        } else {
          ids.add(verdict.challengeId);
        }
        if (verdict?.disposition !== "CONFIRMED" && verdict?.disposition !== "DISMISSED") {
          errors.push(`eval_contract.challengeVerdicts[${index}].disposition must be CONFIRMED or DISMISSED`);
        }
        if (!isNonEmptyString(verdict?.evidence)) {
          errors.push(`eval_contract.challengeVerdicts[${index}].evidence must be a non-empty string`);
        }
      });
    }
  }

  if (doc.unresolvedCriticalChallengeIds !== undefined) {
    if (!Array.isArray(doc.unresolvedCriticalChallengeIds)) {
      errors.push("eval_contract.unresolvedCriticalChallengeIds must be an array when provided");
    } else {
      const ids = new Set<string>();
      doc.unresolvedCriticalChallengeIds.forEach((id, index) => {
        if (!isNonEmptyString(id)) {
          errors.push(`eval_contract.unresolvedCriticalChallengeIds[${index}] must be a non-empty string`);
        } else if (ids.has(id)) {
          errors.push(`eval_contract.unresolvedCriticalChallengeIds has duplicate id '${id}'`);
        } else {
          ids.add(id);
        }
      });
      if (doc.overall === "PASS" && doc.unresolvedCriticalChallengeIds.length > 0) {
        errors.push("eval_contract.overall must be FAIL when unresolvedCriticalChallengeIds are present");
      }
    }
  }

  return errors;
}

/** Check challenge report for unaddressed CRITICAL issues. */
export function findUnaddressedCriticals(content: string): string[] {
  const lines = content.split("\n");
  const criticals: string[] = [];
  let inCritical = false;
  for (const line of lines) {
    const trimmed = line.trim();
    if (/critical/i.test(trimmed) && !/addressed|resolved|fixed|mitigated/i.test(trimmed)) {
      if (trimmed.startsWith("- [ ]") || trimmed.startsWith("- ")) {
        if (!/\[x\]/i.test(trimmed)) {
          criticals.push(trimmed);
        }
      } else if (/^#+\s.*critical/i.test(trimmed)) {
        inCritical = true;
      }
    }
    if (inCritical && trimmed.startsWith("- [ ]")) {
      criticals.push(trimmed);
    }
    if (inCritical && /^#+\s/.test(trimmed) && !/critical/i.test(trimmed)) {
      inCritical = false;
    }
  }
  return criticals;
}

/** Count unchecked DoD items from plan content. */
export function findUncheckedDod(planContent: string): string[] {
  const items = extractDodItems(planContent);
  return items.filter((i) => !i.checked).map((i) => i.text);
}

export function buildPlanContract(
  runId: string,
  taskDescription: string,
  planPath: string,
  dodItems: DodItem[],
  features: Feature[],
  contractItems: ContractItem[],
  verifyCommand?: string,
): PlanContractDocument {
  return {
    schemaVersion: "harness.phase1.v1",
    kind: "plan_contract",
    runId,
    taskDescription,
    createdAt: new Date().toISOString(),
    planPath,
    ...(verifyCommand ? { verifyCommand } : {}),
    dodItems,
    features,
    contractItems,
  };
}

function validateDodItemsSchema(items: DodItem[]): string[] {
  const errors: string[] = [];
  items.forEach((item, index) => {
    if (!item || typeof item.text !== "string" || item.text.trim().length === 0) {
      errors.push(`plan_contract.dodItems[${index}].text must be a non-empty string`);
    }
    if (typeof item.checked !== "boolean") {
      errors.push(`plan_contract.dodItems[${index}].checked must be boolean`);
    }
  });
  return errors;
}

function validateFeaturesSchema(features: Feature[]): string[] {
  const errors: string[] = [];
  const ids = new Set<string>();
  const allowedStatuses = new Set(["pending", "in_progress", "passed", "failed", "deferred"]);
  const allowedVerifiedBy = new Set(["test", "build", "manual", "lint"]);
  features.forEach((feature, index) => {
    if (!isNonEmptyString(feature?.id)) {
      errors.push(`plan_contract.features[${index}].id must be a non-empty string`);
    } else if (ids.has(feature.id)) {
      errors.push(`plan_contract.features has duplicate id '${feature.id}'`);
    } else {
      ids.add(feature.id);
    }
    if (!isNonEmptyString(feature?.category)) {
      errors.push(`plan_contract.features[${index}].category must be a non-empty string`);
    }
    if (!isNonEmptyString(feature?.description)) {
      errors.push(`plan_contract.features[${index}].description must be a non-empty string`);
    }
    if (!allowedStatuses.has(feature?.status)) {
      errors.push(`plan_contract.features[${index}].status is invalid`);
    }
    if (feature?.verifiedAt !== undefined && !isValidIsoTimestamp(feature.verifiedAt)) {
      errors.push(`plan_contract.features[${index}].verifiedAt must be a valid ISO timestamp`);
    }
    if (feature?.verifiedBy !== undefined && !allowedVerifiedBy.has(feature.verifiedBy)) {
      errors.push(`plan_contract.features[${index}].verifiedBy is invalid`);
    }
  });
  return errors;
}

function validateContractItemsSchema(items: ContractItem[]): string[] {
  const errors: string[] = [];
  const ids = new Set<string>();
  const allowedStatuses = new Set(["pending", "in_progress", "passed", "failed", "skipped"]);
  items.forEach((item, index) => {
    if (!isNonEmptyString(item?.id)) {
      errors.push(`plan_contract.contractItems[${index}].id must be a non-empty string`);
    } else if (ids.has(item.id)) {
      errors.push(`plan_contract.contractItems has duplicate id '${item.id}'`);
    } else {
      ids.add(item.id);
    }
    if (!isNonEmptyString(item?.description)) {
      errors.push(`plan_contract.contractItems[${index}].description must be a non-empty string`);
    }
    if (!Array.isArray(item?.acceptanceCriteria)) {
      errors.push(`plan_contract.contractItems[${index}].acceptanceCriteria must be an array`);
    } else if (item.acceptanceCriteria.length === 0) {
      errors.push(`plan_contract.contractItems[${index}].acceptanceCriteria must not be empty`);
    } else {
      item.acceptanceCriteria.forEach((criterion, acIndex) => {
        if (!isNonEmptyString(criterion)) {
          errors.push(`plan_contract.contractItems[${index}].acceptanceCriteria[${acIndex}] must be a non-empty string`);
        }
      });
    }
    if (!allowedStatuses.has(item?.status)) {
      errors.push(`plan_contract.contractItems[${index}].status is invalid`);
    }
    if (typeof item?.attempts !== "number" || item.attempts < 0) {
      errors.push(`plan_contract.contractItems[${index}].attempts must be a non-negative number`);
    }
    if (typeof item?.maxAttempts !== "number" || item.maxAttempts < 1) {
      errors.push(`plan_contract.contractItems[${index}].maxAttempts must be >= 1`);
    }
    if (typeof item?.attempts === "number" && typeof item?.maxAttempts === "number" && item.attempts > item.maxAttempts) {
      errors.push(`plan_contract.contractItems[${index}].attempts must not exceed maxAttempts`);
    }
    if (item?.status === "skipped" && !isNonEmptyString(item.skipReason)) {
      errors.push(`plan_contract.contractItems[${index}].skipReason is required when status=skipped`);
    }
    if (item?.startedAt !== undefined && !isValidIsoTimestamp(item.startedAt)) {
      errors.push(`plan_contract.contractItems[${index}].startedAt must be a valid ISO timestamp`);
    }
    if (item?.completedAt !== undefined && !isValidIsoTimestamp(item.completedAt)) {
      errors.push(`plan_contract.contractItems[${index}].completedAt must be a valid ISO timestamp`);
    }
    if (item?.timeoutMinutes !== undefined && (typeof item.timeoutMinutes !== "number" || item.timeoutMinutes <= 0)) {
      errors.push(`plan_contract.contractItems[${index}].timeoutMinutes must be > 0`);
    }
    if (item?.verifyCommand !== undefined && !isNonEmptyString(item.verifyCommand)) {
      errors.push(`plan_contract.contractItems[${index}].verifyCommand must be a non-empty string when provided`);
    }
    if (item?.verifyFileExists !== undefined) {
      if (!Array.isArray(item.verifyFileExists)) {
        errors.push(`plan_contract.contractItems[${index}].verifyFileExists must be an array when provided`);
      } else {
        item.verifyFileExists.forEach((filePath, fileIndex) => {
          if (!isNonEmptyString(filePath)) {
            errors.push(`plan_contract.contractItems[${index}].verifyFileExists[${fileIndex}] must be a non-empty string`);
          }
        });
      }
    }
    if (item?.alternativeApproaches !== undefined) {
      if (!Array.isArray(item.alternativeApproaches)) {
        errors.push(`plan_contract.contractItems[${index}].alternativeApproaches must be an array when provided`);
      } else {
        item.alternativeApproaches.forEach((approach, approachIndex) => {
          if (!isNonEmptyString(approach)) {
            errors.push(`plan_contract.contractItems[${index}].alternativeApproaches[${approachIndex}] must be a non-empty string`);
          }
        });
      }
    }
    if (item?.dependsOn !== undefined) {
      if (!Array.isArray(item.dependsOn)) {
        errors.push(`plan_contract.contractItems[${index}].dependsOn must be an array when provided`);
      } else {
        const seenDeps = new Set<string>();
        item.dependsOn.forEach((dep, depIndex) => {
          if (!isNonEmptyString(dep)) {
            errors.push(`plan_contract.contractItems[${index}].dependsOn[${depIndex}] must be a non-empty string`);
            return;
          }
          if (dep === item.id) {
            errors.push(`plan_contract.contractItems[${index}].dependsOn must not reference itself ('${item.id}')`);
          }
          if (seenDeps.has(dep)) {
            errors.push(`plan_contract.contractItems[${index}].dependsOn has duplicate reference '${dep}'`);
          }
          seenDeps.add(dep);
        });
      }
    }
  });
  return errors;
}

export function validatePlanContract(doc: PlanContractDocument): string[] {
  const errors: string[] = [];
  if (doc.schemaVersion !== "harness.phase1.v1") errors.push("plan_contract.schemaVersion must be harness.phase1.v1");
  if (doc.kind !== "plan_contract") errors.push("plan_contract.kind must be plan_contract");
  if (!isNonEmptyString(doc.runId)) errors.push("plan_contract.runId is required");
  if (!isNonEmptyString(doc.taskDescription)) errors.push("plan_contract.taskDescription is required");
  if (!isValidIsoTimestamp(doc.createdAt)) errors.push("plan_contract.createdAt must be a valid ISO timestamp");
  if (doc.updatedAt !== undefined && !isValidIsoTimestamp(doc.updatedAt)) errors.push("plan_contract.updatedAt must be a valid ISO timestamp");
  if (!isNonEmptyString(doc.planPath)) errors.push("plan_contract.planPath is required");
  if (isNonEmptyString(doc.planPath) && !path.isAbsolute(doc.planPath)) errors.push("plan_contract.planPath must be an absolute path");
  if (doc.verifyCommand !== undefined && !isNonEmptyString(doc.verifyCommand)) errors.push("plan_contract.verifyCommand must be a non-empty string when provided");
  if (!Array.isArray(doc.dodItems)) errors.push("plan_contract.dodItems must be an array");
  else errors.push(...validateDodItemsSchema(doc.dodItems));
  if (!Array.isArray(doc.features)) errors.push("plan_contract.features must be an array");
  else errors.push(...validateFeaturesSchema(doc.features));
  if (!Array.isArray(doc.contractItems)) errors.push("plan_contract.contractItems must be an array");
  else errors.push(...validateContractItemsSchema(doc.contractItems));

  if (Array.isArray(doc.contractItems)) {
    const ids = new Set(doc.contractItems.map((item) => item.id));
    for (const item of doc.contractItems) {
      for (const dep of item.dependsOn ?? []) {
        if (!ids.has(dep)) {
          errors.push(`plan_contract.contractItems '${item.id}' depends on missing item '${dep}'`);
        }
      }
    }
    const cycle = detectDependencyCycle(doc.contractItems);
    if (cycle) {
      errors.push(`plan_contract.contractItems dependency cycle detected: ${cycle}`);
    }
  }

  const hasPlanSurface =
    (Array.isArray(doc.dodItems) && doc.dodItems.length > 0)
    || (Array.isArray(doc.features) && doc.features.length > 0);
  if (hasPlanSurface && Array.isArray(doc.contractItems) && doc.contractItems.length === 0) {
    errors.push("plan_contract.contractItems must not be empty when dodItems/features are present");
  }

  return errors;
}

export function buildChallengeContract(
  runId: string,
  reportPath: string,
  content: string,
): ChallengeContractDocument {
  const findings = content
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => /\b(critical|major)\b/i.test(line) && (line.startsWith("-") || line.startsWith("*")))
    .map((line, index) => ({
      id: `challenge-${String(index + 1).padStart(3, "0")}`,
      severity: /\bcritical\b/i.test(line) ? "critical" as const : "major" as const,
      status: /addressed|resolved|fixed|mitigated|dismissed|\[x\]/i.test(line) ? "resolved" as const : "open" as const,
      summary: line,
      reproductionCommand: (() => {
        const match = line.match(/(?:repro|cmd|command)\s*:\s*`?([^`]+)`?/i);
        return match?.[1]?.trim();
      })(),
      evidence: (() => {
        const match = line.match(/evidence\s*:\s*(.*)$/i);
        return match?.[1]?.trim();
      })(),
    }));

  const unresolvedCriticalCount = findings.filter((finding) => finding.severity === "critical" && finding.status === "open").length;
  const summary = firstMeaningfulParagraph(content);
  return {
    schemaVersion: "harness.phase1.v1",
    kind: "challenge_contract",
    runId,
    createdAt: new Date().toISOString(),
    reportPath,
    overall: unresolvedCriticalCount > 0 ? "FAIL" : "PASS",
    summary,
    confidence: parseConfidenceRating(content),
    findings,
    evidenceDemands: extractSectionBullets(content, ["demands for evidence", "evidence demands"]),
    weakestPoints: extractSectionBullets(content, ["weakest points"]),
    overconfidenceFlags: extractSectionBullets(content, ["overconfidence flags"]),
    unresolvedCriticalCount,
  };
}

export function validateChallengeContract(doc: ChallengeContractDocument): string[] {
  const errors: string[] = [];
  if (doc.schemaVersion !== "harness.phase1.v1") errors.push("challenge_contract.schemaVersion must be harness.phase1.v1");
  if (doc.kind !== "challenge_contract") errors.push("challenge_contract.kind must be challenge_contract");
  if (!isNonEmptyString(doc.runId)) errors.push("challenge_contract.runId is required");
  if (!isValidIsoTimestamp(doc.createdAt)) errors.push("challenge_contract.createdAt must be a valid ISO timestamp");
  if (!isNonEmptyString(doc.reportPath)) errors.push("challenge_contract.reportPath is required");
  if (isNonEmptyString(doc.reportPath) && !path.isAbsolute(doc.reportPath)) errors.push("challenge_contract.reportPath must be an absolute path");
  if (doc.overall !== "PASS" && doc.overall !== "FAIL") errors.push("challenge_contract.overall must be PASS or FAIL");
  if (doc.summary !== undefined && !isNonEmptyString(doc.summary)) errors.push("challenge_contract.summary must be a non-empty string when provided");
  if (doc.confidence !== undefined && (!Number.isFinite(doc.confidence) || doc.confidence < 1 || doc.confidence > 5)) {
    errors.push("challenge_contract.confidence must be between 1 and 5 when provided");
  }
  if (!Array.isArray(doc.findings)) {
    errors.push("challenge_contract.findings must be an array");
  } else {
    const ids = new Set<string>();
    doc.findings.forEach((finding, index) => {
      if (!isNonEmptyString(finding?.id)) {
        errors.push(`challenge_contract.findings[${index}].id must be a non-empty string`);
      } else if (ids.has(finding.id)) {
        errors.push(`challenge_contract.findings has duplicate id '${finding.id}'`);
      } else {
        ids.add(finding.id);
      }
      if (finding?.severity !== "critical" && finding?.severity !== "major") {
        errors.push(`challenge_contract.findings[${index}].severity must be 'critical' or 'major'`);
      }
      if (finding?.status !== "open" && finding?.status !== "resolved") {
        errors.push(`challenge_contract.findings[${index}].status must be open or resolved`);
      }
      if (!isNonEmptyString(finding?.summary)) {
        errors.push(`challenge_contract.findings[${index}].summary must be a non-empty string`);
      }
      if (finding?.evidence !== undefined && !isNonEmptyString(finding.evidence)) {
        errors.push(`challenge_contract.findings[${index}].evidence must be a non-empty string when provided`);
      }
      if (finding?.reproductionCommand !== undefined && !isNonEmptyString(finding.reproductionCommand)) {
        errors.push(`challenge_contract.findings[${index}].reproductionCommand must be a non-empty string when provided`);
      }
    });
    const openCriticals = doc.findings.filter((finding) => finding.severity === "critical" && finding.status === "open").length;
    if (typeof doc.unresolvedCriticalCount === "number" && doc.unresolvedCriticalCount !== openCriticals) {
      errors.push("challenge_contract.unresolvedCriticalCount must match number of open findings");
    }
    if (doc.overall === "PASS" && openCriticals > 0) {
      errors.push("challenge_contract.overall must be FAIL when open findings exist");
    }
    if (doc.overall === "FAIL" && openCriticals === 0) {
      errors.push("challenge_contract.overall must be PASS when no open findings exist");
    }
  }
  if (doc.evidenceDemands !== undefined) {
    if (!Array.isArray(doc.evidenceDemands)) {
      errors.push("challenge_contract.evidenceDemands must be an array when provided");
    } else {
      doc.evidenceDemands.forEach((item, index) => {
        if (!isNonEmptyString(item)) errors.push(`challenge_contract.evidenceDemands[${index}] must be a non-empty string`);
      });
    }
  }
  if (doc.weakestPoints !== undefined) {
    if (!Array.isArray(doc.weakestPoints)) {
      errors.push("challenge_contract.weakestPoints must be an array when provided");
    } else {
      doc.weakestPoints.forEach((item, index) => {
        if (!isNonEmptyString(item)) errors.push(`challenge_contract.weakestPoints[${index}] must be a non-empty string`);
      });
    }
  }
  if (doc.overconfidenceFlags !== undefined) {
    if (!Array.isArray(doc.overconfidenceFlags)) {
      errors.push("challenge_contract.overconfidenceFlags must be an array when provided");
    } else {
      doc.overconfidenceFlags.forEach((item, index) => {
        if (!isNonEmptyString(item)) errors.push(`challenge_contract.overconfidenceFlags[${index}] must be a non-empty string`);
      });
    }
  }
  if (typeof doc.unresolvedCriticalCount !== "number" || doc.unresolvedCriticalCount < 0) {
    errors.push("challenge_contract.unresolvedCriticalCount must be a non-negative number");
  }
  return errors;
}

/**
 * Extract structured features from a markdown plan.
 * Looks for checkbox items under ### headings, grouping by heading as category.
 * Each `- [ ] **Bold text**: description` or `- [ ] text` becomes a Feature.
 */
export function extractFeatures(content: string): Feature[] {
  const lines = content.split("\n");
  const features: Feature[] = [];
  let currentCategory = "General";
  let inCodeBlock = false;
  let featureIndex = 0;

  for (const line of lines) {
    if (/^\s*```/.test(line)) {
      inCodeBlock = !inCodeBlock;
      continue;
    }
    if (inCodeBlock) continue;

    const trimmed = line.trim();

    // Track heading as category
    const headingMatch = trimmed.match(/^#{2,4}\s+(.*)/);
    if (headingMatch) {
      currentCategory = headingMatch[1].replace(/[^\w\s\-()]/g, "").trim();
      continue;
    }

    // Match checkbox items
    const checkboxMatch = trimmed.match(/^[-*]\s+\[([\sxX])\]\s+(.*)/);
    if (checkboxMatch) {
      const checked = checkboxMatch[1].toLowerCase() === "x";
      let description = checkboxMatch[2];

      // Extract bold prefix as a sub-label: **Feature Name**: rest
      const boldMatch = description.match(/^\*\*([^*]+)\*\*[:\s]*(.*)/);
      if (boldMatch) {
        description = `${boldMatch[1]}: ${boldMatch[2]}`.trim();
        if (description.endsWith(":")) description = description.slice(0, -1);
      }

      featureIndex++;
      const id = `f${String(featureIndex).padStart(3, "0")}`;

      features.push({
        id,
        category: currentCategory,
        description,
        status: checked ? "passed" : "pending",
      });
    }
  }

  return features;
}

/**
 * Extract contract items from a markdown plan.
 * Supports two formats:
 *
 * Simple (from DoD checkboxes):
 *   - [ ] Description of what to do
 *
 * Rich (with acceptance criteria and verify commands):
 *   - [ ] **Feature Name**: Description
 *     - AC: Acceptance criterion 1
 *     - AC: Acceptance criterion 2
 *     - VERIFY: shell command to run
 *     - FILE: path/to/file/that/must/exist
 *     - DEPENDS: c001, c002
 *     - MAX_ATTEMPTS: 5
 *
 * If no rich syntax is found, DoD items become contract items with
 * auto-generated acceptance criteria.
 */
export function extractContractItems(content: string): ContractItem[] {
  const lines = content.split("\n");
  const items: ContractItem[] = [];
  let inCodeBlock = false;
  let itemIndex = 0;
  let currentItem: ContractItem | null = null;

  function pushCurrentItem() {
    if (currentItem) {
      // Auto-generate acceptance criteria if none specified
      if (currentItem.acceptanceCriteria.length === 0) {
        currentItem.acceptanceCriteria.push(`"${currentItem.description}" is implemented and working`);
      }
      items.push(currentItem);
    }
  }

  for (const line of lines) {
    if (/^\s*```/.test(line)) {
      inCodeBlock = !inCodeBlock;
      continue;
    }
    if (inCodeBlock) continue;

    const trimmed = line.trim();

    // Match top-level checkbox items (DoD items)
    const checkboxMatch = trimmed.match(/^[-*]\s+\[([\sxX])\]\s+(.*)/);
    if (checkboxMatch && !line.startsWith("    ") && !line.startsWith("\t\t")) {
      // Save previous item
      pushCurrentItem();

      const checked = checkboxMatch[1].toLowerCase() === "x";
      let description = checkboxMatch[2];

      // Extract bold prefix
      const boldMatch = description.match(/^\*\*([^*]+)\*\*[:\s]*(.*)/);
      if (boldMatch) {
        description = boldMatch[2] ? `${boldMatch[1]}: ${boldMatch[2]}`.trim() : boldMatch[1].trim();
        if (description.endsWith(":")) description = description.slice(0, -1);
      }

      itemIndex++;
      const id = `c${String(itemIndex).padStart(3, "0")}`;

      currentItem = {
        id,
        description,
        acceptanceCriteria: [],
        status: checked ? "passed" : "pending",
        attempts: 0,
        maxAttempts: 3,
      };
      continue;
    }

    // Match sub-items (indented) under the current contract item
    if (currentItem && /^\s{2,}[-*]\s/.test(line)) {
      const subContent = trimmed.replace(/^[-*]\s+/, "");

      // AC: Acceptance criterion
      const acMatch = subContent.match(/^AC:\s*(.*)/i);
      if (acMatch) {
        currentItem.acceptanceCriteria.push(acMatch[1]);
        continue;
      }

      // VERIFY: shell command
      const verifyMatch = subContent.match(/^VERIFY:\s*(.*)/i);
      if (verifyMatch) {
        currentItem.verifyCommand = verifyMatch[1];
        continue;
      }

      // FILE: required file path
      const fileMatch = subContent.match(/^FILE:\s*(.*)/i);
      if (fileMatch) {
        if (!currentItem.verifyFileExists) currentItem.verifyFileExists = [];
        currentItem.verifyFileExists.push(fileMatch[1].trim());
        continue;
      }

      // DEPENDS: comma-separated item IDs
      const depsMatch = subContent.match(/^DEPENDS:\s*(.*)/i);
      if (depsMatch) {
        currentItem.dependsOn = depsMatch[1].split(",").map(d => d.trim());
        continue;
      }

      // MAX_ATTEMPTS: number
      const maxMatch = subContent.match(/^MAX_ATTEMPTS:\s*(\d+)/i);
      if (maxMatch) {
        currentItem.maxAttempts = parseInt(maxMatch[1], 10);
        continue;
      }

      // Plain sub-item = acceptance criterion
      if (subContent.length > 0) {
        currentItem.acceptanceCriteria.push(subContent);
      }
    }
  }

  // Don't forget the last item
  pushCurrentItem();

  return items;
}
