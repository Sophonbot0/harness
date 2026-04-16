# Harness Robustness Roadmap

_Date: 2026-04-16_

## Goal

Turn the harness from a useful but brittle multi-agent workflow into a **measurable, evolvable, regression-resistant system** aligned with:

- **Natural-Language Agent Harnesses** (`arXiv:2603.25723`)
- **Meta-Harness: End-to-End Optimization of Model Harnesses** (`arXiv:2603.28052`)
- **AutoHarness** (Google DeepMind)

The target is not just “better prompts”. The target is a harness that:

1. fails less often,
2. explains failures clearly,
3. can be benchmarked offline,
4. can evolve safely over time, and
5. only promotes changes that survive holdout evaluation.

---

## Current Diagnosis

The current harness already has strong foundations:

- 4-agent architecture: Planner → Generator → Adversary → Evaluator
- natural-language orchestration (`skill/`)
- runtime/plugin integration (`plugin/`)
- checkpointing and progress tracking
- a partial meta-harness workspace (`meta-harness/`)

But it is still not robust enough. The main weaknesses are:

### 1. Weak failure observability
We do not yet have a clean, standard, per-run failure taxonomy with raw traces, normalized scores, and structured postmortems that make regressions easy to diagnose.

### 2. Contracts are still mostly markdown-first
`plan.md`, `challenge-report.md`, and `eval-report.md` are human-readable, but not yet strongly schema-validated, making downstream comparison and scoring fragile.

### 3. Benchmarking is not yet the center of development
We have meta-harness scaffolding, but the benchmark suite, scoring discipline, and promotion gates are not yet the hard control surface for all harness changes.

### 4. Search vs holdout discipline needs tightening
The papers are clear: the proposer must learn only from the search set, while promotion must depend on a separate holdout set. We have this structure conceptually, but it needs to become operationally strict.

### 5. Robustness logic is still under-specified
The current loop handles progress and stuck detection, but still needs stronger protections for:
- repeated non-progress loops,
- malformed artifacts,
- partial task completion misclassified as success,
- runtime/tool failures being conflated with harness-quality failures.

### 6. Harness evolution is not yet closed-loop in practice
We already have a `meta-harness/` area, but we still need the system to reliably:
- propose candidate variants,
- evaluate them over a benchmark suite,
- archive traces,
- compare against baselines,
- promote only safe improvements.

---

## North Star

By the end of this roadmap, the harness should behave like this:

1. **Every run emits structured artifacts** in addition to markdown.
2. **Every failure is classified** (planning failure, generator stall, adversary miss, evaluator mismatch, runtime/tooling fault, timeout, malformed contract, false pass, etc.).
3. **Every harness change is benchmarked** on a search set.
4. **Every promotion is gated** by holdout evaluation and regression rules.
5. **The proposer can inspect full prior experience** through the filesystem: code, prompts, diffs, traces, scores, reports.
6. **The production harness and the evolutionary harness remain decoupled**, so experimentation cannot silently degrade day-to-day task execution.

---

## Roadmap

## Phase 0 — Stabilize the Measurement Surface

### Objective
Make failures legible before changing harness behavior.

### Deliverables
- Define a **failure taxonomy** for all harness runs.
- Add a structured `run-summary.json` artifact for every task execution.
- Add structured status fields for each stage:
  - `planner_status`
  - `generator_status`
  - `adversary_status`
  - `evaluator_status`
  - `final_outcome`
- Separate **harness failure** from **environment failure**:
  - repo/setup failure
  - tool/runtime failure
  - model timeout
  - malformed output
  - genuine quality failure
- Add wall-clock timings, round counts, and artifact completeness checks.

### Why this matters
Right now “many failures” can mean several different things. Before changing prompts or policies, we need to know whether the harness is failing because the logic is poor, the runtime is brittle, the task is ambiguous, or the infrastructure is flaky.

