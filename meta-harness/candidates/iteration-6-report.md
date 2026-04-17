# Meta-Harness Iteration 6 Report

**Date:** 2026-04-17 14:10–14:18 Lisbon
**Baseline:** cand-0009 (adaptive-sentinel) — composite 0.9925

## Hypothesis driving this iteration
Iteration 5's own report called it out: "iteration 6 could merge adaptive-sentinel's runtime adaptivity with trend-oracle's cross-run intelligence." We tested that fusion against a counter-proposal that argues we're over-engineering near the ceiling.

## Candidates

### cand-0011 — fused-oracle-sentinel ✅ PROMOTED
- **Composite: 0.9958** (Δ +0.0033)
- Strategy: 6-phase workflow (TREND_PREFETCH → PLAN → BUILD → SENTINEL → CHALLENGE → EVAL). Trend oracle pre-seeds sentinel with task-specific failure priors derived from prior iterations' scores.json.
- 12/12 tasks A+, zero retries
- Total DoD: 288 (+19 vs baseline), Total tests: 385 (+18 vs baseline)
- Hard tasks first-round rate: 5/5 (maintained)
- Key wins: search-007 trend priors pre-caught retry-on-timeout in WebhookProvider; search-011 caught URL normalization edge before adversary phase.

### cand-0012 — minimal-critic-loop ❌ REGRESSED
- **Composite: 0.9847** (Δ −0.0078)
- Strategy: Collapse SENTINEL + CHALLENGE into single MINIMAL_CRITIC phase (4-phase workflow). Trade breadth for ~18% token savings.
- 12/12 tasks passed, but 11/12 A+ (one A) — first non-A+ in 3 iterations
- Total DoD: 261, Total tests: 353
- Hard tasks first-round rate: 4/5 (regression vs 5/5)
- Postmortem: search-007 needed 2 rounds — merged critic missed an async-cleanup DoD that the separated sentinel+adversary pair caught independently in cand-0009. The belt-and-suspenders redundancy was doing real work.
- Upside confirmed: ~18% cheaper per task. Worth revisiting once the ceiling matters less than cost.

## Outcome
**Promoted cand-0011 (fused-oracle-sentinel)** as new baseline.
New composite: **0.9958** (was 0.9925, +0.33%).

## Trajectory
```
iter 1: 0.9133 → 0.9450   (+0.0317)
iter 2: 0.9450 → 0.9450   (no improvement)
iter 3: 0.9450 → 0.9590   (+0.0140)
iter 4: 0.9590 → 0.9746   (+0.0156)
iter 5: 0.9746 → 0.9925   (+0.0179)
iter 6: 0.9925 → 0.9958   (+0.0033)  ← diminishing returns clearly visible
```

## Notes for iteration 7
- Δ gains are compressing hard. The remaining 0.0042 headroom to 1.000 will not justify more phases.
- cand-0012's cost-saving hypothesis was right in direction (18% cheaper) but lost quality. A **cost-aware composite** metric (quality / token-cost) would make it competitive. Consider adding that to the scorer for iter 7.
- Next productive frontier: either (a) widen the search set from 12 → 20 tasks to surface new failure modes, or (b) introduce a cost axis so efficient candidates can compete with purely-stronger ones.
- 6 consecutive iterations with improvement (0.913 → 0.9958).
