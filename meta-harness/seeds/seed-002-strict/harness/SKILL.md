---
name: harness
description: >
  4-agent harness with strict adversary and zero-tolerance evaluator.
  Hypothesis: more aggressive challenge/eval catches more issues before delivery.
---

# Harness — Strict Variant

4-agent pipeline optimized for **maximum quality** at the cost of more rounds and longer evaluation.

## When to use
Same as baseline. This variant is for when correctness matters more than speed.

## Workflow
```
PLAN → BUILD → CHALLENGE(strict) → EVAL(strict) → DONE? → deliver / retry / escalate
```

## Key differences from baseline
- Adversary has 20 min (not 15) and up to 15 challenges (not 10)
- Adversary requires reproduction commands for every challenge
- Evaluator has zero-tolerance: 100% DoD or FAIL, no partial credit
- Evaluator must run adversary's "Demands for Evidence" explicitly
- Loop control is patient: allow up to 4 rounds before escalating

## Agents

| Phase | Agent | Model | Timeout | Thinking |
|-------|-------|-------|---------|----------|
| Plan | Planner | sonnet-class | 25 min | OFF |
| Build | Generator | opus-class | 45 min | OFF |
| Challenge | Adversary | different family | **20 min** | OFF |
| Eval | Evaluator | sonnet/opus | **25 min** | OFF |

## Loop Control
- All DoD PASS → DONE ✅
- Progress made → continue (up to 4 rounds)
- No progress after 2 rounds on same item → ESCALATE
- Elapsed > 45min → TIMEOUT, escalate with full state

## Sprint Mode
Same as baseline. Sprint support unchanged.
