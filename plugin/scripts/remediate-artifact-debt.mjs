#!/usr/bin/env node
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const STALE_RUN_TIMEOUT_MINUTES = 120;

function parseArgs(argv) {
  const args = { json: false, apply: false };
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === '--json') args.json = true;
    else if (arg === '--apply') args.apply = true;
    else if (arg === '--runsDir') args.runsDir = argv[++i];
    else if (arg === '--out') args.out = argv[++i];
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

function writeJson(filePath, value) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, JSON.stringify(value, null, 2) + '\n');
}

function writeText(filePath, value) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, value.endsWith('\n') ? value : `${value}\n`);
}

function extractCheckboxItems(markdown) {
  if (!markdown) return [];
  const items = [];
  let index = 0;
  for (const line of markdown.split('\n')) {
    const match = line.trim().match(/^[-*]\s+\[([ xX])\]\s+(.*)$/);
    if (!match) continue;
    index += 1;
    items.push({
      id: `c${String(index).padStart(3, '0')}`,
      description: match[2].trim(),
      acceptanceCriteria: [`"${match[2].trim()}" is implemented and working`],
      status: match[1].toLowerCase() === 'x' ? 'passed' : 'pending',
      attempts: 0,
      maxAttempts: 3,
    });
  }
  return items;
}

function deriveContract(runDir, runState) {
  const dodItems = readJson(path.join(runDir, 'dod-items.json'));
  if (Array.isArray(dodItems) && dodItems.length > 0) {
    return dodItems.map((item, idx) => ({
      id: `c${String(idx + 1).padStart(3, '0')}`,
      description: item.text,
      acceptanceCriteria: [`"${item.text}" is implemented and working`],
      status: item.checked ? 'passed' : 'pending',
      attempts: 0,
      maxAttempts: 3,
    }));
  }

  const contractMd = fs.existsSync(path.join(runDir, 'contract.md'))
    ? fs.readFileSync(path.join(runDir, 'contract.md'), 'utf8')
    : null;
  const fromContractMd = extractCheckboxItems(contractMd);
  if (fromContractMd.length > 0) return fromContractMd;

  const planMd = runState?.planPath && fs.existsSync(runState.planPath)
    ? fs.readFileSync(runState.planPath, 'utf8')
    : null;
  const fromPlan = extractCheckboxItems(planMd);
  if (fromPlan.length > 0) return fromPlan;

  if (typeof planMd === 'string' && planMd.trim().length > 0) {
    return [{
      id: 'c001',
      description: runState?.taskDescription || 'Recovered plan item',
      acceptanceCriteria: [`"${runState?.taskDescription || 'Recovered plan item'}" is implemented and working`],
      status: 'pending',
      attempts: 0,
      maxAttempts: 3,
    }];
  }

  if (runState?.taskDescription) {
    return [{
      id: 'c001',
      description: runState.taskDescription,
      acceptanceCriteria: [`"${runState.taskDescription}" is implemented and working`],
      status: 'pending',
      attempts: 0,
      maxAttempts: 3,
    }];
  }

  return [];
}

function derivePlanMarkdown(runDir, runState, summary) {
  if (runState?.planPath && fs.existsSync(runState.planPath)) {
    return fs.readFileSync(runState.planPath, 'utf8');
  }

  const contractMdPath = path.join(runDir, 'contract.md');
  if (fs.existsSync(contractMdPath)) {
    const body = fs.readFileSync(contractMdPath, 'utf8').trim();
    if (body.length > 0) return body;
  }

  const dodItems = readJson(path.join(runDir, 'dod-items.json'));
  if (Array.isArray(dodItems) && dodItems.length > 0) {
    return [
      `# ${runState?.taskDescription || summary?.taskDescription || 'Recovered Plan'}`,
      '',
      '## Definition of Done',
      ...dodItems.map((item) => `- [${item.checked ? 'x' : ' '}] ${item.text}`),
      '',
    ].join('\n');
  }

  const features = readJson(path.join(runDir, 'features.json'));
  if (Array.isArray(features) && features.length > 0) {
    return [
      `# ${runState?.taskDescription || summary?.taskDescription || 'Recovered Plan'}`,
      '',
      '## Features',
      ...features.map((feature) => `- [${feature.status === 'passed' ? 'x' : ' '}] ${feature.description || feature.title || feature.id || 'Recovered feature'}`),
      '',
    ].join('\n');
  }

  const contract = readJson(path.join(runDir, 'contract.json'));
  if (Array.isArray(contract) && contract.length > 0) {
    return [
      `# ${runState?.taskDescription || summary?.taskDescription || 'Recovered Plan'}`,
      '',
      '## Contract',
      ...contract.map((item) => `- [${item.status === 'passed' ? 'x' : ' '}] ${item.description || item.id || 'Recovered contract item'}`),
      '',
    ].join('\n');
  }

  if (runState?.taskDescription || summary?.taskDescription) {
    return [
      `# ${runState?.taskDescription || summary?.taskDescription || 'Recovered Plan'}`,
      '',
      '## Recovered objective',
      `- [ ] ${runState?.taskDescription || summary?.taskDescription || 'Recovered task'}`,
      '',
    ].join('\n');
  }

  return null;
}

