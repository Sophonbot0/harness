#!/usr/bin/env node
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const STALE_RUN_TIMEOUT_MINUTES = 120;
const SUBAGENT_STALE_TIMEOUT_MINUTES = 30;

function parseArgs(argv) {
  const args = { json: false, backfill: true, force: false };
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === '--json') {
      args.json = true;
    } else if (arg === '--runsDir') {
      args.runsDir = argv[++i];
    } else if (arg === '--out') {
      args.out = argv[++i];
    } else if (arg === '--no-backfill') {
      args.backfill = false;
    } else if (arg === '--force') {
      args.force = true;
    }
  }
  return args;
}

function defaultRunsDir() {
  return path.join(os.homedir(), '.openclaw', 'harness-enforcer', 'runs');
}

function readJson(filePath) {
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
  } catch {
    return null;
  }
}

function readJsonl(filePath) {
  try {
    if (!fs.existsSync(filePath)) return [];
    return fs.readFileSync(filePath, 'utf8')
      .split('\n')
      .filter((line) => line.trim().length > 0)
      .map((line) => {
        try {
          return JSON.parse(line);
        } catch {
          return null;
        }
      })
      .filter(Boolean);
  } catch {
    return [];
  }
}

function safeWriteJson(filePath, value) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, JSON.stringify(value, null, 2) + '\n');
}

function normalizeStatus(rawStatus) {
  if (rawStatus === 'active' || rawStatus === 'completed' || rawStatus === 'failed' || rawStatus === 'cancelled') {
    return { status: rawStatus, normalizedFromLegacy: false, normalizationKey: null, sourceStatus: rawStatus };
  }
  if (rawStatus === 'delivered') {
    return {
      status: 'completed',
      normalizedFromLegacy: true,
      normalizationKey: 'delivered_to_completed',
      sourceStatus: 'delivered',
    };
  }
  if (typeof rawStatus === 'string') {
    return {
      status: 'failed',
      normalizedFromLegacy: true,
      normalizationKey: `unknown_${rawStatus}_to_failed`,
      sourceStatus: rawStatus,
    };
  }
  return {
    status: 'failed',
    normalizedFromLegacy: true,
    normalizationKey: 'missing_status_to_failed',
    sourceStatus: String(rawStatus),
  };
}

function derivePhaseStatuses(runState, checkpoints, finalOutcome) {
  const observed = new Set(checkpoints.map((cp) => String(cp.phase || '').toLowerCase()));
  const currentPhase = String(runState.phase || '').toLowerCase();

  let plannerStatus = 'not_started';
  let generatorStatus = 'not_started';
  let adversaryStatus = 'not_started';
  let evaluatorStatus = 'not_started';

  if (runState.status === 'completed') {
    return {
      plannerStatus: 'completed',
      generatorStatus: 'completed',
      adversaryStatus: 'completed',
      evaluatorStatus: 'completed',
    };
  }

  if (currentPhase === 'plan') {
    plannerStatus = 'in_progress';
  } else if (observed.has('plan') || ['build', 'challenge', 'eval', 'iteration'].includes(currentPhase)) {
    plannerStatus = 'completed';
  }

  if (currentPhase === 'build') {
    generatorStatus = 'in_progress';
  } else if (observed.has('build') || ['challenge', 'eval', 'iteration'].includes(currentPhase)) {
    generatorStatus = 'completed';
  }

  if (currentPhase === 'challenge') {
    adversaryStatus = 'in_progress';
  } else if (observed.has('challenge') || ['eval', 'iteration'].includes(currentPhase)) {
    adversaryStatus = 'completed';
  }

  if (currentPhase === 'eval') {
    evaluatorStatus = 'in_progress';
  } else if (observed.has('eval') || observed.has('iteration')) {
    evaluatorStatus = 'completed';
  }

  if (runState.status === 'cancelled') {
    if (currentPhase === 'plan') plannerStatus = 'blocked';
    if (currentPhase === 'build') generatorStatus = 'blocked';
    if (currentPhase === 'challenge') adversaryStatus = 'blocked';
    if (currentPhase === 'eval') evaluatorStatus = 'blocked';
  }

  if (runState.status === 'failed') {
    if (currentPhase === 'plan') plannerStatus = 'failed';
    if (currentPhase === 'build') generatorStatus = 'failed';
    if (currentPhase === 'challenge') adversaryStatus = 'failed';
    if (currentPhase === 'eval') evaluatorStatus = 'failed';
  }

  if (String(finalOutcome).includes('iteration_required') || String(finalOutcome).includes('eval_failed')) {
    evaluatorStatus = 'failed';
    if (runState.status === 'active' && currentPhase === 'build') {
      generatorStatus = 'in_progress';
    }
  }

  return { plannerStatus, generatorStatus, adversaryStatus, evaluatorStatus };
}

