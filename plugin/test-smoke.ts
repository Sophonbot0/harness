// Smoke test for harness-enforcer plugin
// Run: npx tsx test-smoke.ts

import * as fs from "node:fs";
import * as path from "node:path";
import * as os from "node:os";
import { execFileSync } from "node:child_process";
import {
  createHarnessStartTool,
  createHarnessCheckpointTool,
  createHarnessSubmitTool,
  createHarnessStatusTool,
  createHarnessResetTool,
} from "./src/tools.js";
import { renderProgressBar, renderFinalStatus } from "./src/progress.js";
import * as validation from "./src/validation.js";
import * as state from "./src/state.js";

const testDir = path.join(os.tmpdir(), `harness-test-${Date.now()}`);
const runsDir = path.join(testDir, "runs");
const sessionCtx = { currentSessionKey: "test:session:smoke" as string | undefined };

// Create a fake plan.md in a valid ~/.openclaw path for sanitizePath to accept
const planDir = path.join(os.homedir(), ".openclaw", "harness-enforcer", "_test");
fs.mkdirSync(planDir, { recursive: true });
const planPath = path.join(planDir, "plan.md");
fs.writeFileSync(planPath, `# Plan: Test

## Feature 1: Test Feature
- **DoD:**
  - [ ] First criterion
  - [ ] Second criterion
  - [x] Already done criterion
`);

let passed = 0;
let failed = 0;

function assert(label: string, condition: boolean, detail?: string) {
  if (condition) {
    console.log(`  ✅ ${label}`);
    passed++;
  } else {
    console.log(`  ❌ ${label}${detail ? ` — ${detail}` : ""}`);
    failed++;
  }
}

