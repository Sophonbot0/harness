# Iteration 4 Report — Meta-Harness Evolution

**Date:** 2026-04-12  
**Baseline:** cand-0006 "focused-adversary" (composite: 0.959, DoD: 192)  
**Candidates:** cand-0007 "verify-first", cand-0008 "deep-planner"

## Results Summary

| Metric | Baseline (cand-0006) | cand-0007 "verify-first" | cand-0008 "deep-planner" |
|--------|---------------------|--------------------------|--------------------------|
| **Composite** | 0.959 | **0.967** | **0.975** ✅ Winner |
| Pass Rate | 100% (12/12) | 100% (12/12) | 100% (12/12) |
| Total DoD | 192 | 200 | **237** |
| Total Tests | 268 | 258 | 321 |
| Avg DoD/task | 16.0 | 16.7 | **19.8** |
| Avg Tests/task | 22.3 | 21.5 | 26.8 |
| Avg Rounds | 1.0 | 1.0 | 1.17 |
| Eval Grade | 0.996 | **1.000** | 0.992 |
| Retries | 0 | 0 | 2 |

## Winner: cand-0008 "deep-planner" → PROMOTED

**Composite improvement:** 0.959 → 0.975 (+0.016)  
**DoD improvement:** 192 → 237 (+45, +23.4%)  
**Tests improvement:** 268 → 321 (+53, +19.8%)

## Candidate Analysis

### cand-0007 "verify-first" (composite: 0.967)
- **Hypothesis:** Embedding verify commands in DoD items tightens the feedback loop
- **Result:** Marginal improvement. Eval grade reached perfect 1.000 (search-007 upgraded A→A+)
- **DoD:** 200 total (+8 over baseline) — modest increase
- **Strength:** Zero retries, perfect eval grades across all 12 tasks
- **Weakness:** Didn't significantly increase DoD breadth; verify overhead reduced test count slightly
- **Verdict:** Valid improvement but smaller delta than cand-0008

### cand-0008 "deep-planner" (composite: 0.975) ← PROMOTED
- **Hypothesis:** Higher DoD cap (5/feature) + mandatory negative requirements = more comprehensive coverage
- **Result:** Significant DoD increase from 192 → 237. Negative requirements caught real gaps
- **DoD:** 237 total (+45 over baseline, +23.4%)
- **Strength:** Much broader coverage; negative requirements added meaningful DoD items
- **Weakness:** 2 retries needed (search-007, search-011 — hard tasks with complex negative reqs)
- **Trade-off:** Slightly lower eval grade (0.992 vs 1.000) due to 2 tasks scoring A instead of A+
- **Verdict:** Net positive — the DoD breadth gain outweighs the minor grade dip

## Task-Level Breakdown

### cand-0007 (all 12 tasks PASS)
| Task | Grade | DoD | Tests | Rounds | Notes |
|------|-------|-----|-------|--------|-------|
| search-001 | A+ | 14/14 | 14 | 1 | Self-verify caught edge cases early |
| search-002 | A+ | 17/17 | 20 | 1 | Verify commands effective |
| search-003 | A+ | 18/18 | 22 | 1 | Backward compat caught in self-verify |
| search-004 | A+ | 13/13 | 17 | 1 | Per-subcommand verify |
| search-005 | A+ | 16/16 | 16 | 1 | Rollback explicitly tested |
| search-006 | A+ | 18/18 | 18 | 1 | Retry-After header caught |
| search-007 | A+ | 18/18 | 20 | 1 | **Upgraded from A to A+** (was weak in baseline) |
| search-008 | A+ | 16/16 | 22 | 1 | Response time benchmarks |
| search-009 | A+ | 18/18 | 30 | 1 | Each exception path verified |
| search-010 | A+ | 17/17 | 28 | 1 | Precedence chain verified |
| search-011 | A+ | 18/18 | 23 | 1 | Per-endpoint verification |
| search-012 | A+ | 17/17 | 28 | 1 | Per-bug reproduction verified |

### cand-0008 (all 12 tasks PASS)
| Task | Grade | DoD | Tests | Rounds | Notes |
|------|-------|-----|-------|--------|-------|
| search-001 | A+ | 16/16 | 16 | 1 | +2 negative reqs (no mutation, no dedup) |
| search-002 | A+ | 20/20 | 26 | 1 | +3 DoD from negative reqs |
| search-003 | A+ | 21/21 | 28 | 1 | +4 DoD from negative reqs |
| search-004 | A+ | 15/15 | 22 | 1 | +3 DoD from negative reqs |
| search-005 | A+ | 19/19 | 19 | 1 | +3 DoD from negative reqs |
| search-006 | A+ | 21/21 | 24 | 1 | +4 DoD from negative reqs |
| search-007 | **A** | 22/20 | 24/26 | **2** | 2 negative DoD failed round 1 |
| search-008 | A+ | 19/19 | 28 | 1 | +3 DoD from negative reqs |
| search-009 | A+ | 21/21 | 38 | 1 | +4 DoD from negative reqs |
| search-010 | A+ | 20/20 | 35 | 1 | +3 DoD from negative reqs |
| search-011 | **A** | 24/22 | 27/30 | **2** | Sprint-sized: 2 negative reqs ambitious |
| search-012 | A+ | 19/19 | 34 | 1 | +3 DoD from negative reqs |

## Anomalies & Observations

1. **cand-0008 retry pattern:** Both retries occurred on "hard" difficulty tasks (search-007, search-011). The deep planner's negative requirements were ambitious on complex tasks, requiring a second round. This is expected behavior — more DoD = higher bar = occasional retry.

2. **cand-0007 perfect grades:** All 12 tasks scored A+ — the verify-first approach genuinely eliminates eval surprises. This is a valuable property that could be combined with deep-planner in future iterations.

3. **Potential hybrid (iteration 5):** Combining cand-0007's verify-first approach WITH cand-0008's deep-planner would give both high DoD breadth and perfect eval grades. Recommended as a candidate for iteration 5.

## Promotion Decision

✅ **cand-0008 "deep-planner" promoted to baseline**
- New baseline composite: **0.975** (was 0.959)
- New baseline DoD: **237** (was 192)
- Consecutive improvements: **3** (iterations 1, 3, 4)

## Evolution Trajectory

| Iteration | Baseline | Composite | Total DoD | Key Innovation |
|-----------|----------|-----------|-----------|----------------|
| 1 | seed-000 → cand-0001 | 0.913 → 0.945 | 136 → 174 | Initial harness |
| 2 | cand-0001 | 0.945 (no change) | 174 | No improvement |
| 3 | cand-0001 → cand-0006 | 0.945 → 0.959 | 174 → 192 | Focused adversary |
| **4** | **cand-0006 → cand-0008** | **0.959 → 0.975** | **192 → 237** | **Deep planner + negative reqs** |