### Exit criteria
- Every run produces enough structured data for aggregation.
- We can answer: “What failed most often in the last 100 runs?” without manually reading markdown.

---

## Phase 1 — Make Contracts Explicit and Machine-Checkable

### Objective
Upgrade markdown artifacts into explicit contracts with validation.

### Deliverables
- Introduce JSON sidecars or primary structured outputs for:
  - `plan.contract.json`
  - `challenge.contract.json`
  - `eval.contract.json`
- Add schema validation for required fields such as:
  - extracted requirements
  - DoD items
  - challenge severity and evidence
  - evaluator verdicts per DoD item
  - overall pass/fail + confidence + rationale
- Fail fast on malformed contracts.
- Keep markdown reports for human readability, but treat structured artifacts as the system-of-record.

### Why this matters
This is the direct move toward the NLAH/IHR idea: explicit contracts, durable artifacts, and portable execution surfaces. It also makes comparison across candidates possible.

### Exit criteria
- A run cannot be marked successful if required contract fields are missing.
- Benchmark scoring consumes structured artifacts, not regex over markdown prose.

---

## Phase 2 — Build a Real Robustness Benchmark Suite

### Objective
Stop developing the harness against anecdotes; develop it against a representative benchmark.

### Deliverables
- Curate a benchmark task corpus divided into:
  - **search set**
  - **holdout set**
- Ensure diversity across failure modes:
  - bug fixes
  - multi-file feature work
  - ambiguous specs
  - sprint-sized implementations
  - brittle existing codebases
  - tasks with hidden edge cases
  - tasks with easy happy-path but subtle correctness failures
- Define canonical scoring dimensions:
  - pass rate
  - DoD coverage
  - evaluator quality
  - average rounds
  - stuck rate
  - time to completion
  - artifact validity rate
- Create benchmark fixtures that are replayable and isolated.

### Why this matters
If the benchmark is weak, the harness will optimize for the wrong things. The benchmark must encode the kinds of failures we actually care about.

### Exit criteria
- We can run baseline harness evaluation over the full search set and holdout set.
- Failures are reproducible enough to compare candidate variants.

---

## Phase 3 — Harden the Runtime Loop

### Objective
Make the production harness more resistant to loops, false positives, and incomplete work.

### Deliverables
- Strengthen stuck detection with explicit categories:
  - same DoD item failing repeatedly
  - no delta in files/tests/results
  - repeated artifact malformation
  - repeated runtime/tooling failure
- Add explicit anti-false-pass checks:
  - required files changed when task scope demands it
  - tests or validations actually executed
  - evaluator evidence required for claims of success
- Add phase-specific retry policies:
  - planner retry rules
  - generator retry rules
  - adversary re-run only when needed
  - evaluator fail-closed behavior on insufficient evidence
- Add artifact completeness gating before entering the next phase.
- Add deterministic “escalate to owner” triggers rather than vague best-effort continuation.

### Why this matters
A robust harness is not one that loops longer. It is one that knows when to continue, when to stop, and when not to trust its own outputs.

### Exit criteria
- Reduced false-pass rate.
- Fewer long useless loops.
- Clearer escalation behavior.

---

## Phase 4 — Finish the Meta-Harness Outer Loop

### Objective
Convert the existing `meta-harness/` scaffolding into a real evolutionary system.

### Deliverables
- Complete the proposer → validator → benchmark → archive → frontier → promotion loop.
- Ensure the proposer has filesystem access to:
  - prompts
  - `SKILL.md`
  - prior candidates
  - diffs
  - structured scores
  - raw traces
  - challenge/eval reports
- Preserve raw artifacts per candidate under candidate-specific directories.
- Keep production harness isolated from experimental candidates.
- Add candidate manifests with explicit hypotheses, e.g.:
  - “stricter planner requirement extraction reduces scope misses”
  - “shorter adversary prompt improves issue precision”
  - “fail-closed evaluator reduces false passes but may hurt throughput”

