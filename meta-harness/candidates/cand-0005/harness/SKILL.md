---
name: harness
description: >
  TDD-Crossover: combines TDD generator (tests-first) from cand-0003 with
  cand-0001's full adversary (8 challenges, 12 min). DoD cap restored to 4/feature.
  Parent: cand-0001 (strict-lean). Hypothesis: TDD + full adversary = best of both.
---

# Harness — TDD-Crossover Variant

TDD generator catches bugs early; full adversary catches design issues. Best of both parents.

## Workflow
```
PLAN(lean) → BUILD(TDD) → CHALLENGE(full) → EVAL(zero-tolerance) → done/retry/escalate
```

## Key properties
- Planner extracts requirements + coverage matrix, 4 DoD/feature cap
- Generator uses TDD: failing tests first, then implement, then refactor
- Adversary: 12 min, max 8 challenges, reproduction commands + demands-for-evidence
- Evaluator: zero-tolerance (100% DoD or FAIL)
- Max 3 retry rounds

## Agents

| Phase | Agent | Model | Timeout | Thinking |
|-------|-------|-------|---------|----------|
| Plan | Planner | sonnet-class | 20 min | OFF |
| Build | Generator | opus-class | 40 min | OFF |
| Challenge | Adversary | different family | 12 min | OFF |
| Eval | Evaluator | sonnet/opus | 20 min | OFF |

## Loop Control
- All DoD PASS → DONE ✅
- Progress made → continue (up to 3 rounds)
- No progress after 2 rounds on same item → ESCALATE
- Elapsed > 35min → TIMEOUT, escalate with full state
