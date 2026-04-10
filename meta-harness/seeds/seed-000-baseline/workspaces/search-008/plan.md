# Plan: Make the Dashboard Faster

## Assumptions

The request "Make the dashboard faster" is intentionally vague. The following assumptions were made:

1. **What is the dashboard?** A Python data dashboard that loads records from a simulated database (in-memory list) and renders aggregated statistics (totals, averages, top items).
2. **What makes it slow?**
   - No caching: every refresh recomputes everything from scratch
   - Blocking I/O simulation (sleep) on data load
   - Full-scan aggregations over large datasets without early termination
   - No pagination: renders all N records at once
3. **What does "faster" mean?**
   - Reduced wall-clock load time (measured via benchmark)
   - Caching repeated identical queries
   - Lazy/paginated rendering (only compute the page needed)
   - At least 5× speedup on repeated calls
   - At least 2× speedup on cold first load

## Definition of Done

- [ ] `dashboard.py` — baseline slow dashboard (simulated DB load + full aggregation)
- [ ] `dashboard_optimized.py` — optimized version with LRU cache, lazy loading, pagination
- [ ] `benchmark.py` — measures wall-clock time for both versions, prints comparison table
- [ ] `test_dashboard.py` — pytest suite verifying:
    1. Optimized version returns same results as baseline
    2. Cached calls are faster than cold calls (≥5× speedup)
    3. Pagination returns correct subsets
    4. Cache invalidation works correctly
    5. Large dataset handled without error
- [ ] All tests pass: `/usr/bin/python3 -m pytest -v`
- [ ] `eval-report.md` and `scores.json` written

## File Layout

```
/tmp/dashboard-opt/
  plan.md
  dashboard.py
  dashboard_optimized.py
  benchmark.py
  test_dashboard.py
  challenge-report.md
  eval-report.md
  scores.json
```