function deriveStaleState(runState, checkpoints) {
  const staleThresholdMinutes = runState.isSubagent ? SUBAGENT_STALE_TIMEOUT_MINUTES : STALE_RUN_TIMEOUT_MINUTES;
  const lastCheckpoint = checkpoints.length > 0 ? checkpoints[checkpoints.length - 1] : null;
  const latestActivity = lastCheckpoint?.timestamp || runState.lastCheckpointAt || runState.startedAt;
  const staleMinutes = Math.max(0, Math.round((Date.now() - new Date(latestActivity).getTime()) / 60000));
  const staleActive = runState.status === 'active' && staleMinutes > staleThresholdMinutes;
  return { staleActive, staleMinutes, staleThresholdMinutes };
}

function resolvePlanArtifactPath(runDir, runState, summaryHints = {}) {
  const candidates = [
    summaryHints.planPath,
    runState.planPath,
    path.join(runDir, 'plan.md'),
  ].filter(Boolean);

  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) return candidate;
  }

  return runState.planPath || path.join(runDir, 'plan.md');
}

function deriveArtifactCompleteness(runDir, runState, summaryHints = {}) {
  const resolvedPlanPath = resolvePlanArtifactPath(runDir, runState, summaryHints);
  const required = [
    { name: 'run_state', path: path.join(runDir, 'run-state.json'), required: true, exists: fs.existsSync(path.join(runDir, 'run-state.json')) },
    { name: 'plan', path: resolvedPlanPath, required: true, exists: !!resolvedPlanPath && fs.existsSync(resolvedPlanPath) },
    { name: 'contract', path: path.join(runDir, 'contract.json'), required: true, exists: fs.existsSync(path.join(runDir, 'contract.json')) },
    { name: 'run_summary', path: path.join(runDir, 'run-summary.json'), required: true, exists: true },
  ];

  const optional = [
    { name: 'progress', path: path.join(runDir, 'progress.md'), required: false, exists: fs.existsSync(path.join(runDir, 'progress.md')) },
    { name: 'checkpoints', path: path.join(runDir, 'checkpoints.jsonl'), required: false, exists: fs.existsSync(path.join(runDir, 'checkpoints.jsonl')) },
    { name: 'delivery', path: path.join(runDir, 'delivery.json'), required: false, exists: fs.existsSync(path.join(runDir, 'delivery.json')) },
  ];

  if (summaryHints.evalReportPath) {
    optional.push({
      name: 'eval_report',
      path: summaryHints.evalReportPath,
      required: false,
      exists: fs.existsSync(summaryHints.evalReportPath),
    });
  }

  if (summaryHints.challengeReportPath) {
    optional.push({
      name: 'challenge_report',
      path: summaryHints.challengeReportPath,
      required: false,
      exists: fs.existsSync(summaryHints.challengeReportPath),
    });
  }

  if (runState.status === 'completed') {
    const delivery = optional.find((artifact) => artifact.name === 'delivery');
    if (delivery) delivery.required = true;
    const evalReport = optional.find((artifact) => artifact.name === 'eval_report');
    if (evalReport) evalReport.required = true;
  }

  if (['challenge', 'eval', 'completed', 'failed'].includes(String(runState.phase)) || summaryHints.challengeReportPath) {
    const checkpoints = optional.find((artifact) => artifact.name === 'checkpoints');
    if (checkpoints) checkpoints.required = true;
  }

  const requiredArtifacts = [...required, ...optional.filter((artifact) => artifact.required)];
  const optionalArtifacts = optional.filter((artifact) => !artifact.required);
  const missingRequired = requiredArtifacts.filter((artifact) => !artifact.exists).map((artifact) => artifact.name);
  const missingOptional = optionalArtifacts.filter((artifact) => !artifact.exists).map((artifact) => artifact.name);
  const total = requiredArtifacts.length + optionalArtifacts.length;
  const existing = [...requiredArtifacts, ...optionalArtifacts].filter((artifact) => artifact.exists).length;

  return {
    required: requiredArtifacts,
    optional: optionalArtifacts,
    missingRequired,
    missingOptional,
    complete: missingRequired.length === 0,
    score: total > 0 ? Number((existing / total).toFixed(3)) : 1,
  };
}

