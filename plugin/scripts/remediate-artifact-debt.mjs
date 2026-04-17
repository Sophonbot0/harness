#!/usr/bin/env node
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

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
  return extractCheckboxItems(planMd);
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

function remediateRun(runDir, apply) {
  const runId = path.basename(runDir);
  const runStatePath = path.join(runDir, 'run-state.json');
  const runState = readJson(runStatePath);
  if (!runState) return null;
  const summary = readJson(path.join(runDir, 'run-summary.json'));

  const actions = [];
  const contractPath = path.join(runDir, 'contract.json');
  if (!fs.existsSync(contractPath)) {
    const contract = deriveContract(runDir, runState);
    if (contract.length > 0) {
      actions.push({ type: 'contract', path: contractPath, itemCount: contract.length, applied: apply });
      if (apply) writeJson(contractPath, contract);
    }
  }

  const normalizedStatus = runState.status === 'delivered' ? 'completed' : runState.status;
  const deliveredLike = normalizedStatus === 'completed' || summary?.finalOutcome === 'delivered' || runState.evalGrade === 'PASS';
  const deliveryPath = path.join(runDir, 'delivery.json');
  if (deliveredLike && !fs.existsSync(deliveryPath)) {
    const delivery = deriveDelivery(runDir, runState, summary);
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
    `Contracts repaired: ${report.contractsRepaired}`,
    `Deliveries repaired: ${report.deliveriesRepaired}`,
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
let contractsRepaired = 0;
let deliveriesRepaired = 0;
for (const runDir of runDirs) {
  const result = remediateRun(runDir, args.apply);
  if (!result || result.actions.length === 0) continue;
  touched.push(result);
  for (const action of result.actions) {
    if (action.type === 'contract') contractsRepaired += 1;
    if (action.type === 'delivery') deliveriesRepaired += 1;
  }
}

const report = {
  generatedAt: new Date().toISOString(),
  runsDir,
  apply: args.apply,
  runsScanned: runDirs.length,
  runsTouched: touched.length,
  contractsRepaired,
  deliveriesRepaired,
  touchedRuns: touched,
};

const output = args.json ? JSON.stringify(report, null, 2) : renderText(report);
if (args.out) {
  const outPath = path.resolve(args.out);
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, output + '\n');
}
process.stdout.write(output + '\n');