async function main() {
  console.log("\n🔧 Harness Enforcer — Smoke Test\n");

  // --- Test 1: harness_start ---
  console.log("1. harness_start");
  const startTool = createHarnessStartTool(runsDir, sessionCtx);
  const startResult = await startTool.execute("test-1", {
    planPath,
    taskDescription: "Smoke test run",
  });
  const startData = (startResult as any).details;
  assert("Returns success", startData?.success === true);
  assert("Returns runId", typeof startData?.runId === "string" && startData.runId.length > 0);
  assert("Counts DoD items", startData?.dodItemCount === 3);
  assert("Counts unchecked DoD items", startData?.uncheckedDodItems === 2);

  const runId = startData?.runId;

  // Check state files exist on disk
  const runDir = path.join(runsDir, runId);
  assert("run-state.json exists", fs.existsSync(path.join(runDir, "run-state.json")));
  assert("dod-items.json exists", fs.existsSync(path.join(runDir, "dod-items.json")));
  assert("plan.contract.json exists", fs.existsSync(path.join(runDir, "plan.contract.json")));
  assert("run-summary.json exists", fs.existsSync(path.join(runDir, "run-summary.json")));

  // --- Test 2: harness_start rejects duplicate ---
  console.log("\n2. harness_start (duplicate rejection)");
  const dupResult = await startTool.execute("test-2", {
    planPath,
    taskDescription: "Should be rejected",
  });
  const dupData = (dupResult as any).details;
  assert("Rejects duplicate run", dupData?.error?.includes("already active"));

  // --- Test 3: harness_checkpoint ---
  console.log("\n3. harness_checkpoint");
  const cpTool = createHarnessCheckpointTool(runsDir, sessionCtx);
  const cpResult = await cpTool.execute("test-3", {
    phase: "build",
    completedFeatures: ["Feature A"],
    pendingFeatures: ["Feature B"],
    blockers: [],
    summary: "First checkpoint — Feature A done",
  });
  const cpData = (cpResult as any).details;
  assert("Returns success", cpData?.success === true);
  assert("Checkpoint number is 1", cpData?.checkpointNumber === 1);
  assert("Phase is build", cpData?.phase === "build");
  assert("checkpoints.jsonl exists", fs.existsSync(path.join(runDir, "checkpoints.jsonl")));

  // --- Test 4: harness_status ---
  console.log("\n4. harness_status");
  const statusTool = createHarnessStatusTool(runsDir, sessionCtx);
  const statusResult = await statusTool.execute("test-4", {});
  const statusData = (statusResult as any).details;
  assert("Shows active run", statusData?.status === "active");
  assert("Shows correct runId", statusData?.runId === runId);
  assert("Shows checkpoint count", statusData?.checkpointCount === 1);
  assert("Shows latest checkpoint", statusData?.latestCheckpoint?.phase === "build");

  // --- Test 5: harness_submit (should FAIL — no eval report) ---
  console.log("\n5. harness_submit (rejection test)");
  const submitTool = createHarnessSubmitTool(runsDir, sessionCtx);
  const submitResult = await submitTool.execute("test-5", {
    evalReportPath: path.join(planDir, "nonexistent-eval.md"),
  });
  const submitData = (submitResult as any).details;
  assert("Rejects without eval report", submitData?.delivered === false);
  assert("Lists errors", Array.isArray(submitData?.errors) && submitData.errors.length > 0);
  const failureSummary = state.readRunSummary(runsDir, runId);
  assert("Failure summary written", failureSummary?.finalOutcome === "iteration_required_eval_report_missing");
  assert("Failure summary primary code is fine-grained", failureSummary?.failureCode === "eval_report_missing");
  assert("Failure summary stores failure code list", failureSummary?.failureCodes?.includes("eval_report_missing") === true);
  assert("Failure summary classifies environment failure", failureSummary?.failureDomain === "environment");
  assert("Failure summary has artifact completeness", typeof failureSummary?.artifactCompleteness?.score === "number");

  // --- Test 6: harness_submit (should PASS with valid eval) ---
  console.log("\n6. harness_submit (success test)");
  // Mark all contract items complete so submit can pass
  await cpTool.execute("test-6a", {
    phase: "eval",
    completedFeatures: ["First criterion", "Second criterion", "Already done criterion"],
    pendingFeatures: [],
    blockers: [],
    summary: "All contract items complete and ready for final submit",
  });

  // Corrupt markdown DoD on purpose — submit should rely on structured plan contract, not markdown checkboxes
  fs.writeFileSync(planPath, `# Plan: Test\n\n## Feature 1: Test Feature\n- **DoD:**\n  - [ ] First criterion\n  - [ ] Second criterion\n  - [ ] Already done criterion\n`);
  const syncedPlanContract = state.readPlanContract(runsDir, runId);
  assert("Plan contract keeps contract items after checkpoint", Array.isArray(syncedPlanContract?.contractItems) && syncedPlanContract!.contractItems.length >= 3);
  assert("Plan contract reflects passed contract state", syncedPlanContract?.contractItems.every((item) => item.status === "passed") === true);

  // Create passing eval + challenge reports
  const evalPath = path.join(planDir, "eval-report.md");
  fs.writeFileSync(evalPath, `# Evaluation Report

## Overall: PASS

All criteria verified.
`);
  const challengePath = path.join(planDir, "challenge-report.md");
  fs.writeFileSync(challengePath, `# Challenge Report

- CRITICAL: Login flow brute force risk — mitigated with rate limiting and lockout.
`);
  const passResult = await submitTool.execute("test-6", {
    evalReportPath: evalPath,
    challengeReportPath: challengePath,
  });
  const passData = (passResult as any).details;
  assert("Delivers successfully", passData?.delivered === true);
  assert("Shows PASS grade", passData?.evalGrade === "PASS");
  assert("delivery.json exists", fs.existsSync(path.join(runDir, "delivery.json")));
  assert("eval.contract.json exists", fs.existsSync(path.join(runDir, "eval.contract.json")));
  assert("challenge.contract.json exists", fs.existsSync(path.join(runDir, "challenge.contract.json")));
  const successSummary = state.readRunSummary(runsDir, runId);
  assert("Success summary written", successSummary?.finalOutcome === "delivered");
  assert("Success summary is native-instrumented", successSummary?.instrumentationKind === "native");
  assert("Success summary has high data quality", successSummary?.dataQuality?.grade === "high");
  assert("Success summary has no failure domain", successSummary?.failureDomain === "none");
  assert("Success summary keeps historical failure codes", successSummary?.historicalFailureCodes?.includes("eval_report_missing") === true);
  assert("Success summary artifacts are complete", successSummary?.artifactCompleteness?.complete === true);
  assert("Success summary exposes plan contract path", successSummary?.artifacts?.planContractPath?.endsWith("plan.contract.json") === true);
  assert("Success summary exposes eval contract path", successSummary?.artifacts?.evalContractPath?.endsWith("eval.contract.json") === true);
  assert("Success summary exposes challenge contract path", successSummary?.artifacts?.challengeContractPath?.endsWith("challenge.contract.json") === true);

  const planContractDoc = state.readPlanContract(runsDir, runId);
  fs.unlinkSync(path.join(runDir, "contract.json"));
  fs.unlinkSync(path.join(runDir, "features.json"));
  fs.unlinkSync(path.join(runDir, "dod-items.json"));
  state.writePlanContract(runsDir, runId, planContractDoc!);
  assert("Plan contract rematerializes contract.json", fs.existsSync(path.join(runDir, "contract.json")));
  assert("Plan contract rematerializes features.json", fs.existsSync(path.join(runDir, "features.json")));
  assert("Plan contract rematerializes dod-items.json", fs.existsSync(path.join(runDir, "dod-items.json")));

  // --- Test 7: harness_reset (no active run) ---
  console.log("\n7. harness_reset (no active run)");
  const resetTool = createHarnessResetTool(runsDir, sessionCtx);
  const resetNoRun = await resetTool.execute("test-7a", {});
  const resetNoRunData = (resetNoRun as any).details;
  assert("Returns message when no active run", resetNoRunData?.message?.includes("No active"));

  // --- Test 8: harness_reset (cancel active run) ---
  console.log("\n8. harness_reset (cancel active run)");
  // Start a new run first
  fs.writeFileSync(planPath, `# Plan: Reset Test\n\n- [ ] Item A\n- [ ] Item B\n`);
  const startForReset = await startTool.execute("test-8a", {
    planPath,
    taskDescription: "Run to be reset",
  });
  const resetRunId = (startForReset as any).details?.runId;
  assert("New run started for reset test", typeof resetRunId === "string");

  const resetResult = await resetTool.execute("test-8b", { reason: "Testing reset" });
  const resetData = (resetResult as any).details;
  assert("Reset returns success", resetData?.success === true);
  assert("Reset returns correct runId", resetData?.runId === resetRunId);
  assert("Reset returns reason", resetData?.reason === "Testing reset");
  assert("Reset returns cancelledAt", typeof resetData?.cancelledAt === "string");

  // --- Test 9: harness_start works after reset ---
  console.log("\n9. harness_start after reset");
  const startAfterReset = await startTool.execute("test-9", {
    planPath,
    taskDescription: "Fresh start after reset",
  });
  const afterResetData = (startAfterReset as any).details;
  assert("Start succeeds after reset", afterResetData?.success === true);
  assert("New runId is different", afterResetData?.runId !== resetRunId);

  // --- Test 10: harness_status shows cancelled run ---
  console.log("\n10. harness_status shows cancelled run");
  // First cancel this new run too so we can check status
  await resetTool.execute("test-10a", {});
  const statusAfterReset = await statusTool.execute("test-10b", { runId: resetRunId });
  const statusResetData = (statusAfterReset as any).details;
  assert("Cancelled run shows status=cancelled", statusResetData?.status === "cancelled");

  // --- Test 10b: harness_submit (structured-first contracts) ---
  console.log("\n10b. harness_submit (structured-first contracts)");
  fs.writeFileSync(planPath, `# Plan: Structured Submit Test\n\n## Feature 1: Structured\n- **DoD:**\n  - [ ] Structured criterion A\n  - [ ] Structured criterion B\n`);
  const startStructured = await startTool.execute("test-10c", {
    planPath,
    taskDescription: "Structured contract submission",
  });
  const structuredRunId = (startStructured as any).details?.runId;
  const structuredRunDir = path.join(runsDir, structuredRunId);
  assert("Structured run started", typeof structuredRunId === "string");
  await cpTool.execute("test-10d", {
    phase: "eval",
    completedFeatures: ["Structured criterion A", "Structured criterion B"],
    pendingFeatures: [],
    blockers: [],
    summary: "Structured contract items complete",
  });

  const structuredEvalReportPath = path.join(planDir, "structured-eval-report.md");
  const structuredChallengeReportPath = path.join(planDir, "structured-challenge-report.md");
  const structuredEvalContractPath = path.join(planDir, "structured-eval.contract.json");
  const structuredChallengeContractPath = path.join(planDir, "structured-challenge.contract.json");
  fs.writeFileSync(structuredEvalReportPath, "# Eval Report Companion\n");
  fs.writeFileSync(structuredChallengeReportPath, "# Challenge Report Companion\n");
  fs.writeFileSync(structuredChallengeContractPath, JSON.stringify({
    schemaVersion: "harness.phase1.v1",
    kind: "challenge_contract",
    runId: structuredRunId,
    createdAt: new Date().toISOString(),
    reportPath: structuredChallengeReportPath,
    overall: "PASS",
    summary: "All critical challenges resolved.",
    confidence: 4,
    findings: [
      {
        id: "challenge-001",
        severity: "critical",
        status: "resolved",
        summary: "Resolved auth edge case",
        evidence: "Added integration coverage",
        reproductionCommand: "npm test -- auth",
      },
    ],
    evidenceDemands: ["Run auth integration tests"],
    weakestPoints: ["Session expiry handling"],
    overconfidenceFlags: ["Generator claimed done before integration evidence"],
    unresolvedCriticalCount: 0,
  }, null, 2));
  fs.writeFileSync(structuredEvalContractPath, JSON.stringify({
    schemaVersion: "harness.phase1.v1",
    kind: "eval_contract",
    runId: structuredRunId,
    createdAt: new Date().toISOString(),
    reportPath: structuredEvalReportPath,
    overall: "PASS",
    grade: "PASS",
    summary: "Structured evaluator verdict with explicit evidence.",
    confidence: 5,
    rationale: "All contract items and challenges were checked with evidence.",
    dodVerdicts: [
      {
        itemId: "c001",
        description: "Structured criterion A",
        verdict: "PASS",
        evidence: "Verified via test run",
      },
      {
        itemId: "c002",
        description: "Structured criterion B",
        verdict: "PASS",
        evidence: "Verified via file and behavior check",
      },
    ],
    challengeVerdicts: [
      {
        challengeId: "challenge-001",
        disposition: "DISMISSED",
        evidence: "The reported issue is covered by auth integration tests.",
      },
    ],
    unresolvedCriticalChallengeIds: [],
  }, null, 2));

  const structuredSubmit = await submitTool.execute("test-10e", {
    evalContractPath: structuredEvalContractPath,
    challengeContractPath: structuredChallengeContractPath,
  });
  const structuredSubmitData = (structuredSubmit as any).details;
  assert("Structured-first submit delivers", structuredSubmitData?.delivered === true);
  assert("Structured-first submit returns PASS", structuredSubmitData?.evalGrade === "PASS");
  assert("Structured eval contract written to canonical run path", fs.existsSync(path.join(structuredRunDir, "eval.contract.json")));
  assert("Structured challenge contract written to canonical run path", fs.existsSync(path.join(structuredRunDir, "challenge.contract.json")));
  const structuredSummary = state.readRunSummary(runsDir, structuredRunId);
  assert("Structured summary records eval contract path", structuredSummary?.artifacts?.evalContractPath?.endsWith("eval.contract.json") === true);
  assert("Structured summary records challenge contract path", structuredSummary?.artifacts?.challengeContractPath?.endsWith("challenge.contract.json") === true);
  assert("Structured summary can deliver without markdown report artifact", structuredSummary?.artifactCompleteness?.complete === true);

  // --- Test 11: Validation edge cases ---
  console.log("\n11. Validation edge cases");
  // Path traversal
  try {
    const badStart = await startTool.execute("test-7a", {
      planPath: "/Users/testuser/.openclaw/../../../etc/passwd",
      taskDescription: "Should be rejected",
    });
    const badData = (badStart as any).details;
    assert("Rejects path traversal", badData?.error?.includes(".."));
  } catch {
    assert("Rejects path traversal (thrown)", true);
  }

  // Missing params
  try {
    const badStart2 = await startTool.execute("test-7b", {
      taskDescription: "Missing planPath",
    });
    const badData2 = (badStart2 as any).details;
    assert("Rejects missing planPath", badData2?.error !== undefined);
  } catch {
    assert("Rejects missing planPath (thrown)", true);
  }

  // --- Test 11b: baseline aggregation script ---
  console.log("\n11b. baseline aggregation script");
  {
    const legacyPlanPath = path.join(planDir, "legacy-plan.md");
    fs.writeFileSync(legacyPlanPath, "# Legacy Plan\n\n- [x] Legacy item\n");

    const legacyRunId = "legacy-delivered-run";
    const legacyRunDir = path.join(runsDir, legacyRunId);
    fs.mkdirSync(legacyRunDir, { recursive: true });
    fs.writeFileSync(path.join(legacyRunDir, "run-state.json"), JSON.stringify({
      runId: legacyRunId,
      planPath: legacyPlanPath,
      taskDescription: "Legacy delivered run",
      startedAt: new Date(Date.now() - 60 * 60 * 1000).toISOString(),
      phase: "eval",
      round: 1,
      checkpoints: [],
      status: "delivered",
    }, null, 2));
    fs.writeFileSync(path.join(legacyRunDir, "dod-items.json"), JSON.stringify([{ text: "Legacy item", checked: true }], null, 2));

    const staleRunId = "stale-active-run";
    const staleRunDir = path.join(runsDir, staleRunId);
    fs.mkdirSync(staleRunDir, { recursive: true });
    fs.writeFileSync(path.join(staleRunDir, "run-state.json"), JSON.stringify({
      runId: staleRunId,
      planPath,
      taskDescription: "Stale active run",
      startedAt: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString(),
      phase: "build",
      round: 1,
      checkpoints: [],
      status: "active",
      isSubagent: false,
    }, null, 2));
    fs.writeFileSync(path.join(staleRunDir, "contract.json"), JSON.stringify([], null, 2));

    const missingPlanRunId = "missing-plan-run";
    const missingPlanRunDir = path.join(runsDir, missingPlanRunId);
    fs.mkdirSync(missingPlanRunDir, { recursive: true });
    fs.writeFileSync(path.join(missingPlanRunDir, "run-state.json"), JSON.stringify({
      runId: missingPlanRunId,
      planPath: path.join(planDir, "deleted-plan.md"),
      taskDescription: "Missing plan run",
      startedAt: new Date(Date.now() - 90 * 60 * 1000).toISOString(),
      phase: "plan",
      round: 1,
      checkpoints: [],
      status: "cancelled",
    }, null, 2));
    fs.writeFileSync(path.join(missingPlanRunDir, "contract.md"), "# Contract\n\n- [ ] Recovered from contract\n");

    const missingCheckpointRunId = "missing-checkpoints-run";
    const missingCheckpointRunDir = path.join(runsDir, missingCheckpointRunId);
    fs.mkdirSync(missingCheckpointRunDir, { recursive: true });
    fs.writeFileSync(path.join(missingCheckpointRunDir, "run-state.json"), JSON.stringify({
      runId: missingCheckpointRunId,
      planPath,
      taskDescription: "Missing checkpoints run",
      startedAt: new Date(Date.now() - 45 * 60 * 1000).toISOString(),
      phase: "eval",
      round: 2,
      checkpoints: [],
      status: "completed",
      evalGrade: "PASS",
    }, null, 2));
    fs.writeFileSync(path.join(missingCheckpointRunDir, "contract.json"), JSON.stringify([{ id: "c001", description: "Done", status: "passed" }], null, 2));
    fs.writeFileSync(path.join(missingCheckpointRunDir, "features.json"), JSON.stringify([{ id: "f001", description: "Done", status: "passed" }], null, 2));

    const raw = execFileSync(process.execPath, [
      path.join(process.cwd(), "scripts", "aggregate-run-summaries.mjs"),
      "--runsDir",
      runsDir,
      "--json",
    ], { encoding: "utf8" });
    const report = JSON.parse(raw);
    assert("Aggregation includes total runs", typeof report.totalRuns === "number" && report.totalRuns >= 4);
    assert("Aggregation counts delivered runs", report.deliveredRuns >= 1);
    assert("Aggregation counts eval_report_missing", report.failureCodeCounts?.eval_report_missing >= 1);
    assert("Aggregation exposes env vs harness split", typeof report.environmentVsHarnessSplit?.environment === "number");
    assert("Aggregation exposes false-pass suspects", Array.isArray(report.falsePassSuspects));
    assert("Aggregation tracks native vs backfilled", report.instrumentationCounts?.backfilled >= 2);
    assert("Aggregation tracks stale active runs", report.staleActive?.count >= 1);
    assert("Aggregation tracks legacy normalization", report.legacyDataQuality?.normalizedStatuses?.delivered_to_completed >= 1);
    assert("Aggregation reports artifact debt", typeof report.artifactDebt?.required?.contract === "number");
    assert("Aggregation reports data quality counts", typeof report.dataQualityCounts?.low === "number");
    assert("Backfill writes legacy run-summary", fs.existsSync(path.join(legacyRunDir, "run-summary.json")));
    assert("Backfill writes stale run-summary", fs.existsSync(path.join(staleRunDir, "run-summary.json")));

    const repairRaw = execFileSync(process.execPath, [
      path.join(process.cwd(), "scripts", "remediate-artifact-debt.mjs"),
      "--runsDir",
      runsDir,
      "--apply",
      "--json",
    ], { encoding: "utf8" });
    const repairReport = JSON.parse(repairRaw);
    assert("Repair script repairs at least one plan", repairReport.plansRepaired >= 1);
    assert("Repair script repairs at least one contract", repairReport.contractsRepaired >= 1);
    assert("Repair script repairs at least one checkpoint file", repairReport.checkpointsRepaired >= 1);
    assert("Repair script repairs at least one delivery", repairReport.deliveriesRepaired >= 1);
    assert("Repair script closes stale runs", repairReport.staleRunsClosed >= 1);
    assert("Repair script writes plan snapshot", fs.existsSync(path.join(missingPlanRunDir, "plan.md")));
    assert("Repair script rewires run-state planPath", JSON.parse(fs.readFileSync(path.join(missingPlanRunDir, "run-state.json"), "utf8")).planPath === path.join(missingPlanRunDir, "plan.md"));
    assert("Repair script writes contract.json", fs.existsSync(path.join(legacyRunDir, "contract.json")));
    assert("Repair script writes synthetic checkpoints", fs.existsSync(path.join(missingCheckpointRunDir, "checkpoints.jsonl")));
    assert("Repair script writes delivery.json", fs.existsSync(path.join(legacyRunDir, "delivery.json")));
    assert("Repair script marks stale run failed", JSON.parse(fs.readFileSync(path.join(staleRunDir, "run-state.json"), "utf8")).status === "failed");
  }

  // --- Test 11c: structured contract validation invariants ---
  console.log("\n11c. structured contract validation invariants");
  {
    const validPlan = validation.buildPlanContract(
      "run-validate",
      "Validation test",
      path.join(planDir, "validation-plan.md"),
      [{ text: "First criterion", checked: false }],
      [{ id: "f001", category: "Core", description: "First criterion", status: "pending" }],
      [{ id: "c001", description: "First criterion", acceptanceCriteria: ["Works end-to-end"], status: "pending", attempts: 0, maxAttempts: 3 }],
      "npm test",
    );
    assert("Valid plan contract passes validator", validation.validatePlanContract(validPlan).length === 0);

    const missingDepPlan: state.PlanContractDocument = {
      ...validPlan,
      contractItems: [
        { id: "c001", description: "First criterion", acceptanceCriteria: ["Works end-to-end"], status: "pending", attempts: 0, maxAttempts: 3, dependsOn: ["c999"] },
      ],
    };
    const missingDepErrors = validation.validatePlanContract(missingDepPlan);
    assert("Plan validator catches missing dependency refs", missingDepErrors.some((err) => err.includes("depends on missing item 'c999'")));

    const cyclicPlan: state.PlanContractDocument = {
      ...validPlan,
      contractItems: [
        { id: "c001", description: "Item 1", acceptanceCriteria: ["A"], status: "pending", attempts: 0, maxAttempts: 3, dependsOn: ["c002"] },
        { id: "c002", description: "Item 2", acceptanceCriteria: ["B"], status: "pending", attempts: 0, maxAttempts: 3, dependsOn: ["c001"] },
      ],
    };
    const cyclicErrors = validation.validatePlanContract(cyclicPlan);
    assert("Plan validator catches dependency cycles", cyclicErrors.some((err) => err.includes("dependency cycle detected")));

    const skippedWithoutReason: state.PlanContractDocument = {
      ...validPlan,
      contractItems: [
        { id: "c001", description: "Skipped item", acceptanceCriteria: ["A"], status: "skipped", attempts: 0, maxAttempts: 3 },
      ],
    };
    const skippedErrors = validation.validatePlanContract(skippedWithoutReason);
    assert("Plan validator requires skipReason for skipped items", skippedErrors.some((err) => err.includes("skipReason is required")));

    const surfaceWithoutContract: state.PlanContractDocument = {
      ...validPlan,
      contractItems: [],
    };
    const surfaceErrors = validation.validatePlanContract(surfaceWithoutContract);
    assert("Plan validator rejects empty contractItems when plan surface exists", surfaceErrors.some((err) => err.includes("must not be empty when dodItems/features are present")));

    const badEval: state.EvalContractDocument = {
      schemaVersion: "harness.phase1.v1",
      kind: "eval_contract",
      runId: "run-eval",
      createdAt: "not-a-date",
      reportPath: "relative/eval.md",
      overall: "PASS",
      grade: "FAIL",
      summary: "Summary",
    };
    const evalErrors = validation.validateEvalContract(badEval);
    assert("Eval validator catches invalid createdAt", evalErrors.some((err) => err.includes("createdAt must be a valid ISO timestamp")));
    assert("Eval validator catches relative reportPath", evalErrors.some((err) => err.includes("reportPath must be an absolute path")));
    assert("Eval validator catches grade/overall mismatch", evalErrors.some((err) => err.includes("grade must match overall")));

    const badChallenge: state.ChallengeContractDocument = {
      schemaVersion: "harness.phase1.v1",
      kind: "challenge_contract",
      runId: "run-challenge",
      createdAt: new Date().toISOString(),
      reportPath: path.join(planDir, "challenge-report.md"),
      overall: "PASS",
      findings: [
        { id: "crit-001", severity: "critical", status: "open", summary: "Open critical issue" },
      ],
      unresolvedCriticalCount: 0,
    };
    const challengeErrors = validation.validateChallengeContract(badChallenge);
    assert("Challenge validator catches unresolved count mismatch", challengeErrors.some((err) => err.includes("must match number of open findings")));
    assert("Challenge validator catches PASS with open findings", challengeErrors.some((err) => err.includes("must be FAIL when open findings exist")));

    const richBadEval: state.EvalContractDocument = {
      schemaVersion: "harness.phase1.v1",
      kind: "eval_contract",
      runId: "run-eval-rich",
      createdAt: new Date().toISOString(),
      reportPath: path.join(planDir, "eval-report.md"),
      overall: "PASS",
      grade: "PASS",
      summary: "Summary",
      confidence: 7,
      dodVerdicts: [
        { itemId: "c001", description: "Criterion", verdict: "FAIL", evidence: "Broken" },
      ],
      challengeVerdicts: [
        { challengeId: "challenge-001", disposition: "CONFIRMED", evidence: "Evidence A" },
        { challengeId: "challenge-001", disposition: "DISMISSED", evidence: "Evidence B" },
      ],
      unresolvedCriticalChallengeIds: ["challenge-001"],
    };
    const richEvalErrors = validation.validateEvalContract(richBadEval);
    assert("Eval validator catches confidence out of range", richEvalErrors.some((err) => err.includes("confidence must be between 1 and 5")));
    assert("Eval validator catches PASS with FAIL DoD verdict", richEvalErrors.some((err) => err.includes("overall must be FAIL when any core DoD verdict is FAIL")));
    assert("Eval validator catches duplicate challenge verdict ids", richEvalErrors.some((err) => err.includes("duplicate challengeId")));
    assert("Eval validator catches PASS with unresolved critical ids", richEvalErrors.some((err) => err.includes("overall must be FAIL when unresolvedCriticalChallengeIds are present")));

    const richBadChallenge: state.ChallengeContractDocument = {
      schemaVersion: "harness.phase1.v1",
      kind: "challenge_contract",
      runId: "run-challenge-rich",
      createdAt: new Date().toISOString(),
      reportPath: path.join(planDir, "challenge-report.md"),
      overall: "PASS",
      summary: "Summary",
      confidence: 9,
      findings: [
        { id: "challenge-001", severity: "major", status: "resolved", summary: "Major issue" },
        { id: "challenge-002", severity: "critical", status: "open", summary: "Open critical", reproductionCommand: "" },
      ],
      evidenceDemands: ["", "Run e2e"],
      weakestPoints: [""],
      overconfidenceFlags: [""],
      unresolvedCriticalCount: 0,
    };
    const richChallengeErrors = validation.validateChallengeContract(richBadChallenge);
    assert("Challenge validator catches confidence out of range", richChallengeErrors.some((err) => err.includes("confidence must be between 1 and 5")));
    assert("Challenge validator catches empty reproduction command", richChallengeErrors.some((err) => err.includes("reproductionCommand must be a non-empty string")));
    assert("Challenge validator catches empty evidence demand", richChallengeErrors.some((err) => err.includes("evidenceDemands[0] must be a non-empty string")));
    assert("Challenge validator catches empty weakest point", richChallengeErrors.some((err) => err.includes("weakestPoints[0] must be a non-empty string")));
    assert("Challenge validator catches empty overconfidence flag", richChallengeErrors.some((err) => err.includes("overconfidenceFlags[0] must be a non-empty string")));
  }

  // ─── Progress Bar Tests ───

  // --- Test 12: renderProgressBar — 0% progress ---
  console.log("\n12. renderProgressBar — 0% progress");
  {
    const output = renderProgressBar({
      taskDescription: "Implement progress bar",
      phase: "plan",
      completedFeatures: [],
      pendingFeatures: ["Feature A", "Feature B", "Feature C"],
      blockers: [],
      dodTotal: 10,
      dodCompleted: 0,
      elapsedSeconds: 0,
    });
    assert("Contains task description", output.includes("Implement progress bar"));
    assert("Contains 0%", output.includes("0%"));
    assert("Contains empty bar (all ▱)", output.includes("▱".repeat(BAR_WIDTH)));
    assert("No filled blocks", !output.includes("▰"));
    assert("Phase plan is current (▶)", output.includes("▶plan"));
    assert("Phase build is pending (○)", output.includes("○build"));
    assert("Shows 0/10 done", output.includes("0/10 done"));
    assert("Shows 0s elapsed", output.includes("⏱0s"));
    assert("Pending features shown", output.includes("⬜ Feature A"));
    assert("Under 4096 chars", output.length <= 4096);
  }

  // --- Test 13: renderProgressBar — 50% progress ---
  console.log("\n13. renderProgressBar — 50% progress");
  {
    const output = renderProgressBar({
      taskDescription: "Build API endpoint",
      phase: "build",
      completedFeatures: ["Schema types", "API endpoint"],
      pendingFeatures: ["Integration tests", "Documentation"],
      inProgressFeature: "Integration tests",
      blockers: [],
      dodTotal: 10,
      dodCompleted: 5,
      elapsedSeconds: 222,
    });
    assert("Contains 50%", output.includes("50%"));
    assert("Contains filled blocks (▰)", output.includes("▰"));
    assert("Phase plan completed (●)", output.includes("●plan"));
    assert("Phase build is current (▶)", output.includes("▶build"));
    assert("Phase challenge pending (○)", output.includes("○challenge"));
    assert("Completed features marked", output.includes("✅ Schema types"));
    assert("In-progress feature marked", output.includes("⏳ Integration tests"));
    assert("Pending feature marked", output.includes("⬜ Documentation"));
    assert("Elapsed formatted", output.includes("3m 42s"));
    assert("Shows 5/10 done", output.includes("5/10 done"));
    assert("In-progress not duplicated as pending",
      output.split("Integration tests").length - 1 === 1);
  }

  // --- Test 14: renderProgressBar — 100% progress ---
  console.log("\n14. renderProgressBar — 100% progress");
  {
    const output = renderProgressBar({
      taskDescription: "Complete task",
      phase: "eval",
      completedFeatures: ["Feature A", "Feature B"],
      pendingFeatures: [],
      blockers: [],
      dodTotal: 6,
      dodCompleted: 6,
      elapsedSeconds: 3661,
    });
    assert("Contains 100%", output.includes("100%"));
    assert("Full bar (all ▰)", output.includes("▰".repeat(BAR_WIDTH)));
    assert("No empty blocks", !output.includes("▱"));
    assert("Eval phase current (▶)", output.includes("▶eval"));
    assert("Shows 6/6 done", output.includes("6/6 done"));
    assert("Hours in elapsed", output.includes("1h 1m 1s"));
    assert("Blockers: 0", output.includes("0 blockers"));
  }

  // --- Test 15: renderProgressBar — with blockers ---
  console.log("\n15. renderProgressBar — with blockers");
  {
    const output = renderProgressBar({
      taskDescription: "Task with blockers",
      phase: "challenge",
      completedFeatures: ["Done thing"],
      pendingFeatures: ["Blocked thing"],
      blockers: ["Database connection failing", "Missing API key"],
      dodTotal: 4,
      dodCompleted: 2,
      elapsedSeconds: 600,
    });
    assert("Shows blocker count", output.includes("2 blockers"));
    assert("Shows blocker emoji", output.includes("🚫"));
    assert("Shows first blocker", output.includes("Database connection failing"));
    assert("Shows second blocker", output.includes("Missing API key"));
    assert("Shows warning section", output.includes("⚠️ Blockers:"));
  }

  // --- Test 16: renderProgressBar — empty features ---
  console.log("\n16. renderProgressBar — empty features");
  {
    const output = renderProgressBar({
      taskDescription: "No features yet",
      phase: "plan",
      completedFeatures: [],
      pendingFeatures: [],
      blockers: [],
      dodTotal: 0,
      dodCompleted: 0,
      elapsedSeconds: 5,
    });
    assert("Contains 0%", output.includes("0%"));
    assert("Shows 0/0 done", output.includes("0/0 done"));
    assert("Under 4096 chars", output.length <= 4096);
  }

  // --- Test 17: renderProgressBar — very long feature names ---
  console.log("\n17. renderProgressBar — very long feature names (truncation)");
  {
    const longName = "A".repeat(100);
    const output = renderProgressBar({
      taskDescription: "T".repeat(200),
      phase: "build",
      completedFeatures: [longName],
      pendingFeatures: [longName, longName],
      blockers: [longName],
      dodTotal: 3,
      dodCompleted: 1,
      elapsedSeconds: 10,
    });
    assert("Task description truncated", !output.includes("T".repeat(100)));
    assert("Contains truncation char", output.includes("…"));
    assert("Under 4096 chars", output.length <= 4096);
  }

  // --- Test 18: renderProgressBar — 10 features (Telegram limit) ---
  console.log("\n18. renderProgressBar — 10 features (Telegram limit)");
  {
    const features = Array.from({ length: 10 }, (_, i) => `Feature ${i + 1}: Something descriptive here`);
    const output = renderProgressBar({
      taskDescription: "Large feature set",
      phase: "build",
      completedFeatures: features.slice(0, 5),
      pendingFeatures: features.slice(5),
      blockers: ["Blocker 1", "Blocker 2", "Blocker 3"],
      dodTotal: 30,
      dodCompleted: 15,
      elapsedSeconds: 1800,
    });
    assert("Under 4096 chars with 10 features", output.length <= 4096);
    assert("All completed features present", features.slice(0, 5).every(f => output.includes(f)));
    assert("All pending features present", features.slice(5).every(f => output.includes(f)));
  }

  // --- Test 19: renderProgressBar — unknown phase ---
  console.log("\n19. renderProgressBar — unknown phase");
  {
    const output = renderProgressBar({
      taskDescription: "Custom phase",
      phase: "deploy",
      completedFeatures: ["A"],
      pendingFeatures: ["B"],
      blockers: [],
      dodTotal: 2,
      dodCompleted: 1,
      elapsedSeconds: 30,
    });
    assert("All phases shown as pending for unknown phase (○)",
      output.includes("○plan") && output.includes("○build"));
    assert("Still renders valid output", output.includes("50%"));
  }

  // --- Test 20: renderFinalStatus — pass ---
  console.log("\n20. renderFinalStatus — pass");
  {
    const output = renderFinalStatus({
      taskDescription: "Completed task",
      status: "pass",
      evalGrade: "PASS",
      dodTotal: 8,
      dodCompleted: 8,
      elapsedSeconds: 900,
      completedFeatures: ["Feature X", "Feature Y"],
      pendingFeatures: [],
      blockers: [],
    });
    assert("Shows DELIVERED", output.includes("✅ DELIVERED"));
    assert("Shows grade PASS", output.includes("Grade: PASS"));
    assert("Shows 100%", output.includes("100%"));
    assert("Shows full bar (▰)", output.includes("▰".repeat(BAR_WIDTH)));
    assert("Shows DoD count", output.includes("DoD: 8/8"));
    assert("Under 4096 chars", output.length <= 4096);
  }

  // --- Test 21: renderFinalStatus — fail ---
  console.log("\n21. renderFinalStatus — fail");
  {
    const output = renderFinalStatus({
      taskDescription: "Failed task",
      status: "fail",
      evalGrade: "FAIL",
      dodTotal: 8,
      dodCompleted: 3,
      elapsedSeconds: 1200,
      completedFeatures: ["Feature X"],
      pendingFeatures: ["Feature Y", "Feature Z"],
      blockers: ["Critical bug"],
    });
    assert("Shows FAILED", output.includes("❌ FAILED"));
    assert("Shows grade FAIL", output.includes("Grade: FAIL"));
    assert("Shows partial progress", output.includes("38%"));
    assert("Shows blocker", output.includes("Critical bug"));
  }

  // --- Test 22: renderFinalStatus — cancelled ---
  console.log("\n22. renderFinalStatus — cancelled");
  {
    const output = renderFinalStatus({
      taskDescription: "Cancelled task",
      status: "cancelled",
      dodTotal: 5,
      dodCompleted: 2,
      elapsedSeconds: 60,
      completedFeatures: ["A"],
      pendingFeatures: ["B", "C"],
      blockers: [],
    });
    assert("Shows CANCELLED", output.includes("🚫 CANCELLED"));
    assert("Shows partial progress", output.includes("40%"));
    assert("Under 4096 chars", output.length <= 4096);
  }

  // --- Test 23: Edge cases — dodCompleted > dodTotal ---
  console.log("\n23. Edge cases — dodCompleted > dodTotal");
  {
    const output = renderProgressBar({
      taskDescription: "Edge case",
      phase: "eval",
      completedFeatures: [],
      pendingFeatures: [],
      blockers: [],
      dodTotal: 5,
      dodCompleted: 10,
      elapsedSeconds: 0,
    });
    assert("Clamps to 100%", output.includes("100%"));
    assert("Clamps dodCompleted to dodTotal", output.includes("5/5 done"));
  }

  // --- Test 24: Edge cases — negative elapsedSeconds ---
  console.log("\n24. Edge cases — negative elapsedSeconds");
  {
    const output = renderProgressBar({
      taskDescription: "Negative time",
      phase: "plan",
      completedFeatures: [],
      pendingFeatures: [],
      blockers: [],
      dodTotal: 1,
      dodCompleted: 0,
      elapsedSeconds: -100,
    });
    assert("Handles negative elapsed gracefully", output.includes("⏱0s"));
  }

  // ─── Sprint-specific Tests ───

  // --- Test 25: renderProgressBar — sprint mode, sprint 1/4 ---
  console.log("\n25. renderProgressBar — sprint mode (sprint 1/4)");
  {
    const output = renderProgressBar({
      taskDescription: "Large project with sprints",
      phase: "build",
      completedFeatures: ["Schema types"],
      pendingFeatures: ["API routes", "Auth middleware"],
      inProgressFeature: "API routes",
      blockers: [],
      dodTotal: 10,
      dodCompleted: 3,
      elapsedSeconds: 300,
      sprintCurrent: 1,
      sprintTotal: 4,
    });
    assert("Shows sprint header", output.includes("📦 Sprint 1/4"));
    assert("Shows task description", output.includes("Large project with sprints"));
    assert("Shows phase indicator", output.includes("▶build"));
    assert("Sprint status line: ⏳⬜⬜⬜", output.includes("⏳⬜⬜⬜"));
    // Overall: (0 completed sprints * 100 + 30%) / 4 = 8%
    assert("Overall percentage is 8%", output.includes("8%"));
    assert("Shows completed feature", output.includes("✅ Schema types"));
    assert("Shows in-progress feature", output.includes("⏳ API routes"));
    assert("Shows pending feature", output.includes("⬜ Auth middleware"));
    assert("Under 4096 chars", output.length <= 4096);
  }

  // --- Test 26: renderProgressBar — sprint mode, sprint 3/4 (midway) ---
  console.log("\n26. renderProgressBar — sprint mode (sprint 3/4)");
  {
    const output = renderProgressBar({
      taskDescription: "Large project",
      phase: "challenge",
      completedFeatures: ["Notifications", "Search"],
      pendingFeatures: ["File upload"],
      blockers: [],
      dodTotal: 12,
      dodCompleted: 8,
      elapsedSeconds: 7200,
      sprintCurrent: 3,
      sprintTotal: 4,
    });
    assert("Shows sprint 3/4", output.includes("📦 Sprint 3/4"));
    assert("Sprint status: ✅✅⏳⬜", output.includes("✅✅⏳⬜"));
    // Overall: (2 * 100 + 67%) / 4 = 67%
    assert("Overall percentage is 67%", output.includes("67%"));
    assert("Shows 2h elapsed", output.includes("2h 0m 0s"));
    assert("Under 4096 chars", output.length <= 4096);
  }

  // --- Test 27: renderProgressBar — sprint mode, last sprint 100% ---
  console.log("\n27. renderProgressBar — sprint mode (last sprint at 100%)");
  {
    const output = renderProgressBar({
      taskDescription: "Almost done",
      phase: "eval",
      completedFeatures: ["API docs", "Integration tests"],
      pendingFeatures: [],
      blockers: [],
      dodTotal: 8,
      dodCompleted: 8,
      elapsedSeconds: 28800,
      sprintCurrent: 4,
      sprintTotal: 4,
    });
    assert("Shows sprint 4/4", output.includes("📦 Sprint 4/4"));
    assert("Sprint status: ✅✅✅⏳", output.includes("✅✅✅⏳"));
    // Overall: (3 * 100 + 100%) / 4 = 100%
    assert("Overall percentage is 100%", output.includes("100%"));
    assert("Under 4096 chars", output.length <= 4096);
  }

  // --- Test 28: renderProgressBar — no sprint params (backward compat) ---
  console.log("\n28. renderProgressBar — no sprint params (backward compatible)");
  {
    const output = renderProgressBar({
      taskDescription: "Simple project",
      phase: "build",
      completedFeatures: ["Feature A"],
      pendingFeatures: ["Feature B"],
      blockers: [],
      dodTotal: 4,
      dodCompleted: 2,
      elapsedSeconds: 120,
    });
    assert("No sprint header", !output.includes("📦 Sprint"));
    assert("No sprint status line", !output.includes("⏳⬜"));
    assert("Shows 50%", output.includes("50%"));
    assert("Shows task description", output.includes("Simple project"));
    assert("Under 4096 chars", output.length <= 4096);
  }

  // --- Test 29: renderFinalStatus — with sprint params ---
  console.log("\n29. renderFinalStatus — with sprint params");
  {
    const output = renderFinalStatus({
      taskDescription: "Sprint project completed",
      status: "pass",
      evalGrade: "PASS",
      dodTotal: 45,
      dodCompleted: 45,
      elapsedSeconds: 28800,
      completedFeatures: ["Schema", "Auth", "CRUD", "Notifications", "Dashboard"],
      pendingFeatures: [],
      blockers: [],
      sprintCurrent: 6,
      sprintTotal: 6,
    });
    assert("Shows DELIVERED", output.includes("✅ DELIVERED"));
    assert("Shows sprint count", output.includes("📦 Sprints: 6/6 completed"));
    assert("Shows DoD", output.includes("DoD: 45/45"));
    assert("Under 4096 chars", output.length <= 4096);
  }

  // --- Test 30: renderFinalStatus — without sprint params (backward compat) ---
  console.log("\n30. renderFinalStatus — without sprint params (backward compat)");
  {
    const output = renderFinalStatus({
      taskDescription: "Simple completed",
      status: "pass",
      evalGrade: "PASS",
      dodTotal: 8,
      dodCompleted: 8,
      elapsedSeconds: 600,
      completedFeatures: ["A", "B"],
      pendingFeatures: [],
      blockers: [],
    });
    assert("Shows DELIVERED", output.includes("✅ DELIVERED"));
    assert("No sprint line", !output.includes("📦 Sprints:"));
    assert("Under 4096 chars", output.length <= 4096);
  }

  // --- Test 31: renderProgressBar — sprint mode with blockers ---
  console.log("\n31. renderProgressBar — sprint mode with blockers");
  {
    const output = renderProgressBar({
      taskDescription: "Sprint with blockers",
      phase: "build",
      completedFeatures: [],
      pendingFeatures: ["Feature X"],
      blockers: ["Test failure"],
      dodTotal: 5,
      dodCompleted: 0,
      elapsedSeconds: 100,
      sprintCurrent: 2,
      sprintTotal: 3,
    });
    assert("Shows sprint header", output.includes("📦 Sprint 2/3"));
    assert("Shows blocker section", output.includes("⚠️ Blockers:"));
    assert("Shows blocker detail", output.includes("Test failure"));
    assert("Sprint status: ✅⏳⬜", output.includes("✅⏳⬜"));
    assert("Under 4096 chars", output.length <= 4096);
  }

  // --- Test 32: renderFinalStatus — sprint mode fail ---
  console.log("\n32. renderFinalStatus — sprint mode fail");
  {
    const output = renderFinalStatus({
      taskDescription: "Sprint project failed",
      status: "fail",
      evalGrade: "FAIL",
      dodTotal: 30,
      dodCompleted: 15,
      elapsedSeconds: 3600,
      completedFeatures: ["A", "B"],
      pendingFeatures: ["C", "D"],
      blockers: ["Critical regression"],
      sprintCurrent: 3,
      sprintTotal: 5,
    });
    assert("Shows FAILED", output.includes("❌ FAILED"));
    assert("Shows sprint count", output.includes("📦 Sprints: 3/5 completed"));
    assert("Shows blocker", output.includes("Critical regression"));
    assert("Under 4096 chars", output.length <= 4096);
  }

  // ── 33. Feature extraction from plan ──
  console.log("\n33. Feature extraction from plan");
  {
    const planWithFeatures = `# My Plan

## Phase 1: Core

- [ ] **Feature A**: Build the widget
- [ ] **Feature B**: Test the widget
- [x] **Feature C**: Deploy the widget

## Phase 2: Polish

- [ ] Add error handling
- [ ] Improve performance

\`\`\`
- [ ] This should be ignored (in code block)
\`\`\`
`;
    const features = validation.extractFeatures(planWithFeatures);
    assert("Extracts 5 features", features.length === 5, `got ${features.length}`);
    assert("First feature id is f001", features[0].id === "f001");
    assert("Category includes Phase 1", features[0].category.includes("Phase 1"));
    assert("Unchecked = pending", features[0].status === "pending");
    assert("Checked = passed", features[2].status === "passed");
    assert("Plain text feature extracted", features[3].description === "Add error handling");
  }

  // ── 34. Feature sync from checkpoint ──
  console.log("\n34. Feature sync from checkpoint");
  {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "harness-feat-"));
    const runId = "test-feat-sync";
    const features: state.Feature[] = [
      { id: "f001", category: "Core", description: "Build the widget", status: "pending" },
      { id: "f002", category: "Core", description: "Test the widget", status: "pending" },
      { id: "f003", category: "Polish", description: "Add error handling", status: "pending" },
    ];
    state.writeFeatures(tmpDir, runId, features);

    state.syncFeaturesFromCheckpoint(
      tmpDir, runId,
      ["Build the widget"],
      ["Test the widget", "Add error handling"],
    );

    const updated = state.readFeatures(tmpDir, runId);
    assert("Completed feature → passed", updated[0].status === "passed");
    assert("Passed feature gets verifiedAt", updated[0].verifiedAt !== undefined);
    assert("Pending feature stays pending", updated[1].status === "pending");
    assert("Other pending stays pending", updated[2].status === "pending");

    fs.rmSync(tmpDir, { recursive: true, force: true });
  }

  // ── 35. Progress file generation ──
  console.log("\n35. Progress file generation");
  {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "harness-prog-"));
    const runId = "test-progress";
    const runState2: state.RunState = {
      runId,
      planPath: "/test/plan.md",
      taskDescription: "Test Task",
      startedAt: new Date().toISOString(),
      phase: "build",
      round: 1,
      checkpoints: [new Date().toISOString()],
      status: "active",
    };
    const checkpoint: state.Checkpoint = {
      timestamp: new Date().toISOString(),
      phase: "build",
      completedFeatures: ["Widget A"],
      pendingFeatures: ["Widget B"],
      blockers: [],
      summary: "Making progress",
    };
    const features: state.Feature[] = [
      { id: "f001", category: "Core", description: "Widget A", status: "passed" },
      { id: "f002", category: "Core", description: "Widget B", status: "pending" },
    ];

    state.writeProgressFile(tmpDir, runId, runState2, checkpoint, features);
    const progress = state.readProgressFile(tmpDir, runId);
    assert("Progress file exists", progress !== null);
    assert("Contains task description", progress!.includes("Test Task"));
    assert("Contains passed count", progress!.includes("Passed: 1"));
    assert("Contains pending count", progress!.includes("Pending: 1"));
    assert("Contains completed feature", progress!.includes("Widget A"));
    assert("Contains summary", progress!.includes("Making progress"));

    fs.rmSync(tmpDir, { recursive: true, force: true });
  }

  // ── 36. Feature immutability — passed features don't revert ──
  console.log("\n36. Feature immutability — passed features don't revert");
  {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "harness-immut-"));
    const runId = "test-immut";
    const features: state.Feature[] = [
      { id: "f001", category: "Core", description: "Already done", status: "passed", verifiedAt: "2026-01-01T00:00:00Z" },
      { id: "f002", category: "Core", description: "Still pending", status: "pending" },
    ];
    state.writeFeatures(tmpDir, runId, features);

    // Checkpoint that doesn't mention the passed feature
    state.syncFeaturesFromCheckpoint(
      tmpDir, runId,
      [],  // nothing completed this round
      ["Still pending"],
    );

    const updated = state.readFeatures(tmpDir, runId);
    assert("Passed feature stays passed", updated[0].status === "passed");
    assert("VerifiedAt preserved", updated[0].verifiedAt === "2026-01-01T00:00:00Z");
  }

  // ── 37. Work log in progress bar ──
  console.log("\n37. Work log in progress bar");
  {
    const bar = renderProgressBar({
      taskDescription: "Test Work Log",
      phase: "build",
      completedFeatures: ["Done A"],
      pendingFeatures: ["Pending B"],
      blockers: [],
      dodTotal: 4,
      dodCompleted: 2,
      elapsedSeconds: 120,
      workLog: ["Editing state.ts", "Running tests", "Pushing to GitHub"],
    });
    assert("Contains work log marker", bar.includes("📝"));
    assert("Shows last action", bar.includes("Pushing to GitHub"));
    assert("Shows earlier action", bar.includes("Running tests"));
    assert("Under 4096 chars", bar.length <= 4096);
  }

  // ── 38. Work log truncation ──
  console.log("\n38. Work log truncation (max 5 entries)");
  {
    const bar = renderProgressBar({
      taskDescription: "Test Truncation",
      phase: "build",
      completedFeatures: [],
      pendingFeatures: [],
      blockers: [],
      dodTotal: 1,
      dodCompleted: 0,
      elapsedSeconds: 60,
      workLog: ["Action 1", "Action 2", "Action 3", "Action 4", "Action 5", "Action 6", "Action 7"],
    });
    // Should only show last 5
    assert("Does not show Action 1", !bar.includes("Action 1"));
    assert("Does not show Action 2", !bar.includes("Action 2"));
    assert("Shows Action 3", bar.includes("Action 3"));
    assert("Shows Action 7", bar.includes("Action 7"));
  }

  // ── 39. Empty work log doesn't render ──
  console.log("\n39. Empty work log doesn't render");
  {
    const bar = renderProgressBar({
      taskDescription: "No Log",
      phase: "plan",
      completedFeatures: [],
      pendingFeatures: [],
      blockers: [],
      dodTotal: 1,
      dodCompleted: 0,
      elapsedSeconds: 10,
    });
    assert("No work log marker", !bar.includes("📝"));
  }

  // Summary
  console.log(`\n${"─".repeat(40)}`);
  console.log(`Results: ${passed} passed, ${failed} failed, ${passed + failed} total`);
  console.log(`${"─".repeat(40)}\n`);

  // Cleanup
  fs.rmSync(testDir, { recursive: true, force: true });
  fs.rmSync(planDir, { recursive: true, force: true });

  process.exit(failed > 0 ? 1 : 0);
}

// BAR_WIDTH must match the constant in progress.ts
const BAR_WIDTH = 15;

main().catch((err) => {
  console.error("Test crashed:", err);
  process.exit(1);
});