function normalizeRunState(rawState) {
  const normalized = normalizeStatus(rawState?.status);
  return {
    ...rawState,
    status: normalized.status,
    sourceStatus: normalized.sourceStatus,
    normalizedFromLegacy: normalized.normalizedFromLegacy,
    normalizationKey: normalized.normalizationKey,
  };
}

function needsBackfill(existingSummary, runDir, runState) {
  if (!existingSummary) return true;
  if (!existingSummary.instrumentationKind) return true;
  if (existingSummary.runStatus === 'delivered') return true;
  if (existingSummary.runStatus !== runState.status) return true;
  if (existingSummary.sourceRunStatus !== runState.sourceStatus) return true;
  if (runState.status === 'active' && existingSummary.staleActive === undefined) return true;
  if (!existingSummary.dataQuality) return true;

  const resolvedPlanPath = resolvePlanArtifactPath(runDir, runState, existingSummary?.artifacts ?? {});
  if (existingSummary?.artifacts?.planPath !== resolvedPlanPath) return true;

  const expectedArtifactCompleteness = deriveArtifactCompleteness(runDir, runState, { ...(existingSummary?.artifacts ?? {}), planPath: resolvedPlanPath });
  const existingMissingRequired = JSON.stringify(existingSummary?.artifactCompleteness?.missingRequired ?? []);
  const expectedMissingRequired = JSON.stringify(expectedArtifactCompleteness.missingRequired ?? []);
  const existingMissingOptional = JSON.stringify(existingSummary?.artifactCompleteness?.missingOptional ?? []);
  const expectedMissingOptional = JSON.stringify(expectedArtifactCompleteness.missingOptional ?? []);
  if (existingMissingRequired !== expectedMissingRequired) return true;
  if (existingMissingOptional !== expectedMissingOptional) return true;

  return false;
}

function deriveDataQuality(instrumentationKind, artifactCompleteness, runState) {
  const reasons = [];
  if (instrumentationKind === 'backfilled') reasons.push('backfilled_summary');
  if (runState.normalizedFromLegacy) reasons.push('legacy_status_normalized');
  if (artifactCompleteness.missingRequired.length > 0) reasons.push(`missing_required:${artifactCompleteness.missingRequired.join(',')}`);
  else if (artifactCompleteness.missingOptional.length > 0) reasons.push('missing_optional_artifacts');

  let grade = 'high';
  if (reasons.some((reason) => reason.startsWith('missing_required:') || reason === 'legacy_status_normalized')) {
    grade = 'low';
  } else if (reasons.length > 0) {
    grade = 'medium';
  }

  return { grade, reasons };
}

