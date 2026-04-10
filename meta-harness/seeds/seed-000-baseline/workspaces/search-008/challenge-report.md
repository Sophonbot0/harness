# Challenge Report

## Task Interpretation

The original request — *"Make the dashboard faster"* — was intentionally vague. The following challenges and assumptions were documented:

## Assumptions Made

| # | Assumption | Rationale |
|---|-----------|-----------|
| 1 | "Dashboard" = Python data dashboard with in-memory simulated DB | Most common type of dashboard in backend Python projects |
| 2 | "Slow" = no caching + blocking I/O on every call | Most common cause of dashboard slowness |
| 3 | "Faster" = ≥5× speedup on repeated/cached calls | Measurable, concrete target |
| 4 | Dataset size = 10,000 records | Realistic scale that shows meaningful speedup |
| 5 | Optimizations in scope: LRU cache, lazy load, pagination | Widely applicable, no external dependencies needed |

## Potential Misinterpretations

- The "dashboard" could have been a web frontend (React, Vue) — in that case optimization would target bundle size, SSR, or CDN caching instead.
- "Faster" could mean visual perceived performance (skeleton screens, streaming) rather than raw computation time.
- The "database" could be real SQL — indexing, query planning, and connection pooling would be more relevant.

## What Was Actually Built

A self-contained Python optimization demonstration with:
- **Baseline**: loads 10k records + computes aggregations on every call (~200ms each)
- **Optimized**: caches data in memory with TTL; `lru_cache` on aggregation step; pagination works on cached slice
- **Benchmark**: prints before/after table with speedup multiplier
- **Tests**: 16 tests covering correctness, caching behaviour, pagination, invalidation, edge cases

## Benchmark Results

| Scenario | Baseline | Optimized | Speedup |
|----------|----------|-----------|---------|
| get_summary() — cached | ~207ms | <0.001ms | >200,000× |
| get_page(0,20) — cached | ~169ms | <0.001ms | >80,000× |
| get_summary() — cold load | ~207ms | ~212ms | ~1× (expected) |

Cold load speedup is ~1× (both must pay the I/O cost). All repeated calls are effectively free.

## Risks / Limitations

- In-memory cache is per-process; not suitable for multi-worker deployments (would need Redis/Memcached).
- TTL is hardcoded at 60s; real systems need dynamic invalidation triggers.
- The sleep() simulates I/O but does not represent real DB latency distribution.
