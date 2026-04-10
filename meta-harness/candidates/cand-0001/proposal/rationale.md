# Candidate 0001: Strict-Lean

## Parent: seed-002-strict

## Hypothesis
Strict's quality comes from 3 key mechanisms: (1) requirement extraction with coverage matrix, (2) zero-tolerance eval, (3) adversary reproduction commands. Its *cost* comes from verbosity: long instructional prose, 15-challenge cap, 20-min adversary budget, sprint-splitting logic that inflates DoD on complex tasks.

**We can keep the quality signals and cut the fat.**

## Changes from parent

### Planner
- Keep: requirement extraction technique, coverage matrix, completeness check
- Cut: sprint-splitting logic entirely (fast proved single-cycle works for these tasks)
- Cut: question-asking phase (fast proved assumptions work fine)
- Reduce: max 5 features (from unbounded), max 4 DoD per feature (from ~5+)
- Net: ~40% shorter prompt, same rigor in requirements

### Generator
- Keep: feature-by-feature implementation, test after each feature
- Cut: verbose principles section — distill to 3 rules
- Net: ~50% shorter prompt

### Adversary
- Keep: reproduction commands (strict's key differentiator), severity classification
- Cut: 15→8 max challenges, 20→12 min budget
- Cut: verbose adversarial input checklist — trust the model knows edge cases
- Keep: "Demands for Evidence" but cap at 5 (from 8+)
- Net: ~40% shorter, still thorough

### Evaluator
- Keep: zero-tolerance policy, progress delta tracking
- Cut: verbose process steps — the model knows how to evaluate
- Net: ~35% shorter

### SKILL.md
- Reduce max rounds from 4→3
- Reduce timeouts across the board
- Keep zero-tolerance pass criteria

## Expected outcome
- DoD quality: ~90-100 items (vs strict's 118) — still 1.5x fast's 63
- Test count: ~280-320 (vs strict's 364)
- Token cost: ~60% of strict
- Pass rate: 100% (no reason to regress)