function inferBackfilledFailure(runState, artifactCompleteness, staleState, lastCheckpoint, existingSummary) {
  if (existingSummary?.failureCode || (Array.isArray(existingSummary?.failureCodes) && existingSummary.failureCodes.length > 0)) {
    return {
      failureDomain: existingSummary.failureDomain,
      failureCode: existingSummary.failureCode,
      failureCodes: existingSummary.failureCodes,
    };
  }

  if (staleState.staleActive) {
    return {
      failureDomain: 'harness',
      failureCode: 'stale_active',
      failureCodes: ['stale_active'],
    };
  }

  if (runState.status === 'cancelled') {
    return {
      failureDomain: 'user',
      failureCode: 'cancelled',
      failureCodes: ['cancelled'],
    };
  }

  if (runState.status === 'failed') {
    if (artifactCompleteness.missingRequired.includes('plan')) {
      return {
        failureDomain: 'environment',
        failureCode: 'plan_missing',
        failureCodes: ['plan_missing'],
      };
    }
    if (artifactCompleteness.missingRequired.includes('contract')) {
      return {
        failureDomain: 'environment',
        failureCode: 'contract_missing',
        failureCodes: ['contract_missing'],
      };
    }
    if (String(lastCheckpoint?.phase || '').toLowerCase() === 'iteration' || /failed eval|iterating/i.test(String(lastCheckpoint?.summary || ''))) {
      return {
        failureDomain: 'harness',
        failureCode: 'eval_failed',
        failureCodes: ['eval_failed'],
      };
    }
  }

  return {
    failureDomain: runState.status === 'completed' ? 'none' : runState.status === 'cancelled' ? 'user' : runState.status === 'failed' ? 'unknown' : 'none',
    failureCode: undefined,
    failureCodes: undefined,
  };
}

