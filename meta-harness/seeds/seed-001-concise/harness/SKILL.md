---
name: harness
description: >
  4-agent harness: Planner → Generator → Adversary → Evaluator.
  Concise variant — minimal prompts, same architecture.
---

# Harness — Concise Variant

4-agent pipeline for quality-driven development. Each agent has a focused, minimal prompt.

## When to use

- Implementing features, bug fixes, refactors
- Tasks touching >2 files or >1 feature
- Tasks where quality verification matters

Skip for: trivial one-line fixes, pure research, user says "quick" or "just do it".

## Workflow

```
PLAN → BUILD → CHALLENGE → EVAL → DONE? → deliver / retry / escalate
```

## Agents

| Phase | Agent | Model | Timeout | Thinking |
|-------|-------|-------|---------|----------|
| Plan | Planner | sonnet-class | 25 min | OFF |
| Build | Generator | opus-class | 45 min | OFF |
| Challenge | Adversary | different family | 15 min | OFF |
| Eval | Evaluator | sonnet/opus | 20 min | OFF |

## Loop Control

After each EVAL:
- All DoD PASS → DONE ✅
- Progress made → continue BUILD R(n+1)
- Same items stuck → ESCALATE to owner
- Elapsed > 30min → TIMEOUT, escalate

## Sprint Mode

If plan has >8 features: auto-split into sprints (3-5 features each).
Each sprint: BUILD→CHALLENGE→EVAL cycle. Context handoff between sprints (2-3 sentences per completed sprint).
Integration eval after >2 sprints.
