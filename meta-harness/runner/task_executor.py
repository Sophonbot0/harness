#!/usr/bin/env python3
"""
Task Executor — Runs a single benchmark task through a harness pipeline.

This is the actual execution engine. For each task, it:
1. Sets up a temporary project directory from the task fixture
2. Runs the 4-agent pipeline: Planner → Generator → Adversary → Evaluator
3. Captures all artifacts as execution traces
4. Returns structured scores

Designed to be called by benchmark_runner.py, or standalone for debugging.

The pipeline is executed as a SINGLE subagent that receives the full
orchestration instructions + candidate prompts. This keeps the execution
self-contained and matches how the real harness works in OpenClaw.
"""

import json
import os
import shutil
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path


def build_orchestrator_prompt(task: dict, prompts: dict, project_dir: str) -> str:
    """Build the full orchestrator prompt that a subagent will execute.
    
    This injects the candidate's prompts into a single orchestration task,
    simulating what the harness skill does but in a controlled benchmark context.
    """
    
    task_desc = task.get("description", "No description")
    task_name = task.get("name", task.get("id", "unknown"))
    
    planner_prompt = prompts.get("planner-system", "You are the PLANNER. Write plan.md.")
    generator_prompt = prompts.get("generator-system", "You are the GENERATOR. Implement plan.md.")
    adversary_prompt = prompts.get("adversary-system", "You are the ADVERSARY. Challenge the implementation.")
    evaluator_prompt = prompts.get("evaluator-system", "You are the EVALUATOR. Grade the work.")
    skill_md = prompts.get("skill", "")
    
    prompt = f"""# Benchmark Task Execution

You are executing a benchmark task. You MUST use tools (read, write, exec) to do real work.

**DO NOT just describe what you would do. Actually DO it.**
- Use `read` to read files
- Use `write` to create plan.md, challenge-report.md, eval-report.md, scores.json
- Use `exec` to run tests
- Use `edit` to fix code

## Task
**Name:** {task_name}
**Description:** {task_desc}
**Working directory:** {project_dir}

## Instructions

Execute the following 4-phase pipeline IN ORDER. Each phase produces specific artifacts.

### Phase 1: PLAN
Act as the Planner with these instructions:

<planner_instructions>
{planner_prompt}
</planner_instructions>

**Input:** The task description above + the project files in {project_dir}
**Output:** Write `plan.md` to {project_dir}/plan.md

### Phase 2: BUILD
Act as the Generator with these instructions:

<generator_instructions>
{generator_prompt}
</generator_instructions>

**Input:** The plan.md you just wrote + the project files
**Output:** Implement the features. Write code, run tests.

### Phase 3: CHALLENGE
Act as the Adversary with these instructions:

<adversary_instructions>
{adversary_prompt}
</adversary_instructions>

**Input:** plan.md + all code changes
**Output:** Write `challenge-report.md` to {project_dir}/challenge-report.md

### Phase 4: EVALUATE
Act as the Evaluator with these instructions:

<evaluator_instructions>
{evaluator_prompt}
</evaluator_instructions>

**Input:** plan.md + challenge-report.md + all code
**Output:** Write `eval-report.md` to {project_dir}/eval-report.md

## CRITICAL RULES

1. Execute ALL 4 phases. Do not skip any.
2. Write ALL artifacts to the project directory: plan.md, challenge-report.md, eval-report.md
3. If the eval says FAIL and you have time, do ONE retry cycle: BUILD(fix) → CHALLENGE → EVAL
4. Maximum 2 rounds total (initial + 1 retry)
5. At the end, write a `scores.json` to {project_dir}/ with this EXACT format:

```json
{{
    "task_id": "{task.get('id', 'unknown')}",
    "status": "completed",
    "pass": true/false,
    "eval_grade": "PASS" or "FAIL",
    "rounds": 1 or 2,
    "dod_total": <number>,
    "dod_passed": <number>,
    "notes": "brief summary"
}}
```

6. Work in the project directory. Do NOT create files outside it.
7. You MUST use tools (read, write, edit, exec) to do actual work. Do NOT just describe actions — execute them.
8. Start by reading the project files with the `read` tool.
"""
    
    return prompt