function needsCheckpoints(runState, summary) {
  return ['challenge', 'eval', 'completed', 'failed'].includes(String(runState?.phase || ''))
    || String(runState?.status || '') === 'completed'
    || String(summary?.finalOutcome || '') === 'delivered';
}

function deriveSyntheticCheckpoint(runState, summary, runDir) {
  const features = readJson(path.join(runDir, 'features.json')) || [];
  const completedFeatures = features
    .filter((feature) => feature.status === 'passed')
    .map((feature) => feature.description || feature.title || feature.id)
    .filter(Boolean);
  const pendingFeatures = features
    .filter((feature) => feature.status !== 'passed')
    .map((feature) => feature.description || feature.title || feature.id)
    .filter(Boolean);
  const blockers = summary?.failureCode ? [summary.failureCode] : [];

  return {
    checkpoint: 1,
    timestamp: summary?.updatedAt || summary?.endedAt || runState?.lastCheckpointAt || runState?.startedAt || new Date().toISOString(),
    phase: runState?.phase || 'eval',
    summary: 'Synthetic checkpoint reconstructed during artifact remediation.',
    completedFeatures,
    pendingFeatures,
    blockers,
    metadata: {
      synthetic: true,
      source: 'remediate-artifact-debt',
    },
  };
}

function deriveDelivery(runDir, runState, summary) {
  const checkpointCount = fs.existsSync(path.join(runDir, 'checkpoints.jsonl'))
    ? fs.readFileSync(path.join(runDir, 'checkpoints.jsonl'), 'utf8').split('\n').filter((line) => line.trim().length > 0).length
    : 0;
  return {
    deliveredAt: summary?.endedAt ?? summary?.updatedAt ?? runState?.lastCheckpointAt ?? runState?.startedAt ?? new Date().toISOString(),
    evalGrade: runState?.evalGrade ?? summary?.evalGrade ?? 'UNKNOWN',
    totalRounds: runState?.round ?? 1,
    elapsedSeconds: summary?.metrics?.elapsedSeconds ?? 0,
    checkpointCount,
  };
}

function deriveStaleMinutes(runState, summary) {
  const latestActivity = runState?.lastCheckpointAt || runState?.startedAt || summary?.startedAt || summary?.updatedAt;
  if (!latestActivity) return 0;
  return Math.max(0, Math.round((Date.now() - new Date(latestActivity).getTime()) / 60000));
}