function backfillSummary(runId, runDir, rawState, existingSummary) {
  const runState = normalizeRunState(rawState);
  const checkpoints = readJsonl(path.join(runDir, 'checkpoints.jsonl'));
  const dodItems = readJson(path.join(runDir, 'dod-items.json')) || [];
  const features = readJson(path.join(runDir, 'features.json')) || [];
  const contractItems = readJson(path.join(runDir, 'contract.json')) || [];
  const delivery = readJson(path.join(runDir, 'delivery.json'));
  const lastCheckpoint = checkpoints.length > 0 ? checkpoints[checkpoints.length - 1] : null;
  const staleState = deriveStaleState(runState, checkpoints);
  const finalOutcome = runState.status === 'completed'
    ? 'delivered'
    : runState.status === 'cancelled'
      ? 'cancelled'
      : runState.status === 'failed'
        ? 'failed'
        : staleState.staleActive
          ? 'active_stale'
          : 'active';
  const phaseStatuses = derivePhaseStatuses(runState, checkpoints, finalOutcome);
  const resolvedPlanPath = resolvePlanArtifactPath(runDir, runState, existingSummary?.artifacts ?? {});
  const artifactCompleteness = deriveArtifactCompleteness(runDir, runState, { ...(existingSummary?.artifacts ?? {}), planPath: resolvedPlanPath });
  const instrumentationKind = existingSummary?.instrumentationKind ?? 'backfilled';
  const dataQuality = deriveDataQuality(instrumentationKind, artifactCompleteness, runState);
  const inferredFailure = inferBackfilledFailure(runState, artifactCompleteness, staleState, lastCheckpoint, existingSummary);
  const historicalFailureCodes = [...new Set([
    ...(Array.isArray(existingSummary?.historicalFailureCodes) ? existingSummary.historicalFailureCodes : []),
    ...(Array.isArray(existingSummary?.failureCodes) ? existingSummary.failureCodes : []),
    ...(existingSummary?.failureCode ? [existingSummary.failureCode] : []),
    ...(Array.isArray(inferredFailure.failureCodes) ? inferredFailure.failureCodes : []),
    ...(inferredFailure.failureCode ? [inferredFailure.failureCode] : []),
  ])];
  const updatedAt = existingSummary?.updatedAt
    || delivery?.deliveredAt
    || lastCheckpoint?.timestamp
    || runState.lastCheckpointAt
    || runState.startedAt
    || new Date().toISOString();

  return {
    runId,
    taskDescription: runState.taskDescription,
    startedAt: runState.startedAt,
    updatedAt,
    ...(delivery?.deliveredAt ? { endedAt: delivery.deliveredAt } : {}),
    instrumentationKind,
    runStatus: runState.status,
    ...(runState.sourceStatus ? { sourceRunStatus: runState.sourceStatus } : {}),
    ...(runState.normalizedFromLegacy ? { legacyNormalized: true } : {}),
    phase: runState.phase,
    round: runState.round,
    plannerStatus: existingSummary?.plannerStatus ?? phaseStatuses.plannerStatus,
    generatorStatus: existingSummary?.generatorStatus ?? phaseStatuses.generatorStatus,
    adversaryStatus: existingSummary?.adversaryStatus ?? phaseStatuses.adversaryStatus,
    evaluatorStatus: existingSummary?.evaluatorStatus ?? phaseStatuses.evaluatorStatus,
    finalOutcome,
    failureDomain: inferredFailure.failureDomain,
    ...(inferredFailure.failureCode ? { failureCode: inferredFailure.failureCode } : {}),
    ...(Array.isArray(inferredFailure.failureCodes) && inferredFailure.failureCodes.length > 0 ? { failureCodes: inferredFailure.failureCodes } : {}),
    ...(historicalFailureCodes.length > 0 ? { historicalFailureCodes } : {}),
    ...(staleState.staleActive ? { staleActive: true, staleMinutes: staleState.staleMinutes, staleThresholdMinutes: staleState.staleThresholdMinutes } : {}),
    summary: existingSummary?.summary ?? (staleState.staleActive ? `Harness run appears stale (${staleState.staleMinutes}min since last activity).` : `Harness run is ${runState.status}.`),
    metrics: {
      elapsedSeconds: delivery?.elapsedSeconds ?? Math.max(0, Math.round((Date.now() - new Date(runState.startedAt).getTime()) / 1000)),
      checkpointCount: checkpoints.length,
      dodTotal: dodItems.length,
      dodCompleted: dodItems.filter((item) => item.checked).length,
      featureTotal: features.length,
      featurePassed: features.filter((feature) => feature.status === 'passed').length,
      featureFailed: features.filter((feature) => feature.status === 'failed').length,
      featurePending: features.filter((feature) => feature.status === 'pending' || feature.status === 'in_progress').length,
      contractTotal: contractItems.length,
      contractPassed: contractItems.filter((item) => item.status === 'passed').length,
      contractFailed: contractItems.filter((item) => item.status === 'failed').length,
      contractPending: contractItems.filter((item) => item.status === 'pending' || item.status === 'in_progress').length,
      contractSkipped: contractItems.filter((item) => item.status === 'skipped').length,
    },
    artifacts: {
      runDir,
      runStatePath: path.join(runDir, 'run-state.json'),
      checkpointsPath: path.join(runDir, 'checkpoints.jsonl'),
      planPath: resolvedPlanPath,
      contractPath: path.join(runDir, 'contract.json'),
      progressPath: path.join(runDir, 'progress.md'),
      deliveryPath: path.join(runDir, 'delivery.json'),
      ...(existingSummary?.artifacts?.evalReportPath ? { evalReportPath: existingSummary.artifacts.evalReportPath } : {}),
      ...(existingSummary?.artifacts?.challengeReportPath ? { challengeReportPath: existingSummary.artifacts.challengeReportPath } : {}),
    },
    artifactCompleteness,
    dataQuality,
    ...(lastCheckpoint ? {
      latestCheckpoint: {
        timestamp: lastCheckpoint.timestamp,
        phase: lastCheckpoint.phase,
        summary: lastCheckpoint.summary,
        blockerCount: Array.isArray(lastCheckpoint.blockers) ? lastCheckpoint.blockers.length : 0,
      },
    } : {}),
    errors: Array.isArray(existingSummary?.errors) ? existingSummary.errors : [],
    warnings: Array.isArray(existingSummary?.warnings) ? existingSummary.warnings : [],
  };
}

