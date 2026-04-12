---
name: harness
description: >
  Verify-First: Every DoD item carries an explicit verify command. Generator self-verifies
  before declaring done. Evaluator fast-tracks pre-verified items (spot-checks 30%).
  Parent: cand-0006 (focused-adversary). Hypothesis: tighter verify loop = higher eval_grade + better DoD/test ratio.
---

# Harness — Verify-First Variant

DoD items embed verify commands. Generator self-verifies. Evaluator fast-tracks trusted checks.

## Workflow
```
PLAN(verify-embedded) → BUILD(self-verify) → CHALLENGE(edge-focused) → EVAL(fast-track + spot-check) → done/retry/escalate
```

## Key properties
- Planner embeds verify commands in every DoD item
- Generator runs verify commands after each feature, pastes evidence
- Adversary: same as cand-0006 (edge-focused, max 6 MAJOR+, suggests missing DoD)
- Evaluator: fast-tracks generator-verified items (spot-checks 30%), full-checks the rest
- Max 3 retry rounds

## Agents

| Phase | Agent | Model | Timeout | Thinking |
|-------|-------|-------|---------|----------|
| Plan | Planner | sonnet-class | 20 min | OFF |
| Build | Generator | opus-class | 45 min | OFF |
| Challenge | Adversary | different family | 12 min | OFF |
| Eval | Evaluator | sonnet/opus | 18 min | OFF |

## Loop Control
- All DoD PASS → DONE ✅
- Progress made → continue (up to 3 rounds)
- No progress after 2 rounds on same item → ESCALATE
- Elapsed > 35min → TIMEOUT, escalate with full state
