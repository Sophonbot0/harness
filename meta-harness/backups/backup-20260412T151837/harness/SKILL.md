---
name: harness
description: >
  Focused-Adversary: strict-lean base with adversary rewritten to target only
  edge cases, untested paths, and security. Skip basic checks (evaluator handles those).
  Adversary suggests missing DoD items. Evaluator runs bonus checks.
  Parent: cand-0001 (strict-lean). Hypothesis: deeper adversary analysis = higher quality.
---

# Harness — Focused-Adversary Variant

Same strict-lean base, but adversary goes deep on hard bugs instead of wide on all bugs.

## Workflow
```
PLAN(lean) → BUILD → CHALLENGE(edge-focused) → EVAL(zero-tolerance + bonus) → done/retry/escalate
```

## Key properties
- Planner extracts requirements + coverage matrix (from strict-lean)
- No question-asking, no sprint splitting
- Adversary: 12 min, max 6 challenges (MAJOR+ only), suggests missing DoD items
- Evaluator: zero-tolerance (100% DoD or FAIL) + bonus checks from adversary suggestions
- Max 3 retry rounds

## Agents

| Phase | Agent | Model | Timeout | Thinking |
|-------|-------|-------|---------|----------|
| Plan | Planner | sonnet-class | 20 min | OFF |
| Build | Generator | opus-class | 40 min | OFF |
| Challenge | Adversary | different family | 12 min | OFF |
| Eval | Evaluator | sonnet/opus | 22 min | OFF |

## Loop Control
- All DoD PASS → DONE ✅
- Progress made → continue (up to 3 rounds)
- No progress after 2 rounds on same item → ESCALATE
- Elapsed > 35min → TIMEOUT, escalate with full state
