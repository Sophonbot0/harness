# Candidate 0002: Fast-Strict Hybrid

## Parents: seed-003-fast (structure) + seed-002-strict (quality signals)

## Hypothesis
Fast's prompts are ~80% shorter than strict's, yet fast still gets 100% pass rate and 18.3 tests/task. The base model is strong — it doesn't need verbose instructions. What fast *lacks* is strict's quality scaffolding: requirement extraction, coverage matrix, reproduction commands, zero-tolerance eval.

**Inject strict's 3 key quality signals into fast's lean frame.**

## Changes from fast

### Planner
- Keep: fast's no-questions, max-5-features structure
- Add: requirement extraction step (numbered list from user request)
- Add: lightweight coverage matrix (requirement → feature mapping)
- Increase: max 4 DoD per feature (from 3) — one extra for edge cases
- Net: ~2x fast's planner but still ~40% of strict's

### Generator
- Keep: fast's batch implementation (one commit)
- Add: "read eval-report.md on round >1" with explicit fix protocol
- Net: ~1.5x fast's generator, still very lean

### Adversary
- Keep: fast's 5-issue cap and 10-min budget
- Add: reproduction command requirement for every issue (strict's key signal)
- Add: "Demands for Evidence" — 3 specific tests evaluator must run
- Net: ~2x fast's adversary, still ~40% of strict's

### Evaluator
- Keep: fast's concise structure
- Add: zero-tolerance policy (strict's core: 100% DoD or FAIL, no partial credit)
- Add: progress delta on round >1
- Keep: top-3-fixes feedback constraint (prevents eval bloat)
- Net: ~2x fast's evaluator, still ~35% of strict's

### SKILL.md
- Keep: fast's timeouts and 2-round max
- Add: zero-tolerance pass criteria from strict
- Keep: no sprint support

## Expected outcome
- DoD quality: ~75-90 items (midpoint between fast's 63 and strict's 118)
- Test count: ~230-280
- Token cost: ~70% of strict, ~130% of fast
- Pass rate: 100%
- Key bet: the coverage matrix and zero-tolerance eval will push DoD quality up without needing strict's verbose prompts