function listSummaries(runsDir, { backfill, force = false }) {
  if (!fs.existsSync(runsDir)) return { summaries: [], metadata: { totalDirs: 0, backfilledRuns: 0, normalizedStatuses: {}, staleActives: 0 } };
  const runDirs = fs.readdirSync(runsDir)
    .map((entry) => path.join(runsDir, entry))
    .filter((entryPath) => {
      try { return fs.statSync(entryPath).isDirectory(); } catch { return false; }
    })
    .sort((a, b) => path.basename(b).localeCompare(path.basename(a)));

  const summaries = [];
  const normalizedStatuses = new Map();
  let backfilledRuns = 0;
  let staleActives = 0;

  for (const runDir of runDirs) {
    const runId = path.basename(runDir);
    const rawState = readJson(path.join(runDir, 'run-state.json'));
    if (!rawState) continue;
    const runState = normalizeRunState(rawState);
    if (runState.normalizationKey) {
      normalizedStatuses.set(runState.normalizationKey, (normalizedStatuses.get(runState.normalizationKey) ?? 0) + 1);
    }
    const existingSummary = readJson(path.join(runDir, 'run-summary.json'));
    const shouldBackfill = force || needsBackfill(existingSummary, runDir, runState);
    const summary = shouldBackfill ? backfillSummary(runId, runDir, rawState, existingSummary) : existingSummary;

    if (shouldBackfill && backfill) {
      safeWriteJson(path.join(runDir, 'run-summary.json'), summary);
    }
    if (summary.instrumentationKind === 'backfilled') {
      backfilledRuns += 1;
    }
    if (summary.staleActive) {
      staleActives += 1;
    }
    summaries.push(summary);
  }

  summaries.sort((a, b) => String(b.updatedAt ?? '').localeCompare(String(a.updatedAt ?? '')));
  return {
    summaries,
    metadata: {
      totalDirs: runDirs.length,
      backfilledRuns,
      normalizedStatuses: Object.fromEntries([...normalizedStatuses.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))),
      staleActives,
    },
  };
}

function tally(items, keyFn) {
  const counts = new Map();
  for (const item of items) {
    const key = keyFn(item);
    if (!key) continue;
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }
  return Object.fromEntries([...counts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])));
}

function flattenFailureCodes(summaries) {
  const codes = [];
  for (const summary of summaries) {
    const summaryCodes = [...new Set([
      ...(Array.isArray(summary.failureCodes) ? summary.failureCodes : []),
      ...(summary.failureCode ? [summary.failureCode] : []),
      ...(Array.isArray(summary.historicalFailureCodes) ? summary.historicalFailureCodes : []),
    ])];
    for (const code of summaryCodes) {
      codes.push({ code, runId: summary.runId, domain: summary.failureDomain, instrumentationKind: summary.instrumentationKind });
    }
  }
  return codes;
}

function accumulateArtifactDebt(summaries, key) {
  const counts = new Map();
  for (const summary of summaries) {
    const names = summary.artifactCompleteness?.[key] ?? [];
    for (const name of names) {
      counts.set(name, (counts.get(name) ?? 0) + 1);
    }
  }
  return Object.fromEntries([...counts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])));
}

