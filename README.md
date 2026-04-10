# Harness — Meta-Evolved Development Pipeline

A 4-agent harness for quality-driven AI development, with automated evolution via [Meta-Harness](https://arxiv.org/abs/2603.28052).

## Architecture

```
PLAN → BUILD → CHALLENGE → EVAL → DONE? → ✅ deliver / 🔄 retry / ⛔ escalate
```

| Agent | Role | Model |
|-------|------|-------|
| **Planner** | Decompose request → features + DoD criteria | sonnet-class |
| **Generator** | Implement features, run tests, commit | opus-class |
| **Adversary** | Devil's advocate — find holes, demand evidence | different family |
| **Evaluator** | Grade against DoD, verify adversary challenges | sonnet/opus |

Each agent is a separate subagent with clean context. The orchestrator manages the loop.

## Meta-Harness Evolution

> *"The performance of LLM systems depends not only on model weights, but also on their harness: the code that determines what information to store, retrieve, and present to the model."* — [Khattab & Finn, 2026](https://arxiv.org/abs/2603.28052)

This harness **evolves itself** through an outer-loop search:

1. **Seeds** — Human-authored harness variants (baseline, concise, strict, fast)
2. **Proposer** — A coding agent inspects prior candidates' code, scores, and execution traces via filesystem
3. **Benchmark** — Each candidate is evaluated on a standardized task set
4. **Frontier** — Pareto-optimal candidates tracked across multiple objectives
5. **Promotion** — Best candidates replace the active harness after holdout validation

### Key design choices (paper-faithful)

- **Full filesystem access** — The proposer reads raw code, scores, and execution traces. Not compressed summaries.
- **Minimal outer loop** — The loop only proposes, evaluates, and logs. Diagnosis is delegated to the proposer agent.
- **Search vs holdout split** — Proposer only sees search-set results. Holdout set used only for promotion decisions.
- **Code-space search** — The proposer can edit prompts, orchestration logic, policies, and grading criteria — not just templates.
- **Multi-objective Pareto** — Quality, cost, and speed are optimized jointly.

### Structure

```
meta-harness/
├── config/                    # Search parameters, objectives, constraints
│   ├── meta-harness.yaml     # Main configuration
│   ├── objectives.json       # Multi-objective scoring definition
│   ├── search-space.json     # What the proposer can modify
│   ├── search-set.json       # 12 benchmark tasks (proposer sees these)
│   └── holdout-set.json      # 8 holdout tasks (promotion only)
├── seeds/                     # Initial harness population
│   ├── seed-000-baseline/    # Current production harness
│   ├── seed-001-concise/     # Shorter prompts, less prescriptive
│   ├── seed-002-strict/      # Aggressive adversary, zero-tolerance eval
│   └── seed-003-fast/        # Speed-optimized, minimal overhead
├── candidates/                # Proposed candidates (grows over time)
├── runner/                    # Evaluation infrastructure
│   ├── benchmark_runner.py   # Run candidate against task set
│   ├── scorer.py             # Multi-objective scoring
│   ├── frontier.py           # Pareto frontier tracking
│   ├── validator.py          # Candidate structure validation
│   └── promotion.py          # Holdout evaluation + promotion gate
├── proposer/                  # Proposer agent configuration
│   └── proposer-skill.md     # Minimal skill for the coding-agent proposer
├── runs/                      # Evolution run logs
├── fixtures/                  # Task scaffolds for benchmarks
├── frontier.json              # Current Pareto frontier
└── run_meta_harness.py        # CLI entry point
```

### Quick start

```bash
# Check status
python3 meta-harness/run_meta_harness.py --status

# Evaluate all seeds (dry run — validates without executing)
python3 meta-harness/run_meta_harness.py --seed-eval --dry-run

# Run 5 evolution iterations
python3 meta-harness/run_meta_harness.py --iterate 5

# Check promotion candidates
python3 meta-harness/run_meta_harness.py --promote
```

## Harness Skill

The core skill orchestrates the 4-agent pipeline:

### When to use

- Implementing features, bug fixes, refactors
- Tasks touching >2 files or >1 feature
- Tasks where quality verification matters

**Skip** for: trivial one-line fixes, pure research, user says "quick"

### Loop control

After each EVAL round:
- **All DoD PASS** → ✅ Deliver results
- **Progress made** → 🔄 Retry with specific feedback
- **Same items stuck** → ⛔ Escalate to owner
- **Timeout > 30min** → ⛔ Escalate with current state

### Sprint mode

Projects with >8 features auto-split into sprints (3-5 features each). Each sprint runs its own BUILD→CHALLENGE→EVAL cycle. Integration eval runs after >2 sprints.

## Files

| File | Description |
|------|-------------|
| `SKILL.md` | Main skill definition — orchestration rules |
| `prompts/planner-system.md` | System prompt for the Planner agent |
| `prompts/generator-system.md` | System prompt for the Generator agent |
| `prompts/adversary-system.md` | System prompt for the Adversary agent |
| `prompts/evaluator-system.md` | System prompt for the Evaluator agent |
| `references/grading-criteria.md` | Domain-specific grading criteria |
| `templates/*.md` | Output templates for plan, challenge-report, eval-report |

## References

- [Meta-Harness: End-to-End Optimization of Model Harnesses](https://arxiv.org/abs/2603.28052) — Khattab & Finn, 2026
- [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents) — Anthropic
- [Harness Engineering](https://martinfowler.com/articles/exploring-gen-ai/harness-engineering.html) — Böckeler, 2026

## License

MIT
