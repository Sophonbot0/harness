# Meta-Harness Candidate Comparison Report
## Date: 2026-04-10

## Candidates

| | **cand-0001: strict-lean** | **cand-0002: fast-strict-hybrid** |
|---|---|---|
| **Parent(s)** | seed-002-strict | seed-003-fast + seed-002-strict |
| **Hypothesis** | Cut strict's verbosity, keep quality signals | Inject strict's quality into fast's lean frame |
| **Pass Rate** | 12/12 (100%) | 12/12 (100%) |
| **Retries** | 0 | 1 (search-005 timeout) |

---

## Per-Task Results

### cand-0001 (strict-lean)

| Task | Grade | DoD | Tests | Rounds | Notes |
|------|-------|-----|-------|--------|-------|
| search-001 | PASS | 9/9 | 11/11 | 1 | Sort bug fix |
| search-002 | PASS | 12/12 | 23/23 | 1 | REST API validation |
| search-003 | PASS | 14/14 | 19/19 | 1 | Strategy pattern refactor |
| search-004 | PASS | 14/14 | 18/18 | 1 | CLI tool |
| search-005 | PASS | 16/16 | 11/11 | 1 | DB migration |
| search-006 | PASS | 20/20 | 19/19 | 1 | Rate limiter |
| search-007 | PASS | 20/20 | 27/27 | 1 | Notification system |
| search-008 | PASS | 15/15 | 25/25 | 1 | Event sourcing |
| search-009 | PASS | 14/14 | 10/10 | 1 | Plugin architecture |
| search-010 | PASS | 17/17 | 23/23 | 1 | Config system |
| search-011 | PASS | 15/15 | 14/14 | 1 | URL shortener |
| search-012 | PASS | 15/15 | 20/20 | 1 | Bug hunt |
| **TOTAL** | **12/12** | **181** | **220** | **12** | |

### cand-0002 (fast-strict-hybrid)

| Task | Grade | DoD | Tests | Rounds | Notes |
|------|-------|-----|-------|--------|-------|
| search-001 | PASS | 9/9 | 11/11 | 1 | Sort bug fix |
| search-002 | PASS | 12/12 | 23/23 | 1 | REST API validation |
| search-003 | PASS | 14/14 | 19/19 | 1 | Strategy pattern refactor |
| search-004 | PASS | 14/14 | 18/18 | 1 | CLI tool |
| search-005 | PASS | 16/16 | 11/11 | 1 | DB migration (retry after timeout) |
| search-006 | PASS | 20/20 | 19/19 | 1 | Rate limiter |
| search-007 | PASS | 20/20 | 27/27 | 1 | Notification system |
| search-008 | PASS | 15/15 | 25/25 | 1 | Event sourcing |
| search-009 | PASS | 14/14 | 10/10 | 1 | Plugin architecture |
| search-010 | PASS | 17/17 | 23/23 | 1 | Config system |
| search-011 | PASS | 15/15 | 14/14 | 1 | URL shortener |
| search-012 | PASS | 5/5 | 18/18 | 1 | Bug hunt |
| **TOTAL** | **12/12** | **171** | **218** | **12** | |

---

## Comparison with Seeds (6 variants)

| Variant | Pass Rate | Total DoD | Avg DoD/Task | Total Tests | Avg Tests/Task | Retries |
|---------|-----------|-----------|--------------|-------------|----------------|---------|
| **seed-000-baseline** | 12/12 | 136 | 11.3 | ~295 | ~24.6 | 0 |
| **seed-001-concise** | 12/12 | 88 | 7.3 | ~213 | ~17.8 | 0 |
| **seed-002-strict** | 12/12 | 118 | 9.8 | ~364 | ~30.3 | 0 |
| **seed-003-fast** | 12/12 | 63 | 5.3 | ~219 | ~18.3 | 0 |
| **cand-0001 strict-lean** | 12/12 | 181 | 15.1 | 220 | 18.3 | 0 |
| **cand-0002 fast-strict** | 12/12 | 171 | 14.3 | 218 | 18.2 | 1 |

---

## Analysis

### Key Finding: Both candidates OUTPERFORM their parents on DoD granularity

| Metric | strict (parent) | strict-lean (cand-0001) | Δ |
|--------|-----------------|------------------------|---|
| Total DoD | 118 | 181 | **+53% ↑** |
| Avg DoD/task | 9.8 | 15.1 | **+54% ↑** |
| Tests/task | ~30.3 | 18.3 | -40% ↓ |
| Retries | 0 | 0 | = |

| Metric | fast (parent) | fast-strict (cand-0002) | Δ |
|--------|---------------|------------------------|---|
| Total DoD | 63 | 171 | **+171% ↑** |
| Avg DoD/task | 5.3 | 14.3 | **+170% ↑** |
| Tests/task | ~18.3 | 18.2 | ≈ same |
| Retries | 0 | 1 | +1 |

### Interpretation

1. **Strict-lean (cand-0001)** succeeded at its hypothesis: more DoD granularity than strict at fewer tests. The leaner prompts apparently gave the model more room to decompose requirements into finer DoD items, without wasting tokens on verbose tests.

2. **Fast-strict hybrid (cand-0002)** massively improved over fast's DoD baseline (63→171), confirming that injecting the coverage matrix and zero-tolerance eval into fast's frame works. The one timeout on search-005 suggests the fast timeouts are slightly too aggressive for data-intensive tasks.

3. **Both candidates outperform the baseline** (136 DoD). The proposer's hypothesis was correct: the quality signals (coverage matrix, zero-tolerance, reproduction commands) matter more than prompt length.

4. **Surprising result**: cand-0001 slightly outperforms cand-0002 (181 vs 171 DoD) despite cand-0002 being the "hybrid" designed to be optimal. This suggests strict's evaluator may be contributing more than fast's generator.

### Recommendation

**Promote cand-0001 (strict-lean)** as the new baseline:
- Highest DoD granularity of any variant (181)
- Zero retries (most reliable)
- Efficient test count (220 vs strict's ~364)
- Best DoD/test ratio: 0.82 (vs strict's 0.32, fast's 0.29)

For iteration 2, the proposer should:
1. Use strict-lean as the new parent
2. Try tightening DoD caps further (currently 4/feature → try 3) to see if quality holds
3. Experiment with the adversary: strict-lean's adversary may be over-contributing — try reducing to see impact
4. Address the timeout gap: add adaptive timeout based on task complexity hints

---

## Raw Data Location
- Seeds: `~/.openclaw/skills/harness/meta-harness/seeds/`
- Candidates: `~/.openclaw/skills/harness/meta-harness/candidates/`
- This report: `~/.openclaw/skills/harness/meta-harness/candidates/comparison-report.md`
