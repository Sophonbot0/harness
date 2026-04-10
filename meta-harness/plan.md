# Plan: Meta-Harness v1 — Automated Harness Evolution

## Status: READY

## Context

The OpenClaw harness skill (`~/.openclaw/skills/harness/`) orchestrates a 4-agent pipeline (Planner → Generator → Adversary → Evaluator) for development tasks. The harness-enforcer plugin provides runtime enforcement, progress tracking, and contract management.

Currently, the harness is **static** — its prompts, orchestration logic, and policies never improve automatically. The `self-improving-agent` skill captures learnings but nobody applies them systematically.

This plan implements the Meta-Harness concept from Khattab & Finn (2026) — an outer-loop system that searches over harness code using an agentic proposer with filesystem access to prior candidates' source code, scores, and execution traces.

## Architecture (paper-faithful)

```
Meta-Harness Outer Loop
  │
  ├─ Filesystem 𝒟 (growing archive)
  │   ├─ seeds/          — initial harness variants
  │   ├─ candidates/     — proposed variants + eval results
  │   └─ frontier.json   — Pareto-optimal candidates
  │
  ├─ Proposer (coding agent)
  │   ├─ reads 𝒟 via grep/cat (NOT via summaries)
  │   ├─ inspects prior code, scores, execution traces
  │   └─ proposes k=2 new harness candidates
  │
  ├─ Evaluator (benchmark runner)
  │   ├─ applies candidate harness to search-set tasks
  │   ├─ captures full execution traces
  │   └─ scores on multiple objectives
  │
  └─ Promotion Gate
      ├─ holdout evaluation (never seen by proposer)
      └─ Pareto-dominance check before activating
```

## Features

### Feature 1: Meta-Harness Workspace & Configuration
- **Description:** Create the filesystem layout for Meta-Harness evolution. This is the archive 𝒟 from the paper.
- **DoD:**
  - [ ] Directory `~/.openclaw/skills/harness/meta-harness/` exists with proper structure
  - [ ] `config/meta-harness.yaml` defines search space, objectives, iteration params
  - [ ] `config/objectives.json` defines multi-objective scoring (quality, cost, speed, stability)
  - [ ] `config/search-space.json` defines which files the proposer can modify
  - [ ] `seeds/` directory can hold baseline + variant seeds
  - [ ] `candidates/` directory stores per-candidate code + traces
  - [ ] `frontier.json` tracks Pareto-optimal candidates
  - [ ] `active/current` symlink points to the promoted harness version

### Feature 2: Seed Population
- **Description:** Create the initial population of harness variants. Paper requires strong seeds.
- **DoD:**
  - [ ] `seed-000-baseline/` — exact copy of current harness (SKILL.md + prompts/ + references/ + templates/)
  - [ ] `seed-001-concise/` — lighter prompts, less redundant instructions
  - [ ] `seed-002-strict/` — more aggressive adversary, stricter evaluation
  - [ ] `seed-003-fast/` — optimised for speed (shorter timeouts, less verbose)
  - [ ] Each seed has `metadata.json` with name, description, hypothesis
  - [ ] Each seed's harness files are syntactically valid and complete

### Feature 3: Benchmark Task Sets
- **Description:** Curated, reproducible task sets for evaluating harness candidates. Split into search set (proposer sees results) and holdout set (only for promotion).
- **DoD:**
  - [ ] `config/search-set.json` — 12 benchmark tasks across categories
  - [ ] `config/holdout-set.json` — 8 benchmark tasks (disjoint from search set)
  - [ ] Tasks cover: bug fix, feature implementation, refactor, multi-file change, ambiguous request, sprint-sized project
  - [ ] Each task has: description, project scaffold, expected DoD items, difficulty rating
  - [ ] Tasks are self-contained (include minimal project scaffolds or point to fixtures)
  - [ ] A task runner can execute any task with a given harness candidate

