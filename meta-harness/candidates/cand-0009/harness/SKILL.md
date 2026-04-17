---
name: harness
description: >
  Adaptive-Sentinel: Adds a sentinel phase between BUILD and CHALLENGE that pre-scans
  for common gap patterns and injects supplementary DoD items. Reduces retry rounds on
  hard tasks. Parent: cand-0008 (deep-planner). Hypothesis: pre-emptive gap detection = fewer retries.
---

# Harness — Adaptive-Sentinel Variant

5-phase pipeline with a sentinel pre-scan between build and adversary challenge.

## Workflow
```
PLAN(deep + negatives) → BUILD → SENTINEL(gap-scan) → CHALLENGE(edge-focused) → EVAL(zero-tolerance + bonus) → done/retry/escalate
```

## Key properties
- Planner: max 5 DoD/feature + 2 mandatory Must-NOT items per feature (same as cand-0008)
- Generator: same as cand-0008, reads sentinel-dod.md on retry
- Sentinel: NEW — static analysis for async gaps, validation gaps, resource leaks, type coercion
- Adversary: same as cand-0008, reads sentinel-dod.md to skip redundant challenges
- Evaluator: same as cand-0008 + bonus for first-round hard task completion
- Max 3 retry rounds

## Agents

| Phase | Agent | Model | Timeout | Thinking |
|-------|-------|-------|---------|----------|
| Plan | Planner | sonnet-class | 25 min | OFF |
| Build | Generator | opus-class | 40 min | OFF |
| Sentinel | Sentinel | sonnet-class | 5 min | OFF |
| Challenge | Adversary | different family | 12 min | OFF |
| Eval | Evaluator | sonnet/opus | 22 min | OFF |

## Loop Control
- All DoD + sentinel-DoD PASS → DONE ✅
- Progress made → continue (up to 3 rounds)
- No progress after 2 rounds on same item → ESCALATE
- Elapsed > 40min → TIMEOUT, escalate with full state
