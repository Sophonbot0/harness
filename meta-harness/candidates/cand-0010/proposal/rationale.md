# Proposal Rationale — cand-0010 (trend-oracle)

## Observations from cand-0008 (deep-planner, composite 0.975)

1. **Near-perfect on easy/medium tasks**: search-001 through search-006 all scored A+ in round 1
2. **Hard tasks needed round 2**: search-007 (notifications, 20/22 DoD, A) and search-011 (url-shortener, 22/24 DoD, A) both required 2 rounds
3. **Pattern in round-2 items**: The missing DoD items in both cases were related to edge cases the planner didn't anticipate — concurrency in the notification queue and boundary conditions in URL shortener analytics
4. **Adversary found issues planner missed**: The adversary's "suggested missing DoD" items consistently covered patterns the planner didn't think of

## Diagnosis

The planner writes excellent positive requirements and decent Must-NOT items, but lacks awareness of which failure patterns historically cause issues. The adversary finds these, but by that point we're already in round 2.

The adversary probes ad-hoc rather than systematically. It might find 3 concurrency issues and miss all boundary conditions, or vice versa.

## Changes

### Planner: Trend-Aware Planning
Added a mandatory "Trend Analysis" step where the planner evaluates 5 common failure patterns against each feature. This front-loads what the adversary would find, reducing round-2 regressions.

### Adversary: Structured Taxonomy
Replaced ad-hoc probing with a 4-category taxonomy. The adversary must cover each applicable category, ensuring no blind spots. Timeout increased 12→15 min.

### Evaluator: Confidence Tracking
Added per-criterion confidence scores (HIGH/MEDIUM/LOW) so the proposer can identify which criteria had weak verification.

## Expected Impact
- search-007 and search-011 should complete in round 1 (A+ instead of A)
- Overall DoD count should increase slightly (trend analysis produces more Must-NOT items)
- Composite target: ≥0.980

## Risks
- Planner may over-generate DoD items, some low-value
- Adversary taxonomy may be too rigid for unusual tasks (search-008 ambiguous)
- 15 min adversary timeout may not be enough for hard tasks with 4-category coverage
