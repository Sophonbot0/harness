# Meta-Harness Iteration 2 — Comparison Report
## Date: 2026-04-10
## Parent: cand-0001 (strict-lean) — promoted from iteration 1

---

## Candidates

| | **cand-0003: tdd-lean** | **cand-0004: eval-only** |
|---|---|---|
| **Parent** | cand-0001 (strict-lean) | cand-0001 (strict-lean) |
| **Iteration** | 2 | 2 |
| **Hypothesis** | TDD-style generator (tests-first) + reduced adversary (6 challenges). Tests-first should catch edge cases earlier, reducing adversary's value. | Remove adversary entirely. Merge challenge duties into strengthened evaluator. If quality holds, adversary is pure overhead. |
| **Key Change** | Generator rewritten for TDD flow; adversary reduced 8→6 challenges | Adversary removed; evaluator expanded with edge-case audit |
| **Pass Rate** | **12/12 (100%)** | **12/12 (100%)** |
| **Retries** | 0 | 0 |

---

## Per-Task Results

### cand-0003 (tdd-lean)

| Task | Grade | DoD | Tests | Challenges | Notes |
|------|-------|-----|-------|------------|-------|
| search-001 | PASS | 10/10 | 10/10 | 6/6 | Sort bug fix — TDD confirmed |
| search-002 | PASS | 15/15 | 21/21 | 6/6 | REST API validation |
| search-003 | PASS | 15/15 | 22/22 | 6/6 | Strategy pattern refactor |
| search-004 | A | 5/5 | 18/18 | 6/6 | CLI tool — low DoD granularity |
| search-005 | A+ | 15/15 | 14/14 | 6/6 | DB migration |
| search-006 | A+ | 15/15 | 17/17 | 6/6 | Rate limiter middleware |
| search-007 | A | 15/15 | 16/16 | 6/6 | Notification system |
| search-008 | A+ | 15/15 | 23/23 | 6/6 | Dashboard perf (ambiguous task) |
| search-009 | A+ | 15/15 | 32/32 | 6/6 | Error handling overhaul |
| search-010 | A+ | 15/15 | 30/30 | 6/6 | Config system |
| search-011 | A+ | 15/15 | 19/19 | 6/6 | URL shortener |
| search-012 | A+ | 15/15 | 29/29 | 6/6 | Bug hunt (5 bugs) |
| **TOTAL** | **12/12** | **165** | **251** | **72/72** | |

### cand-0004 (eval-only)

| Task | Grade | DoD | Tests | Challenges | Notes |
|------|-------|-----|-------|------------|-------|
| search-001 | A | 15/15 | 16/16 | N/A | Sort bug fix |
| search-002 | A+ | 10/10 | 31/31 | N/A | REST API validation — fewer DoD |
| search-003 | A+ | 15/15 | 73/73 | N/A | Strategy pattern — 73 tests! |
| search-004 | A+ | 14/14 | 31/31 | N/A | CLI tool |
| search-005 | A+ | 12/12 | 9/9 | N/A | DB migration — few tests |
| search-006 | A | 13/13 | 19/19 | N/A | Rate limiter |
| search-007 | PASS | 15/15 | 42/42 | N/A | Notification system |
| search-008 | A+ | 15/15 | 46/46 | N/A | Dashboard perf |
| search-009 | A+ | 15/15 | 41/41 | N/A | Error handling |
| search-010 | A+ | 15/15 | 44/44 | N/A | Config system |
| search-011 | A+ | 15/15 | 23/23 | N/A | URL shortener |
| search-012 | A+ | 15/15 | 21/21 | N/A | Bug hunt (5 bugs) |
| **TOTAL** | **12/12** | **169** | **396** | **N/A** | |

---

## Aggregate Comparison — All Iterations

| Variant | Iter | Pass Rate | Total DoD | Avg DoD/Task | Total Tests | Avg Tests/Task | DoD/Test Ratio | Retries | Challenges |
|---------|------|-----------|-----------|--------------|-------------|----------------|----------------|---------|------------|
| seed-000-baseline | 0 | 12/12 | 136 | 11.3 | ~295 | ~24.6 | 0.46 | 0 | — |
| seed-001-concise | 0 | 12/12 | 88 | 7.3 | ~213 | ~17.8 | 0.41 | 0 | — |
| seed-002-strict | 0 | 12/12 | 118 | 9.8 | ~364 | ~30.3 | 0.32 | 0 | — |
| seed-003-fast | 0 | 12/12 | 63 | 5.3 | ~219 | ~18.3 | 0.29 | 0 | — |
| **cand-0001 strict-lean** | 1 | 12/12 | 181 | 15.1 | 220 | 18.3 | **0.82** | 0 | ✓ |
| cand-0002 fast-strict | 1 | 12/12 | 171 | 14.3 | 218 | 18.2 | 0.78 | 1 | ✓ |
| **cand-0003 tdd-lean** | **2** | **12/12** | **165** | **13.8** | **251** | **20.9** | **0.66** | **0** | **72/72** |
| **cand-0004 eval-only** | **2** | **12/12** | **169** | **14.1** | **396** | **33.0** | **0.43** | **0** | **N/A** |

