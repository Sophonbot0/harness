---
name: harness
description: >
  Trend-Oracle: Planner analyzes failure trend patterns from prior rounds to front-load
  preventive DoD items. Adversary uses a structured taxonomy (data-integrity, concurrency,
  boundary, type-safety) instead of ad-hoc probing. Evaluator tracks per-criterion confidence.
  Parent: cand-0008 (deep-planner). Hypothesis: structured adversary taxonomy + planner
  trend-awareness = fewer round-2 regressions on hard tasks.
---

# Harness — Trend-Oracle Variant

Planner front-loads failure-prone patterns. Adversary uses structured challenge taxonomy.

## Workflow
```
PLAN(deep + negatives + trend-aware) → BUILD → CHALLENGE(taxonomy-driven) → EVAL(confidence-tracked) → done/retry/escalate
```

## Key properties
- Planner: same as cand-0008 (5 DoD/feature + 2 Must-NOT) PLUS trend-awareness section
- Generator: same as cand-0008
- Adversary: structured taxonomy (4 categories, min 1 challenge per category)
- Evaluator: same as cand-0008 + per-criterion confidence score
- Max 3 retry rounds

## Agents

| Phase | Agent | Model | Timeout | Thinking |
|-------|-------|-------|---------|----------|
| Plan | Planner | sonnet-class | 25 min | OFF |
| Build | Generator | opus-class | 40 min | OFF |
| Challenge | Adversary | different family | 15 min | OFF |
| Eval | Evaluator | sonnet/opus | 22 min | OFF |

## Loop Control
- All DoD PASS → DONE ✅
- Progress made → continue (up to 3 rounds)
- No progress after 2 rounds on same item → ESCALATE
- Elapsed > 35min → TIMEOUT, escalate with full state