def setup_project(task: dict, fixtures_base: str, work_dir: str) -> str:
    """Set up the project directory from task fixture."""
    scaffold = task.get("scaffold", "")
    
    if scaffold:
        fixture_dir = os.path.join(fixtures_base, os.path.basename(scaffold.rstrip("/")))
        if os.path.isdir(fixture_dir):
            # Copy fixture to working directory
            task_work = os.path.join(work_dir, task["id"])
            shutil.copytree(fixture_dir, task_work, dirs_exist_ok=True)
            return task_work
    
    # No fixture — create minimal project dir
    task_work = os.path.join(work_dir, task["id"])
    os.makedirs(task_work, exist_ok=True)
    
    # Write task description as README
    Path(os.path.join(task_work, "README.md")).write_text(
        f"# {task.get('name', 'Task')}\n\n{task.get('description', '')}\n"
    )
    
    return task_work


def parse_scores_from_output(project_dir: str, task_id: str, elapsed: float) -> dict:
    """Parse the scores.json written by the subagent, or extract from eval-report.md."""
    
    scores_path = os.path.join(project_dir, "scores.json")
    if os.path.isfile(scores_path):
        try:
            scores = json.loads(Path(scores_path).read_text())
            scores["elapsed_seconds"] = round(elapsed, 2)
            return scores
        except json.JSONDecodeError:
            pass
    
    # Fallback: parse eval-report.md for PASS/FAIL
    eval_path = os.path.join(project_dir, "eval-report.md")
    if os.path.isfile(eval_path):
        content = Path(eval_path).read_text().lower()
        passed = "overall: pass" in content or "## overall: pass" in content
        
        # Try to count DoD items
        pass_count = content.count("✅")
        fail_count = content.count("❌")
        total = pass_count + fail_count
        
        return {
            "task_id": task_id,
            "status": "completed",
            "pass": passed,
            "eval_grade": "PASS" if passed else "FAIL",
            "rounds": 1,
            "dod_total": total,
            "dod_passed": pass_count,
            "elapsed_seconds": round(elapsed, 2),
            "total_tokens": 0,
            "parsed_from": "eval-report.md",
        }
    
    # No output at all
    return {
        "task_id": task_id,
        "status": "error",
        "pass": False,
        "eval_grade": "F",
        "rounds": 0,
        "elapsed_seconds": round(elapsed, 2),
        "total_tokens": 0,
        "error": "No scores.json or eval-report.md found",
    }


def collect_traces(project_dir: str, output_dir: str):
    """Copy all execution artifacts to the trace output directory."""
    artifacts_dir = os.path.join(output_dir, "run-artifacts")
    os.makedirs(artifacts_dir, exist_ok=True)
    
    for artifact in ["plan.md", "challenge-report.md", "eval-report.md", "scores.json"]:
        src = os.path.join(project_dir, artifact)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(artifacts_dir, artifact))
    
    # Also copy any test output
    for pattern in ["test_*.py", "*.test.ts", "*.test.js"]:
        import glob
        for f in glob.glob(os.path.join(project_dir, "**", pattern), recursive=True):
            rel = os.path.relpath(f, project_dir)
            dst = os.path.join(artifacts_dir, "project", rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(f, dst)


if __name__ == "__main__":
    # Standalone test
    import argparse
    parser = argparse.ArgumentParser(description="Execute a single benchmark task")
    parser.add_argument("task_json", help="Path to task.json or inline JSON")
    parser.add_argument("prompts_dir", help="Path to candidate harness/prompts/ directory")
    parser.add_argument("--output", "-o", default=".", help="Output directory")
    args = parser.parse_args()
    
    if os.path.isfile(args.task_json):
        task = json.loads(Path(args.task_json).read_text())
    else:
        task = json.loads(args.task_json)
    
    prompts = {}
    prompts_dir = Path(args.prompts_dir)
    for pfile in prompts_dir.glob("*.md"):
        prompts[pfile.stem] = pfile.read_text()
    
    prompt = build_orchestrator_prompt(task, prompts, args.output)
    print(prompt)