function buildReport(summaries, metadata) {
  const failureCodeRows = flattenFailureCodes(summaries);
  const delivered = summaries.filter((s) => s.finalOutcome === 'delivered');
  const failedOrIterating = summaries.filter((s) => s.failureDomain !== 'none');
  const nativeSummaries = summaries.filter((s) => s.instrumentationKind === 'native');
  const backfilledSummaries = summaries.filter((s) => s.instrumentationKind === 'backfilled');
  const nativeFailureRows = failureCodeRows.filter((row) => row.instrumentationKind === 'native');
  const backfilledFailureRows = failureCodeRows.filter((row) => row.instrumentationKind === 'backfilled');

  const falsePassSuspects = delivered
    .filter((s) =>
      (Array.isArray(s.warnings) && s.warnings.length > 0)
      || (s.artifactCompleteness && !s.artifactCompleteness.complete)
      || (s.artifactCompleteness && Array.isArray(s.artifactCompleteness.missingOptional) && s.artifactCompleteness.missingOptional.length > 0)
    )
    .map((s) => ({
      runId: s.runId,
      taskDescription: s.taskDescription,
      warningCount: Array.isArray(s.warnings) ? s.warnings.length : 0,
      missingRequired: s.artifactCompleteness?.missingRequired ?? [],
      missingOptional: s.artifactCompleteness?.missingOptional ?? [],
      finalOutcome: s.finalOutcome,
      instrumentationKind: s.instrumentationKind,
    }));

  return {
    generatedAt: new Date().toISOString(),
    runsDir: null,
    totalRuns: summaries.length,
    deliveredRuns: delivered.length,
    nonDeliveredRuns: summaries.length - delivered.length,
    statusCounts: tally(summaries, (s) => s.runStatus),
    finalOutcomeCounts: tally(summaries, (s) => s.finalOutcome),
    instrumentationCounts: {
      native: nativeSummaries.length,
      backfilled: backfilledSummaries.length,
    },
    dataQualityCounts: tally(summaries, (s) => s.dataQuality?.grade),
    failureDomainCounts: tally(failedOrIterating, (s) => s.failureDomain),
    failureCodeCounts: tally(failureCodeRows, (row) => row.code),
    nativeFailureCodeCounts: tally(nativeFailureRows, (row) => row.code),
    backfilledFailureCodeCounts: tally(backfilledFailureRows, (row) => row.code),
    topFailureClasses: Object.entries(tally(failureCodeRows, (row) => row.code))
      .slice(0, 10)
      .map(([code, count]) => ({ code, count })),
    phaseStatusCounts: {
      planner: tally(summaries, (s) => s.plannerStatus),
      generator: tally(summaries, (s) => s.generatorStatus),
      adversary: tally(summaries, (s) => s.adversaryStatus),
      evaluator: tally(summaries, (s) => s.evaluatorStatus),
    },
    environmentVsHarnessSplit: {
      harness: failedOrIterating.filter((s) => s.failureDomain === 'harness').length,
      environment: failedOrIterating.filter((s) => s.failureDomain === 'environment').length,
      user: failedOrIterating.filter((s) => s.failureDomain === 'user').length,
      unknown: failedOrIterating.filter((s) => s.failureDomain === 'unknown').length,
    },
    artifactValidity: {
      complete: summaries.filter((s) => s.artifactCompleteness?.complete).length,
      incomplete: summaries.filter((s) => s.artifactCompleteness && !s.artifactCompleteness.complete).length,
      averageScore: summaries.length > 0
        ? Number((summaries.reduce((acc, s) => acc + (Number(s.artifactCompleteness?.score) || 0), 0) / summaries.length).toFixed(3))
        : 0,
    },
    artifactDebt: {
      required: accumulateArtifactDebt(summaries, 'missingRequired'),
      optional: accumulateArtifactDebt(summaries, 'missingOptional'),
    },
    legacyDataQuality: {
      backfilledRuns: metadata.backfilledRuns,
      normalizedStatuses: metadata.normalizedStatuses,
      sourceRunStatusCounts: tally(summaries.filter((s) => s.sourceRunStatus), (s) => s.sourceRunStatus),
      legacyNormalizedRuns: summaries.filter((s) => s.legacyNormalized).length,
    },
    staleActive: {
      count: summaries.filter((s) => s.staleActive).length,
      runs: summaries
        .filter((s) => s.staleActive)
        .slice(0, 20)
        .map((s) => ({
          runId: s.runId,
          taskDescription: s.taskDescription,
          staleMinutes: s.staleMinutes,
          staleThresholdMinutes: s.staleThresholdMinutes,
        })),
    },
    falsePassSuspects,
    recentRuns: summaries.slice(0, 10).map((s) => ({
      runId: s.runId,
      taskDescription: s.taskDescription,
      finalOutcome: s.finalOutcome,
      failureDomain: s.failureDomain,
      failureCode: s.failureCode,
      instrumentationKind: s.instrumentationKind,
      staleActive: !!s.staleActive,
      updatedAt: s.updatedAt,
    })),
  };
}

