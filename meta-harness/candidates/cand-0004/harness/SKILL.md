---
name: harness
description: >
  Eval-Only: No adversary phase. Evaluator absorbs edge-case probing + zero-tolerance verification.
  Parent: cand-0001 (strict-lean). Hypothesis: adversary is redundant with a strong evaluator.
---

# Harness — Eval-Only Variant

Three-phase pipeline. No adversary — the evaluator IS the quality gate.

## Workflow
```
PLAN(lean) → BUILD → EVAL(comprehensive) → done/retry/escalate
```

## Key properties
- Planner extracts requirements + coverage matrix (from strict-lean)
- No adversary phase — evaluator handles edge-case probing
- Evaluator: zero-tolerance + structured edge-case audit (25 min)
- Max 3 retry rounds

## Agents

| Phase | Agent | Model | Timeout | Thinking |
|-------|-------|-------|---------|----------|
| Plan | Planner | sonnet-class | 20 min | OFF |
| Build | Generator | opus-class | 40 min | OFF |
| Eval | Evaluator | sonnet/opus | 25 min | OFF |

## Loop Control
- All DoD PASS + edge-case audit clean → DONE ✅
- Progress made → continue (up to 3 rounds)
- No progress after 2 rounds on same item → ESCALATE
- Elapsed > 35min → TIMEOUT, escalate with full state
