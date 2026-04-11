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
3. **Meta-harness** (`meta-harness/`) evolves the skill prompts by benchmarking variants against a test suite

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
