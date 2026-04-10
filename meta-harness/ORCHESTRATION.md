# Meta-Harness Orchestration Guide

This document explains how to run the Meta-Harness evolution loop from within OpenClaw.

## The loop (for the orchestrating agent)

### Step 1: Evaluate Seeds (one-time setup)

For each seed in `meta-harness/seeds/`:

```
1. Read seed's harness prompts
2. For each task in search-set.json:
   a. Set up project from fixture
   b. Spawn subagent with orchestrator prompt (built from seed's prompts + task)
   c. Wait for completion
   d. Parse scores from eval-report.md / scores.json
   e. Save traces to seed's evaluation/ directory
3. Compute aggregate scores
4. Update frontier.json
```

### Step 2: Proposer Iteration

```
1. Spawn proposer agent with:
   - Task: "Read meta-harness/ filesystem, inspect prior candidates, propose 2 new harness variants"
   - CWD: ~/.openclaw/skills/harness/
   - Skill: meta-harness/proposer/proposer-skill.md
   - Model: opus-class (best available)
   
2. Proposer reads filesystem:
   - frontier.json (what's working)
   - seeds/*/evaluation/ (scores + traces)
   - candidates/*/evaluation/ (if any)
   - config/objectives.json (what to optimize)
   
3. Proposer writes:
   - candidates/cand-NNNN/harness/ (modified prompts)
   - candidates/cand-NNNN/metadata.json
   - candidates/cand-NNNN/proposal/rationale.md

4. Validate each candidate (runner/validator.py)

5. For each valid candidate:
   - Run benchmark (same as seed eval)
   - Save traces
   - Update frontier
```

### Step 3: Promotion

```
1. Select frontier candidates
2. Run holdout-set.json evaluation
3. Compare vs baseline
4. If better: promote (update active/ symlink)
```

## How to spawn benchmark tasks

Each benchmark task is executed as a subagent. The orchestrator prompt is built by
combining the candidate's system prompts with the task description.

Example spawn call (from OpenClaw):

```
sessions_spawn(
    task=<orchestrator_prompt>,     # Built by task_executor.build_orchestrator_prompt()
    mode="run",
    runtime="subagent",
    model="github-copilot/claude-sonnet-4.6",  # Fixed eval model
    cwd=<project_dir>,              # Task's working directory
    runTimeoutSeconds=1800,         # 30 min max
)
```

The subagent:
1. Reads the project files
2. Acts as Planner → writes plan.md
3. Acts as Generator → implements features
4. Acts as Adversary → writes challenge-report.md
5. Acts as Evaluator → writes eval-report.md + scores.json

After the subagent completes, the orchestrator:
1. Reads scores.json from the project directory
2. Copies all artifacts to the evaluation trace directory
3. Moves to the next task

## How to spawn the proposer

```
sessions_spawn(
    task=<proposer_prompt>,    # Content of proposer-skill.md + iteration context
    mode="run",
    runtime="subagent",
    model="github-copilot/claude-opus-4.6",  # Best model for diagnosis
    cwd="~/.openclaw/skills/harness/",
    runTimeoutSeconds=2700,    # 45 min
)
```

The proposer:
1. Reads frontier.json
2. Inspects top candidates' code + traces
3. Forms hypotheses about failure modes
4. Writes 2 new candidate directories
