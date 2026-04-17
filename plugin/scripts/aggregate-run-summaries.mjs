#!/usr/bin/env node
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

function parseArgs(argv) {
  const args = { json: false };
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === '--json') {
      args.json = true;
    } else if (arg === '--runsDir') {
      args.runsDir = argv[++i];
    } else if (arg === '--out') {
      args.out = argv[++i];
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

function listSummaries(runsDir) {
  if (!fs.existsSync(runsDir)) return [];
  return fs.readdirSync(runsDir)
    .map((entry) => path.join(runsDir, entry))
    .filter((entryPath) => {
      try { return fs.statSync(entryPath).isDirectory(); } catch { return false; }
    })
    .map((runDir) => readJson(path.join(runDir, 'run-summary.json')))
    .filter(Boolean)
    .sort((a, b) => String(b.updatedAt ?? '').localeCompare(String(a.updatedAt ?? '')));
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
      codes.push({ code, runId: summary.runId, domain: summary.failureDomain });
    }
  }
  return codes;
}

function buildReport(summaries) {
  const failureCodeRows = flattenFailureCodes(summaries);
  const delivered = summaries.filter((s) => s.finalOutcome === 'delivered');
  const failedOrIterating = summaries.filter((s) => s.failureDomain !== 'none');

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
    }));

  return {
    generatedAt: new Date().toISOString(),
    runsDir: null,
    totalRuns: summaries.length,
    deliveredRuns: delivered.length,
    nonDeliveredRuns: summaries.length - delivered.length,
    statusCounts: tally(summaries, (s) => s.runStatus),
    finalOutcomeCounts: tally(summaries, (s) => s.finalOutcome),
    failureDomainCounts: tally(failedOrIterating, (s) => s.failureDomain),
    failureCodeCounts: tally(failureCodeRows, (row) => row.code),
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
    falsePassSuspects,
    recentRuns: summaries.slice(0, 10).map((s) => ({
      runId: s.runId,
      taskDescription: s.taskDescription,
      finalOutcome: s.finalOutcome,
      failureDomain: s.failureDomain,
      failureCode: s.failureCode,
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
    '## False-pass suspects',
    suspects,
    '',
    '## Final outcome counts',
    ...Object.entries(report.finalOutcomeCounts).map(([key, value]) => `- ${key}: ${value}`),
  ].join('\n');
}

const args = parseArgs(process.argv.slice(2));
const runsDir = path.resolve(args.runsDir ?? defaultRunsDir());
const summaries = listSummaries(runsDir);
const report = buildReport(summaries);
report.runsDir = runsDir;

const output = args.json ? JSON.stringify(report, null, 2) : renderText(report);
if (args.out) {
  const outPath = path.resolve(args.out);
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, output + '\n');
}
process.stdout.write(output + '\n');
