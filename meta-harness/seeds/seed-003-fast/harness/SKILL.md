---
name: harness
description: >
  4-agent harness optimized for speed. Shorter prompts, shorter timeouts, no sprints.
  Hypothesis: for most tasks, speed matters more than exhaustive checking.
---

# Harness — Fast Variant

Optimized for fast delivery. Single-cycle execution, minimal overhead.

## When to use
Same triggers as baseline. This variant prioritizes speed.

## Workflow
```
PLAN(fast) → BUILD(batch) → CHALLENGE(quick) → EVAL(quick) → done/retry
```

## Key differences from baseline
- Planner never asks questions — makes assumptions
- Generator commits once (not per-feature)
- Adversary: 10 min, max 5 issues
- Evaluator: concise, top 3 fixes only
- No sprint support — always single cycle
- Max 2 retry rounds, then escalate

## Agents

| Phase | Agent | Model | Timeout |
|-------|-------|-------|---------|
| Plan | Planner | sonnet-class | 15 min |
| Build | Generator | opus-class | 30 min |
| Challenge | Adversary | different family | 10 min |
| Eval | Evaluator | sonnet/opus | 10 min |

## Loop Control
- All DoD PASS → DONE ✅
- FAIL → retry once (max 2 rounds total)
- Still failing after 2 rounds → ESCALATE
- Elapsed > 20min → TIMEOUT
