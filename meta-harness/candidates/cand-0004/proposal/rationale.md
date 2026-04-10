# cand-0004: eval-only — Rationale

## Parent: cand-0001 (strict-lean, composite 0.945)

## Hypothesis
The adversary phase is redundant when the evaluator is strong enough. By merging adversarial probing INTO the evaluator, we eliminate a full agent call (~12 min) per cycle while retaining quality. The evaluator already has zero-tolerance policy — adding structured edge-case verification makes it a complete quality gate.

## Evidence from iteration 1
1. **Strict's evaluator > fast's generator** — the comparison report explicitly notes this
2. **cand-0001 had 0 retries** — the adversary found issues that the generator already handled, suggesting diminishing returns
3. **Both candidates scored 100% pass rate** — the evaluator's zero-tolerance policy is the actual quality gate, not the adversary

## What changes

### 1. Adversary: REMOVED
No challenge phase. The workflow becomes: PLAN → BUILD → EVAL. This is the most radical cut — if it works, it proves the adversary was overhead.

### 2. Evaluator: Expanded with edge-case probing
The evaluator now has two responsibilities in one pass:
- **Verification** (existing): check every DoD criterion with evidence
- **Probing** (new): try 5 edge cases per feature (empty, large, malformed, boundary, concurrent)
- **Structured output**: verification table + edge-case audit table + final grade

The evaluator gets 25 min (up from 20) to compensate.

### 3. Everything else: unchanged
Planner and generator are identical to cand-0001. This is a controlled experiment isolating the adversary's contribution.

## Risks
- Evaluator may miss issues that a separate adversary (different model family) would catch
- Single-model evaluation lacks the diversity benefit of adversary being a different model
- 25 min may not be enough for probing + verification on complex tasks

## Success criteria
- Pass rate: 100%
- Avg DoD/task: ≥14 (if it drops below cand-0001's 15.1, adversary was contributing)
- Zero retries
- Cycle time: ≥10 min faster than cand-0001
