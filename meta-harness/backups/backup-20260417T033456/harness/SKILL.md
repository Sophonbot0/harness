---
name: harness
description: >
  Deep-Planner: Planner produces richer DoD (5/feature + 2 mandatory negative requirements per feature).
  Adversary skips already-covered negatives and goes deeper. Same evaluator as cand-0006.
  Parent: cand-0006 (focused-adversary). Hypothesis: more DoD at planning time = higher composite.
---

# Harness — Deep-Planner Variant

Planner generates richer specifications with mandatory negative requirements (Must-NOT items).

## Workflow
```
PLAN(deep + negatives) → BUILD → CHALLENGE(edge-focused, skip covered) → EVAL(zero-tolerance + bonus) → done/retry/escalate
```

## Key properties
- Planner: max 5 DoD/feature + 2 mandatory Must-NOT items per feature
- Generator: same as cand-0006
- Adversary: same as cand-0006 but skips already-covered negatives, goes deeper
- Evaluator: same as cand-0006 (zero-tolerance + bonus checks)
- Max 3 retry rounds

## Agents

| Phase | Agent | Model | Timeout | Thinking |
|-------|-------|-------|---------|----------|
| Plan | Planner | sonnet-class | 25 min | OFF |
| Build | Generator | opus-class | 40 min | OFF |
| Challenge | Adversary | different family | 12 min | OFF |
| Eval | Evaluator | sonnet/opus | 22 min | OFF |

## Loop Control
- All DoD PASS → DONE ✅
- Progress made → continue (up to 3 rounds)
- No progress after 2 rounds on same item → ESCALATE
- Elapsed > 35min → TIMEOUT, escalate with full state
