# Meta-Harness — Automated Harness Evolution

Technical documentation for the Meta-Harness evolution system.

## Paper Alignment

This implementation follows [Khattab & Finn (2026)](https://arxiv.org/abs/2603.28052):

| Paper Concept | Our Implementation |
|---|---|
| Proposer (coding agent) | `proposer/proposer-skill.md` — spawned via OpenClaw `sessions_spawn` |
| Filesystem 𝒟 | `seeds/`, `candidates/`, `frontier.json` — raw code + scores + traces |
| Search set | `config/search-set.json` — 12 tasks |
| Holdout/test set | `config/holdout-set.json` — 8 tasks (never shown to proposer) |
| Evaluation | `runner/benchmark_runner.py` |
| Pareto frontier | `runner/frontier.py` |
| Interface validation | `runner/validator.py` |
| Promotion | `runner/promotion.py` |

## Algorithm

```
Algorithm 1: Meta-Harness outer loop

Input: tasks X, LLM M, proposer P, iterations N
Initialize: population H (seeds)
Initialize: filesystem D ← ∅

for H ∈ H do                          # Evaluate seeds
    E_H ← Evaluate(H, M, X)
    D ← D ∪ {(H, E_H)}

for t = 1...N do                       # Evolution loop
    P queries filesystem D              # Proposer inspects prior history
    P proposes k new harnesses          # k=2 by default
    for each proposed H:
        if H passes validation:
            D ← D ∪ {(H, Evaluate(H, M, X))}

return Pareto frontier of D
```

## Objectives

| Objective | Direction | Weight | Description |
|---|---|---|---|
| `pass_rate` | ↑ maximize | 0.4 | Fraction of tasks where all DoD pass |
| `eval_grade` | ↑ maximize | 0.3 | Average evaluator grade |
| `avg_rounds` | ↓ minimize | 0.1 | Mean BUILD→EVAL rounds |
| `avg_time_seconds` | ↓ minimize | 0.1 | Mean wall-clock time per task |
| `stuck_rate` | ↓ minimize | 0.1 | Fraction of tasks that stall/timeout |

## Search Space

The proposer can modify:
- All 4 system prompts (planner, generator, adversary, evaluator)
- `SKILL.md` (orchestration logic)
- Grading criteria
- Templates
- Policy knobs (`meta/policy.json`)

The proposer CANNOT modify:
- Runner infrastructure
- Benchmark tasks
- Scoring logic
- This configuration

## Seed Population

| Seed | Name | Hypothesis |
|---|---|---|
| `seed-000-baseline` | Baseline | Current production harness |
| `seed-001-concise` | Concise | Shorter prompts → less noise → better quality |
| `seed-002-strict` | Strict | Stricter adversary/eval → fewer post-delivery bugs |
| `seed-003-fast` | Fast | Speed over thoroughness for typical tasks |

## Benchmark Tasks

### Search Set (12 tasks)
Categories: bug fix, feature implementation, refactor, ambiguous request, sprint-sized project

### Holdout Set (8 tasks)
Disjoint from search set. Used only for promotion decisions.

### Phase 2 hardening
The benchmark suite is now operationally strict rather than conceptual:

- `runner/task_registry.py` is the canonical loader/validator for task sets
- every task is merged with fixture-local `task.json` metadata
- every fixture receives a deterministic hash for replayability
- search/holdout disjointness is validated explicitly
- thin fixtures are materialized into deterministic scaffold files
- `benchmark_runner.py` supports `dry_run`, `simulate`, and live orchestration modes
- aggregate benchmark output now includes category/difficulty breakdowns, DoD coverage, artifact validity, regression rate, and leaderboard rows
- `runner/verify_benchmark_fixtures.py` proves every scaffold can be materialized and pass its baseline verifier in isolation
- `meta-harness/tests/test_phase2.py` validates the suite end-to-end offline

Useful commands:

```bash
python3 runner/task_registry.py config fixtures
python3 runner/verify_benchmark_fixtures.py
python3 -m unittest discover tests -v
python3 run_meta_harness.py --seed-eval --simulate
```

## Promotion Rules

A candidate is promoted only if:
1. Holdout pass_rate ≥ 70%
2. No metric regresses > 5% vs baseline
3. Pareto-dominates baseline on primary objectives
4. Human-inspectable (no brittle hard-coded solutions)

## Usage

See `run_meta_harness.py --help` for all commands.
