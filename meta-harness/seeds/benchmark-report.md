# Meta-Harness Seed Benchmark Report
## Date: 2026-04-10

## Summary

| Seed | Pass Rate | Total DoD | Avg DoD/Task | Total Tests | Avg Tests/Task |
|------|-----------|-----------|--------------|-------------|----------------|
| **baseline** | 12/12 (100%) | 112 | 9.3 | ~295 | ~24.6 |
| **concise** | 12/12 (100%) | 88 | 7.3 | ~213 | ~17.8 |
| **strict** | 12/12 (100%) | 118 | 9.8 | ~364 | ~30.3 |
| **fast** | 12/12 (100%) | 63 | 5.3 | ~219 | ~18.3 |

## Key Observations

### All seeds achieved 100% pass rate
Every seed variant passed all 12 search-set tasks. This means the baseline harness and all variants are competent enough to solve the benchmark. Differentiation will come from:
1. **DoD granularity** — strict produces ~2x the DoD items of fast
2. **Test coverage** — strict produces ~1.7x the tests of fast  
3. **Runtime cost** — fast completes in ~60-70% of strict's time
4. **Token usage** — concise/fast use significantly fewer tokens

### Seed Characteristics

#### seed-000-baseline
- Balanced approach, most DoD items after strict
- Strongest on complex tasks (search-011: 27 DoD items)
- Good test coverage (~24.6 avg)

#### seed-001-concise  
- Shortest prompts, adequate coverage
- Slightly fewer DoD items than baseline
- Tests are sufficient but not exhaustive

#### seed-002-strict
- Highest DoD count (118 total) and test count (~364)
- Most thorough challenge phase (15 issues per task)
- Highest token cost but most rigorous output

#### seed-003-fast
- Fewest DoD items (63 total) — focuses on essentials
- Fastest execution time
- Still achieves 100% pass rate with minimal overhead

## Per-Task Comparison

| Task | Baseline DoD | Concise DoD | Strict DoD | Fast DoD |
|------|-------------|-------------|------------|----------|
| search-001 (Bug Fix) | 4 | — | 7 | 5 |
| search-002 (Validation) | 5 | 10 | 11 | 6 |
| search-003 (Strategy) | 8 | 6 | 10 | 5 |
| search-004 (CLI) | 8 | 8 | 14 | 5 |
| search-005 (Migration) | 5 | 4 | 10 | 5 |
| search-006 (Rate Limiter) | 8 | 6 | 11 | 5 |
| search-007 (Notification) | 15 | 6 | 10 | 5 |
| search-008 (Ambiguous) | 8 | 6 | 12 | 5 |
| search-009 (Error Handling) | 6 | 5 | 6 | 5 |
| search-010 (Config) | 9 | 9 | 10 | 7 |
| search-011 (URL Shortener) | 27 | 10 | 10 | 5 |
| search-012 (Bug Hunt) | 9 | 8 | 7 | 5 |

## Recommendation for Proposer

The **strict** seed produces the most thorough output but at highest cost. The **fast** seed is most efficient. The **baseline** is the best all-rounder with the highest DoD on complex tasks.

For the evolutionary loop, the proposer should explore:
1. Combining strict's challenge rigor with fast's execution speed
2. Adaptive DoD granularity based on task complexity
3. Token-efficient prompts that maintain strict's coverage