function renderText(report) {
  const topFailures = report.topFailureClasses.length > 0
    ? report.topFailureClasses.map((row) => `- ${row.code}: ${row.count}`).join('\n')
    : '- none';
  const suspects = report.falsePassSuspects.length > 0
    ? report.falsePassSuspects.map((row) => `- ${row.runId}: ${row.taskDescription}`).join('\n')
    : '- none';
  const staleRuns = report.staleActive.runs.length > 0
    ? report.staleActive.runs.map((row) => `- ${row.runId}: ${row.staleMinutes}min stale`).join('\n')
    : '- none';

  return [
    '# Harness Run Summary Aggregate',
    '',
    `Runs dir: ${report.runsDir}`,
    `Generated: ${report.generatedAt}`,
    '',
    `Total runs: ${report.totalRuns}`,
    `Delivered: ${report.deliveredRuns}`,
    `Non-delivered: ${report.nonDeliveredRuns}`,
    '',
    '## Instrumentation',
    `- native: ${report.instrumentationCounts.native}`,
    `- backfilled: ${report.instrumentationCounts.backfilled}`,
    '',
    '## Top failure classes',
    topFailures,
    '',
    '## Environment vs harness split',
    `- harness: ${report.environmentVsHarnessSplit.harness}`,
    `- environment: ${report.environmentVsHarnessSplit.environment}`,
    `- user: ${report.environmentVsHarnessSplit.user}`,
    `- unknown: ${report.environmentVsHarnessSplit.unknown}`,
    '',
    '## Artifact validity',
    `- complete: ${report.artifactValidity.complete}`,
    `- incomplete: ${report.artifactValidity.incomplete}`,
    `- average score: ${report.artifactValidity.averageScore}`,
    '',
    '## Artifact debt (required)',
    ...Object.entries(report.artifactDebt.required).map(([key, value]) => `- ${key}: ${value}`),
    '',
    '## Legacy data quality',
    ...Object.entries(report.legacyDataQuality.normalizedStatuses).map(([key, value]) => `- ${key}: ${value}`),
    '',
    '## Stale active runs',
    staleRuns,
    '',
    '## False-pass suspects',
    suspects,
    '',
    '## Final outcome counts',
    ...Object.entries(report.finalOutcomeCounts).map(([key, value]) => `- ${key}: ${value}`),
  ].join('\n');
}

const args = parseArgs(process.argv.slice(2));
const runsDir = path.resolve(args.runsDir ?? defaultRunsDir());
const { summaries, metadata } = listSummaries(runsDir, { backfill: args.backfill, force: args.force });
const report = buildReport(summaries, metadata);
report.runsDir = runsDir;

const output = args.json ? JSON.stringify(report, null, 2) : renderText(report);
if (args.out) {
  const outPath = path.resolve(args.out);
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, output + '\n');
}
process.stdout.write(output + '\n');