---

## Analysis

### 1. Neither iteration-2 candidate beats the current baseline (cand-0001)

| Metric | cand-0001 (baseline) | cand-0003 (tdd-lean) | cand-0004 (eval-only) |
|--------|---------------------|---------------------|----------------------|
| Total DoD | **181** | 165 (−9%) | 169 (−7%) |
| Avg DoD/task | **15.1** | 13.8 | 14.1 |
| Total Tests | 220 | 251 (+14%) | **396 (+80%)** |
| DoD/Test ratio | **0.82** | 0.66 | 0.43 |
| Retries | 0 | 0 | 0 |
| Challenges | ✓ | 72/72 | N/A |

**cand-0001 remains the best variant** with the highest DoD granularity (181), best efficiency ratio (0.82), and zero retries.

### 2. TDD Hypothesis (cand-0003): Partially confirmed, not an improvement

- TDD flow works — confirmed by failing→passing test transitions
- Challenge coverage perfect (72/72)
- But DoD granularity dropped slightly (165 vs 181) — the 3 DoD/feature cap may be too aggressive
- Test count rose modestly (251 vs 220) — TDD generates more tests than expected
- search-004 had anomalously low DoD (5) — the cap bit too hard on this task

**Verdict: KEEP for diversity but don't promote.** The TDD pattern is worth preserving as a variant.

### 3. Eval-Only Hypothesis (cand-0004): Adversary removable, but evaluator overcompensates with tests

- Quality held perfectly — 100% pass, zero retries, solid DoD (169)
- But test count exploded (396!) — without adversary as separate reviewer, the evaluator-expanded generator writes ~80% more tests to compensate
- DoD slightly lower than baseline (169 vs 181)
- Highly variable test counts per task (9 for search-005 vs 73 for search-003) — less consistent

**Verdict: KEEP for efficiency experiments but don't promote.** The 3-phase workflow is faster in wall-clock time but wastes tokens on excessive tests.

### 4. Key Insight: The adversary-generator separation matters

The iteration-1 insight holds: having a **separate adversary** that challenges the work (but doesn't generate tests) keeps the generator disciplined without token bloat. When the adversary is removed (cand-0004), the generator/evaluator overcompensate with tests. When the adversary is over-reduced (cand-0003), DoD precision drops slightly.

cand-0001's balance — moderate adversary (8 challenges) + lean prompts + zero-tolerance evaluator — remains optimal.

---

## Promotion Decision

**KEEP cand-0001 (strict-lean) as active baseline.** Neither cand-0003 nor cand-0004 improves the composite score.

| Candidate | Action | Reason |
|-----------|--------|--------|
| cand-0003 (tdd-lean) | **KEEP** (not promoted) | DoD regression (−9%), higher test count. TDD variant preserved for future crossover. |
| cand-0004 (eval-only) | **KEEP** (not promoted) | DoD regression (−7%), test bloat (+80%). 3-phase workflow preserved for speed experiments. |

---

## Recommendations for Iteration 3

1. **Start from cand-0001** (still the best)
2. **Try increasing DoD cap back to 4/feature** (cand-0003's 3/feature was too restrictive)
3. **Experiment with adversary focus**: instead of reducing adversary, try making it more targeted (e.g., only challenge edge cases, not basic functionality)
4. **Crossover opportunity**: combine cand-0003's TDD generator with cand-0001's adversary — tests-first + quality review might synergize
5. **Add token tracking**: measure actual cost per candidate to compare efficiency beyond pass rates

---

## Raw Data

- Iteration 1 report: `comparison-report.md`
- Iteration 2 report: `iteration-2-report.md`
- cand-0003 scores: `/tmp/cand0003-search-*/scores.json`
- cand-0004 scores: `/tmp/cand0004-search-*/scores.json`
- Candidate metadata: `candidates/cand-000{3,4}/metadata.json`
- Promotion history: `promotions.jsonl`