function remediateRun(runDir, apply) {
  const runId = path.basename(runDir);
  const runStatePath = path.join(runDir, 'run-state.json');
  const runState = readJson(runStatePath);
  if (!runState) return null;
  const summary = readJson(path.join(runDir, 'run-summary.json'));

  const actions = [];
  let mutableRunState = { ...runState };

  const planSnapshotPath = path.join(runDir, 'plan.md');
  const originalPlanMissing = !mutableRunState.planPath || !fs.existsSync(mutableRunState.planPath);
  if (originalPlanMissing && !fs.existsSync(planSnapshotPath)) {
    const planMarkdown = derivePlanMarkdown(runDir, mutableRunState, summary);
    if (planMarkdown) {
      actions.push({ type: 'plan', path: planSnapshotPath, applied: apply });
      if (apply) writeText(planSnapshotPath, planMarkdown);
    }
  }

  if (originalPlanMissing && (fs.existsSync(planSnapshotPath) || actions.some((action) => action.type === 'plan'))) {
    actions.push({ type: 'plan_path_relinked', path: planSnapshotPath, applied: apply });
    if (apply) {
      mutableRunState = {
        ...mutableRunState,
        originalPlanPath: mutableRunState.originalPlanPath || mutableRunState.planPath || null,
        planPath: planSnapshotPath,
      };
    }
  }

  const contractPath = path.join(runDir, 'contract.json');
  if (!fs.existsSync(contractPath)) {
    const contract = deriveContract(runDir, mutableRunState);
    if (contract.length > 0) {
      actions.push({ type: 'contract', path: contractPath, itemCount: contract.length, applied: apply });
      if (apply) writeJson(contractPath, contract);
    }
  }

  const checkpointsPath = path.join(runDir, 'checkpoints.jsonl');
  if (!fs.existsSync(checkpointsPath) && needsCheckpoints(mutableRunState, summary)) {
    const syntheticCheckpoint = deriveSyntheticCheckpoint(mutableRunState, summary, runDir);
    actions.push({ type: 'checkpoints', path: checkpointsPath, checkpointCount: 1, applied: apply });
    if (apply) writeText(checkpointsPath, JSON.stringify(syntheticCheckpoint));
  }

  const staleMinutes = deriveStaleMinutes(mutableRunState, summary);
  if (mutableRunState.status === 'active' && staleMinutes > STALE_RUN_TIMEOUT_MINUTES) {
    const resolvedAt = new Date().toISOString();
    actions.push({ type: 'stale_run_closed', path: runStatePath, staleMinutes, applied: apply });
    if (apply) {
      mutableRunState = {
        ...mutableRunState,
        originalStatus: mutableRunState.originalStatus || mutableRunState.status,
        status: 'failed',
        endedAt: mutableRunState.endedAt || resolvedAt,
        autoResolvedAt: resolvedAt,
        failureDomain: mutableRunState.failureDomain || 'harness',
        failureCode: mutableRunState.failureCode || 'stale_active',
        resolutionNote: mutableRunState.resolutionNote || `Auto-closed stale active run after ${staleMinutes} minutes without progress.`,
      };
    }
  }

  if (apply && JSON.stringify(mutableRunState) !== JSON.stringify(runState)) {
    writeJson(runStatePath, mutableRunState);
  }

  const normalizedStatus = mutableRunState.status === 'delivered' ? 'completed' : mutableRunState.status;
  const deliveredLike = normalizedStatus === 'completed' || summary?.finalOutcome === 'delivered' || mutableRunState.evalGrade === 'PASS';
  const deliveryPath = path.join(runDir, 'delivery.json');
  if (deliveredLike && !fs.existsSync(deliveryPath)) {
    const delivery = deriveDelivery(runDir, mutableRunState, summary);
    actions.push({ type: 'delivery', path: deliveryPath, deliveredAt: delivery.deliveredAt, applied: apply });
    if (apply) writeJson(deliveryPath, delivery);
  }

  return { runId, actions };
}

function renderText(report) {
  return [
    '# Harness Artifact Remediation',
    '',
    `Runs dir: ${report.runsDir}`,
    `Apply mode: ${report.apply}`,
    `Runs scanned: ${report.runsScanned}`,
    `Runs touched: ${report.runsTouched}`,
    `Plans repaired: ${report.plansRepaired}`,
    `Contracts repaired: ${report.contractsRepaired}`,
    `Checkpoints repaired: ${report.checkpointsRepaired}`,
    `Deliveries repaired: ${report.deliveriesRepaired}`,
    `Stale runs closed: ${report.staleRunsClosed}`,
  ].join('\n');
}

const args = parseArgs(process.argv.slice(2));
const runsDir = path.resolve(args.runsDir ?? defaultRunsDir());
const runDirs = fs.existsSync(runsDir)
  ? fs.readdirSync(runsDir).map((entry) => path.join(runsDir, entry)).filter((entry) => {
      try { return fs.statSync(entry).isDirectory(); } catch { return false; }
    })
  : [];

const touched = [];
let plansRepaired = 0;
let contractsRepaired = 0;
let checkpointsRepaired = 0;
let deliveriesRepaired = 0;
let staleRunsClosed = 0;
for (const runDir of runDirs) {
  const result = remediateRun(runDir, args.apply);
  if (!result || result.actions.length === 0) continue;
  touched.push(result);
  for (const action of result.actions) {
    if (action.type === 'plan') plansRepaired += 1;
    if (action.type === 'contract') contractsRepaired += 1;
    if (action.type === 'checkpoints') checkpointsRepaired += 1;
    if (action.type === 'delivery') deliveriesRepaired += 1;
    if (action.type === 'stale_run_closed') staleRunsClosed += 1;
  }
}

const report = {
  generatedAt: new Date().toISOString(),
  runsDir,
  apply: args.apply,
  runsScanned: runDirs.length,
  runsTouched: touched.length,
  plansRepaired,
  contractsRepaired,
  checkpointsRepaired,
  deliveriesRepaired,
  staleRunsClosed,
  touchedRuns: touched,
};

const output = args.json ? JSON.stringify(report, null, 2) : renderText(report);
if (args.out) {
  const outPath = path.resolve(args.out);
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, output + '\n');
}
process.stdout.write(output + '\n');
