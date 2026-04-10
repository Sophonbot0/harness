---
name: harness
description: >
  Strict-Lean: strict's quality signals (coverage matrix, zero-tolerance, reproduction commands)
  with reduced verbosity, fewer challenges, and no sprint overhead.
  Parent: seed-002-strict. Hypothesis: 60% token cost, same quality.
---

# Harness — Strict-Lean Variant

Strict's rigor at reduced cost. No sprints, fewer challenges, tighter prompts.

## Workflow
```
PLAN(lean) → BUILD → CHALLENGE(focused) → EVAL(zero-tolerance) → done/retry/escalate
```

## Key properties
- Planner extracts requirements + coverage matrix (from strict)
- No question-asking, no sprint splitting (from fast philosophy)
- Adversary: 12 min, max 8 challenges, reproduction commands required
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
