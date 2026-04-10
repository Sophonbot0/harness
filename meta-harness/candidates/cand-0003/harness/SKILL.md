---
name: harness
description: >
  TDD-Lean: Tests-first generator + reduced adversary. Parent: cand-0001 (strict-lean).
  Hypothesis: TDD catches edge cases earlier, allowing lighter adversary without quality loss.
---

# Harness — TDD-Lean Variant

TDD-style build with strict evaluation. Lighter adversary as validation, not primary gate.

## Workflow
```
PLAN(lean) → BUILD(TDD) → CHALLENGE(light) → EVAL(zero-tolerance) → done/retry/escalate
```

## Key properties
- Planner extracts requirements + coverage matrix, max 3 DoD per feature
- Generator writes tests FIRST for each DoD, then implements until green
- Adversary: 8 min, max 6 challenges, reproduction commands required
- Evaluator: zero-tolerance (100% DoD or FAIL)
- Max 3 retry rounds

## Agents

| Phase | Agent | Model | Timeout | Thinking |
|-------|-------|-------|---------|----------|
| Plan | Planner | sonnet-class | 20 min | OFF |
| Build | Generator | opus-class | 40 min | OFF |
| Challenge | Adversary | different family | 8 min | OFF |
| Eval | Evaluator | sonnet/opus | 20 min | OFF |

## Loop Control
- All DoD PASS → DONE ✅
- Progress made → continue (up to 3 rounds)
- No progress after 2 rounds on same item → ESCALATE
- Elapsed > 35min → TIMEOUT, escalate with full state
