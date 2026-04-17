# Harness — OpenClaw Quality Pipeline

A unified system for quality-driven development tasks. Combines the runtime plugin (tools + state management) with the skill (prompts + workflow orchestration) and the meta-harness (evolutionary self-improvement loop).

## Structure

```
harness/
├── plugin/              ← OpenClaw plugin (TypeScript)
│   ├── index.ts         ← Plugin entry + stale detection + progress bar
│   ├── src/
│   │   ├── tools.ts     ← 9 harness_* tools
│   │   ├── state.ts     ← Run state, contracts, learning log
│   │   ├── progress.ts  ← Telegram progress bar renderer
│   │   └── validation.ts ← Eval report + challenge validation
│   └── openclaw.plugin.json
│
├── skill/               ← Agent instructions (prompts)
│   ├── SKILL.md         ← Master orchestration guide
│   ├── prompts/         ← System prompts for each agent phase
│   │   ├── planner-system.md
│   │   ├── generator-system.md
│   │   ├── adversary-system.md
│   │   └── evaluator-system.md
│   ├── templates/       ← Output templates (plan, eval, challenge)
│   └── references/      ← Grading criteria
│
├── meta-harness/        ← Evolutionary self-improvement
│   ├── config/          ← Objectives, search-set, search-space
│   ├── seeds/           ← Seed variants for benchmarking
│   ├── candidates/      ← Evolved candidates + reports
│   ├── active/          ← Currently promoted variant
│   ├── runner/          ← Benchmark + promotion scripts
│   ├── proposer/        ← Proposer skill for generating candidates
│   └── state.json       ← Evolution loop state
│
└── docs/                ← Historical analysis and plans
```

## How it works

1. **Plugin** (`plugin/`) registers 9 tools: `harness_start`, `harness_checkpoint`, `harness_challenge`, `harness_submit`, `harness_status`, `harness_reset`, `harness_resume`, `harness_plan`, `harness_modify`
2. **Skill** (`skill/`) tells the agent *how* to use those tools: PLAN → BUILD → CHALLENGE → EVAL workflow
3. **Meta-harness** (`meta-harness/`) evolves the skill prompts by benchmarking variants against a search set / holdout set benchmark suite

## Benchmark suite (Phase 2)

The benchmark suite is now a first-class surface:

- **Search set:** `meta-harness/config/search-set.json` — proposer-visible tasks
- **Holdout set:** `meta-harness/config/holdout-set.json` — promotion-only tasks
- **Task registry:** `meta-harness/runner/task_registry.py` merges task-set metadata with fixture metadata and enforces search/holdout disjointness
- **Replayable fixtures:** `meta-harness/fixtures/*` contain deterministic scaffolds; thin fixtures are materialized reproducibly
- **Runner modes:**
  - `--dry-run` → validate candidate + task suite only
  - `--simulate` → deterministic offline benchmark for regression testing
  - live mode → emits spawn instructions / captures traces
- **Canonical metrics:** pass rate, DoD coverage, artifact validity rate, avg rounds, avg time, stuck rate, regression rate
- **Fixture verification:** `meta-harness/runner/verify_benchmark_fixtures.py` proves every task scaffold can be materialized and baseline-verified in isolation

Quick checks:

```bash
python3 meta-harness/runner/task_registry.py meta-harness/config meta-harness/fixtures
python3 meta-harness/runner/verify_benchmark_fixtures.py
python3 -m unittest discover meta-harness/tests -v
python3 meta-harness/run_meta_harness.py --seed-eval --simulate
```

## Pipeline

```
User request → PLAN (planner) → BUILD (generator) → CHALLENGE (adversary) → EVAL (evaluator)
                                                                              ↓
                                                                    PASS → deliver
                                                                    FAIL → retry BUILD
                                                                    STUCK → escalate
```

## Installation

The plugin is loaded via `openclaw.json`:
```json
{
  "extensions": {
    "harness-enforcer": {
      "source": "path",
      "installPath": "~/.openclaw/skills/harness/plugin"
    }
  }
}
```
