---
name: harness
description: >
  Fast-Strict Hybrid: fast's lean structure with strict's quality signals
  (coverage matrix, reproduction commands, zero-tolerance eval).
  Parents: seed-003-fast (frame) + seed-002-strict (signals).
---

# Harness — Fast-Strict Hybrid

Fast execution with strict quality gates. Lean prompts, strong verification.

## Workflow
```
PLAN(lean+matrix) → BUILD(batch) → CHALLENGE(quick+repro) → EVAL(zero-tolerance) → done/retry
```

## Key properties
- Planner: fast's no-questions + strict's requirement extraction & coverage matrix
- Generator: batch commit (from fast)
- Adversary: 5-issue cap (from fast) + reproduction commands (from strict)
- Evaluator: zero-tolerance (from strict) + concise feedback (from fast)
- Max 2 retry rounds (from fast)

## Agents

| Phase | Agent | Model | Timeout |
|-------|-------|-------|---------|
| Plan | Planner | sonnet-class | 15 min |
| Build | Generator | opus-class | 30 min |
| Challenge | Adversary | different family | 10 min |
| Eval | Evaluator | sonnet/opus | 15 min |

## Loop Control
- All DoD PASS → DONE ✅
- FAIL → retry (max 2 rounds total)
- Still failing after 2 → ESCALATE
- Elapsed > 25min → TIMEOUT