### Feature 4: Benchmark Runner
- **Description:** Deterministic runner that evaluates a harness candidate against a task set. Captures full traces per the paper's requirement for rich diagnostic data.
- **DoD:**
  - [ ] `runner/benchmark_runner.py` takes a candidate harness dir + task set → runs all tasks
  - [ ] Each task execution produces: plan.md, challenge-report.md, eval-report.md, scores.json
  - [ ] Runner captures execution traces: timestamps, token counts, round counts, pass/fail per DoD
  - [ ] Runner computes aggregate metrics: pass_rate, avg_rounds, avg_time, avg_tokens, stuck_rate
  - [ ] Results saved to candidate's `evaluation/` directory in the archive
  - [ ] Runner can operate in "dry-run" mode (validate harness structure without full execution)
  - [ ] Runner handles timeouts and failures gracefully (records as failure, doesn't crash)

### Feature 5: Scoring & Frontier Tracking
- **Description:** Multi-objective scoring and Pareto frontier maintenance, following the paper's approach.
- **DoD:**
  - [ ] `runner/scorer.py` computes per-candidate scores from evaluation results
  - [ ] Scores include: quality (pass_rate, eval_grade), efficiency (tokens, time), stability (stuck_rate, regression_rate)
  - [ ] `runner/frontier.py` maintains Pareto frontier across all evaluated candidates
  - [ ] Frontier uses Pareto dominance on (quality, -cost, -time) dimensions
  - [ ] `frontier.json` updated after each candidate evaluation
  - [ ] Leaderboard view: sorted by primary objective with secondary tiebreakers

### Feature 6: Proposer Skill
- **Description:** Minimal skill/prompt for the coding-agent proposer. Paper emphasises giving tools and data, not prescriptive search heuristics.
- **DoD:**
  - [ ] `proposer/proposer-skill.md` — minimal instructions for the proposer agent
  - [ ] Proposer knows: where candidates live, what files to edit, what objectives to optimize
  - [ ] Proposer has filesystem access to ALL prior candidates (code + scores + traces)
  - [ ] Proposer is NOT given compressed summaries as primary input
  - [ ] Proposer can read, grep, diff, edit — standard coding agent operations
  - [ ] Proposer outputs: new candidate directory with modified harness files + rationale.md
  - [ ] Proposer produces exactly k candidates per iteration (configurable, default k=2)

### Feature 7: Candidate Validation
- **Description:** Interface validation before evaluation (paper requirement: validate before expensive eval).
- **DoD:**
  - [ ] `runner/validator.py` checks candidate structure before benchmark run
  - [ ] Validates: all required files exist (SKILL.md, all 4 prompts, templates, references)
  - [ ] Validates: prompts are non-empty and parseable
  - [ ] Validates: no files outside search space were modified
  - [ ] Validates: no unsafe operations (rm -rf, etc.) in any file
  - [ ] Invalid candidates archived with status "invalid" and reason
  - [ ] Validation is fast (<5 seconds)

### Feature 8: Promotion Gate
- **Description:** Decides when to promote a candidate to active harness. Uses holdout set evaluation.
- **DoD:**
  - [ ] `runner/promotion.py` evaluates frontier candidates on holdout set
  - [ ] Promotion requires: holdout pass_rate > baseline, no regression on stability
  - [ ] Generates `promotion_decision.json` with: candidate, baseline comparison, rationale
  - [ ] Generates `promotion_report.md` human-readable summary
  - [ ] Updates `active/current` symlink on promotion
  - [ ] Keeps backup of previous active version for rollback
  - [ ] Rollback command: restore previous active version

### Feature 9: Meta-Harness CLI / Entry Point  
- **Description:** Single entry point to run the full Meta-Harness loop or individual phases.
- **DoD:**
  - [ ] `run_meta_harness.py` — main entry point
  - [ ] Supports: `--seed-eval` (evaluate all seeds), `--iterate N` (run N proposer iterations), `--promote` (run promotion gate)
  - [ ] Supports: `--dry-run` (validate without execution), `--verbose` (detailed logging)
  - [ ] Logs all actions to `runs/<run-id>/manifest.json`
  - [ ] Handles interruption gracefully (can resume from last complete iteration)

### Feature 10: README & Documentation
- **Description:** Update repository documentation to reflect Meta-Harness philosophy.
- **DoD:**
  - [ ] `README.md` at repo root describes the harness skill + Meta-Harness evolution system
  - [ ] README includes: architecture diagram (text), quick start, how evolution works
  - [ ] README references the Khattab & Finn paper
  - [ ] README explains: seeds, candidates, frontier, promotion, search vs holdout
  - [ ] All existing files have updated comments where Meta-Harness is relevant
  - [ ] `meta-harness/README.md` with detailed technical documentation

## Sprints

### Sprint 1: Foundation (Features 1, 2, 3)
- Feature 1: Meta-Harness Workspace & Configuration
- Feature 2: Seed Population
- Feature 3: Benchmark Task Sets

### Sprint 2: Evaluation Engine (Features 4, 5, 7)
- Feature 4: Benchmark Runner
- Feature 5: Scoring & Frontier Tracking
- Feature 7: Candidate Validation

### Sprint 3: Evolution Loop (Features 6, 8, 9, 10)
- Feature 6: Proposer Skill
- Feature 8: Promotion Gate
- Feature 9: Meta-Harness CLI
- Feature 10: README & Documentation

## Technical Notes
- The benchmark runner simulates harness execution by applying candidate prompts to mock task scenarios
- For v1, "execution" means: spawn subagents with the candidate's prompts against task fixtures and capture output
- The proposer is spawned as an OpenClaw coding agent with full filesystem access
- All paths are relative to `~/.openclaw/skills/harness/`
- The active harness symlink allows instant rollback without touching the skill loader

## Out of Scope (v1)
- Co-evolution of harness-enforcer plugin internals
- Weight/model co-evolution
- Real-time evolution during production runs
- Auto-triggering from capability-evolver (manual trigger first)
- Distributed/parallel candidate evaluation
