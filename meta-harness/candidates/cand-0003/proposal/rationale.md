# cand-0003: tdd-lean — Rationale

## Parent: cand-0001 (strict-lean, composite 0.945)

## Hypothesis
TDD-style generation catches edge cases during build, reducing dependence on the adversary phase. Combined with tighter DoD caps (3/feature) and a lighter adversary (6 challenges, 8 min), this should maintain or improve DoD quality while cutting cycle time.

## What changes and why

### 1. Generator → TDD mode
The comparison report shows cand-0001 produces 18.3 tests/task — decent but not exceptional. By forcing the generator to write tests FIRST for each DoD criterion before implementing, we expect:
- Higher test relevance (tests directly map to DoD)
- Earlier edge case discovery (no need to wait for adversary)
- Fewer "tests that pass but test the wrong thing" (adversary CRITICAL category)

### 2. Adversary reduction (8→6 challenges, 12→8 min)
The report suggests the adversary "may be over-contributing" at 12min/8 challenges. If TDD catches more issues upfront, the adversary becomes a lighter sanity check rather than the primary quality gate. This is a controlled experiment: if DoD drops, we know the adversary was still needed.

### 3. Planner DoD cap: 4→3 per feature
cand-0001 achieved 15.1 DoD/task avg. With 5 features × 4 DoD = 20 max, many features used all 4. Capping at 3 forces sharper prioritization — each DoD item must be more meaningful. If total DoD stays ≥13/task, we've improved signal density.

## Risks
- TDD may increase generator time (writing tests first adds overhead)
- Reduced adversary may miss issues TDD doesn't catch (concurrency, integration)
- DoD cap reduction could lower absolute numbers without improving quality

## Success criteria
- Pass rate: 100%
- Avg DoD/task: ≥13
- Zero retries
- Cycle time ≤ cand-0001