### Why this matters
This is the core Meta-Harness insight: optimizing harnesses requires richer historical context than compressed summaries.

### Exit criteria
- We can run multi-candidate iterations from the CLI.
- Every candidate has traceable inputs, outputs, scores, and rationale.

---

## Phase 5 — Promotion and Safety Gates

### Objective
Make harness evolution safe enough for real use.

### Deliverables
- Define promotion policy requiring:
  - holdout improvement or non-regression
  - no large regressions on critical metrics
  - artifact validity above threshold
  - no brittle task-specific hacks
- Maintain:
  - `frontier.json`
  - `promotions.jsonl`
  - baseline snapshots
- Add rollback capability for promoted variants.
- Record promotion rationale in machine-readable form.

### Why this matters
Without hard gates, evolution will produce clever but brittle candidates that look good on the search set and fail in the wild.

### Exit criteria
- Promotion is automatic only when thresholds are met.
- Rollback is trivial.

---

## Phase 6 — AutoHarness-Style Search in Code Space

### Objective
Move beyond prompt-only tuning and search over executable harness policies.

### Deliverables
- Define a constrained code-search surface, for example:
  - retry policy knobs
  - phase transition rules
  - evidence thresholds
  - scoring aggregation logic
  - checkpoint cadence
  - challenge selection heuristics
- Keep core runtime protected, but allow specific policy files to evolve.
- Add validation to prevent unsafe or degenerate candidates.

### Why this matters
AutoHarness suggests that learned executable constraints can outperform static hand-authored control logic. For us, the equivalent is evolving policy code and structured control rules, not only prompt text.

### Exit criteria
- Candidate variants can modify approved policy surfaces safely.
- We can compare prompt-only evolution vs code-policy evolution.

---

## Phase 7 — Continuous Robustness Operations

### Objective
Make harness quality a continuously monitored property, not a one-off project.

### Deliverables
- Add dashboards or reports for:
  - pass rate trends
  - false-pass incidents
  - average rounds
  - timeout/stuck distribution
  - most common failure classes
- Add regression alerts when recent runs deviate from baseline.
- Add periodic holdout re-runs on promoted candidates.
- Add a “known failure modes” ledger to inform future proposer iterations.

### Why this matters
Robustness decays if it is not monitored. As tasks, models, and environments change, the harness must keep being measured.

### Exit criteria
- We can detect regression quickly.
- Promotion decisions remain grounded in recent evidence.

---

## Recommended Execution Order

### Sprint 1 — Measurement + Contracts
- Phase 0
- Phase 1

### Sprint 2 — Benchmark Discipline
- Phase 2
- minimal baseline evaluation pass

### Sprint 3 — Runtime Hardening
- Phase 3

### Sprint 4 — Evolution Loop Completion
- Phase 4
- Phase 5

### Sprint 5 — Code-Space Evolution
- Phase 6

### Sprint 6 — Continuous Ops
- Phase 7

---

## Non-Goals

These are important, but not first:

- replacing the whole harness with a totally new runtime,
- optimizing for a single benchmark only,
- letting experimental candidates directly mutate production behavior,
- making the proposer change unrestricted plugin internals,
- overfitting to one model family.

---

## Success Metrics

We should consider this roadmap successful if we achieve most of the following:

- materially lower false-pass rate,
- materially lower stuck/timeout rate,
- higher benchmark pass rate on holdout,
- better artifact validity,
- fewer opaque failures requiring manual diagnosis,
- repeatable promotion of candidates that beat baseline,
- confidence that the harness is improving systematically rather than changing chaotically.

---

## Immediate Next Steps

1. Add this roadmap to the repo.
2. Implement Phase 0 artifacts and failure taxonomy first.
3. Tighten contract schemas before changing prompts further.
4. Run a baseline benchmark pass and record the current failure distribution.
5. Only then resume aggressive prompt/policy evolution.

This order is deliberate: **measure first, evolve second**.
