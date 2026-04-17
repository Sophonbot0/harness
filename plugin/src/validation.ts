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
    return line;
  }
  return "No summary provided.";
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
  return {
    schemaVersion: "harness.phase1.v1",
    kind: "eval_contract",
    runId,
    createdAt: new Date().toISOString(),
    reportPath,
    overall,
    grade: overall,
    summary: firstMeaningfulParagraph(content),
  };
}

export function validateEvalContract(doc: EvalContractDocument): string[] {
  const errors: string[] = [];
  if (doc.schemaVersion !== "harness.phase1.v1") errors.push("eval_contract.schemaVersion must be harness.phase1.v1");
  if (doc.kind !== "eval_contract") errors.push("eval_contract.kind must be eval_contract");
  if (!doc.runId) errors.push("eval_contract.runId is required");
  if (!doc.reportPath) errors.push("eval_contract.reportPath is required");
  if (doc.overall !== "PASS" && doc.overall !== "FAIL") errors.push("eval_contract.overall must be PASS or FAIL");
  if (!doc.grade) errors.push("eval_contract.grade is required");
  if (!doc.summary) errors.push("eval_contract.summary is required");
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

export function validatePlanContract(doc: PlanContractDocument): string[] {
  const errors: string[] = [];
  if (doc.schemaVersion !== "harness.phase1.v1") errors.push("plan_contract.schemaVersion must be harness.phase1.v1");
  if (doc.kind !== "plan_contract") errors.push("plan_contract.kind must be plan_contract");
  if (!doc.runId) errors.push("plan_contract.runId is required");
  if (!doc.taskDescription) errors.push("plan_contract.taskDescription is required");
  if (!doc.planPath) errors.push("plan_contract.planPath is required");
  if (!Array.isArray(doc.dodItems)) errors.push("plan_contract.dodItems must be an array");
  if (!Array.isArray(doc.features)) errors.push("plan_contract.features must be an array");
  if (!Array.isArray(doc.contractItems) || doc.contractItems.length === 0) errors.push("plan_contract.contractItems must be a non-empty array");
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
    .filter((line) => /critical/i.test(line) && (line.startsWith("-") || line.startsWith("*")))
    .map((line, index) => ({
      id: `crit-${String(index + 1).padStart(3, "0")}`,
      severity: "critical" as const,
      status: /addressed|resolved|fixed|mitigated|\[x\]/i.test(line) ? "resolved" as const : "open" as const,
      summary: line,
    }));

  const unresolvedCriticalCount = findings.filter((finding) => finding.status === "open").length;
  return {
    schemaVersion: "harness.phase1.v1",
    kind: "challenge_contract",
    runId,
    createdAt: new Date().toISOString(),
    reportPath,
    overall: unresolvedCriticalCount > 0 ? "FAIL" : "PASS",
    findings,
    unresolvedCriticalCount,
  };
}

export function validateChallengeContract(doc: ChallengeContractDocument): string[] {
  const errors: string[] = [];
  if (doc.schemaVersion !== "harness.phase1.v1") errors.push("challenge_contract.schemaVersion must be harness.phase1.v1");
  if (doc.kind !== "challenge_contract") errors.push("challenge_contract.kind must be challenge_contract");
  if (!doc.runId) errors.push("challenge_contract.runId is required");
  if (!doc.reportPath) errors.push("challenge_contract.reportPath is required");
  if (doc.overall !== "PASS" && doc.overall !== "FAIL") errors.push("challenge_contract.overall must be PASS or FAIL");
  if (!Array.isArray(doc.findings)) errors.push("challenge_contract.findings must be an array");
  if (typeof doc.unresolvedCriticalCount !== "number") errors.push("challenge_contract.unresolvedCriticalCount must be a number");
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
