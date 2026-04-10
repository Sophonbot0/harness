#!/usr/bin/env python3
"""
Benchmark Runner — Evaluates a harness candidate against a task set.

This is the core evaluation engine. It takes a candidate harness directory
and a set of benchmark tasks, runs each task through the harness pipeline,
and captures full execution traces.

Paper principle: "Each evaluated harness contributes a directory containing
its source code, scores, and execution traces."

Execution modes:
  --dry-run    : Validate structure only (no LLM calls)
  --simulate   : Use lightweight LLM scoring (fast, cheap, approximate)
  (default)    : Full subagent execution via OpenClaw sessions_spawn

The runner outputs everything the proposer needs for diagnosis:
  - Raw prompts used per task
  - Full plan.md, challenge-report.md, eval-report.md  
  - Structured scores.json per task
  - Aggregate metrics
"""

import json
import os
import shutil
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

# Add runner dir to path
sys.path.insert(0, str(Path(__file__).parent))

from validator import validate_and_report
from scorer import score_candidate
from task_executor import (
    build_orchestrator_prompt,
    setup_project,
    parse_scores_from_output,
    collect_traces,
)


META_HARNESS_DIR = Path(__file__).parent.parent
FIXTURES_DIR = META_HARNESS_DIR / "fixtures"


def load_task_set(task_set_path: str) -> list:
    """Load a task set from a JSON file."""
    data = json.loads(Path(task_set_path).read_text())
    return data.get("tasks", [])


def load_candidate_prompts(candidate_dir: str) -> dict:
    """Load all prompts from a candidate harness directory."""
    harness_dir = os.path.join(candidate_dir, "harness")
    prompts = {}
    
    for prompt_name in ["planner-system", "generator-system", "adversary-system", "evaluator-system"]:
        prompt_path = os.path.join(harness_dir, "prompts", f"{prompt_name}.md")
        if os.path.isfile(prompt_path):
            prompts[prompt_name] = Path(prompt_path).read_text()
    
    skill_path = os.path.join(harness_dir, "SKILL.md")
    if os.path.isfile(skill_path):
        prompts["skill"] = Path(skill_path).read_text()
    
    return prompts


def evaluate_task_dry_run(task: dict, prompts: dict, output_dir: str) -> dict:
    """Dry-run: validate structure without execution."""
    task_id = task["id"]
    task_dir = os.path.join(output_dir, task_id)
    os.makedirs(task_dir, exist_ok=True)
    
    Path(os.path.join(task_dir, "input.json")).write_text(json.dumps(task, indent=2))
    Path(os.path.join(task_dir, "prompts_used.json")).write_text(
        json.dumps({k: f"{len(v)} chars" for k, v in prompts.items()}, indent=2)
    )
    
    result = {
        "task_id": task_id,
        "status": "dry_run",
        "pass": False,
        "eval_grade": "N/A",
        "rounds": 0,
        "elapsed_seconds": 0.1,
        "total_tokens": 0,
        "dry_run": True,
    }
    
    Path(os.path.join(task_dir, "scores.json")).write_text(json.dumps(result, indent=2))
    return result


def evaluate_task_live(task: dict, prompts: dict, output_dir: str,
                       work_dir: str, timeout_minutes: int = 30,
                       verbose: bool = False) -> dict:
    """Live execution: run full pipeline via subagent.
    
    This creates the orchestrator prompt and writes it to a file that
    can be passed to `sessions_spawn` by the Meta-Harness orchestrator.
    
    The actual spawning happens at the meta-harness level (run_meta_harness.py)
    because it needs access to the OpenClaw session API.
    
    This function:
    1. Sets up the project directory from fixtures
    2. Builds the orchestrator prompt with injected candidate prompts
    3. Writes the prompt + metadata for the spawner
    4. After execution (project_dir populated by subagent), parses results
    """
    task_id = task["id"]
    task_dir = os.path.join(output_dir, task_id)
    os.makedirs(task_dir, exist_ok=True)
    
    start_time = time.time()
    
    # Save task input
    Path(os.path.join(task_dir, "input.json")).write_text(json.dumps(task, indent=2))
    
    # Save full prompts (for proposer to inspect later)
    Path(os.path.join(task_dir, "prompts_used.json")).write_text(
        json.dumps({k: v for k, v in prompts.items()}, indent=2)
    )
    
    # Set up project from fixture
    project_dir = setup_project(task, str(FIXTURES_DIR), work_dir)
    
    # Build the orchestrator prompt
    orchestrator_prompt = build_orchestrator_prompt(task, prompts, project_dir)
    
    # Write the spawn instruction file
    spawn_instruction = {
        "task_id": task_id,
        "task_name": task.get("name", task_id),
        "project_dir": project_dir,
        "orchestrator_prompt": orchestrator_prompt,
        "timeout_minutes": timeout_minutes,
        "created_at": datetime.now(timezone.utc).isoformat() + "Z",
    }
    
    instruction_path = os.path.join(task_dir, "spawn_instruction.json")
    Path(instruction_path).write_text(json.dumps(spawn_instruction, indent=2))
    
    # Write the orchestrator prompt as a standalone file (easy to read)
    prompt_path = os.path.join(task_dir, "orchestrator_prompt.md")
    Path(prompt_path).write_text(orchestrator_prompt)
    
    if verbose:
        print(f"    → Project dir: {project_dir}")
        print(f"    → Orchestrator prompt: {prompt_path}")
        print(f"    → Ready for subagent spawn")
    
    elapsed = time.time() - start_time
    
    # Check if the subagent already ran (results exist)
    scores = parse_scores_from_output(project_dir, task_id, elapsed)
    
    if scores.get("status") == "error" and "No scores.json" in scores.get("error", ""):
        # Subagent hasn't run yet — mark as pending
        scores = {
            "task_id": task_id,
            "status": "pending_execution",
            "pass": False,
            "eval_grade": "N/A",
            "rounds": 0,
            "elapsed_seconds": round(elapsed, 2),
            "total_tokens": 0,
            "spawn_instruction": instruction_path,
            "project_dir": project_dir,
        }
    else:
        # Subagent completed — collect traces
        collect_traces(project_dir, task_dir)
    
    Path(os.path.join(task_dir, "scores.json")).write_text(json.dumps(scores, indent=2))
    return scores


def run_benchmark(
    candidate_dir: str,
    task_set_path: str,
    output_dir: str,
    dry_run: bool = False,
    verbose: bool = False,
    timeout_minutes: int = 30,
) -> dict:
    """Run a full benchmark evaluation of a candidate harness.
    
    Args:
        candidate_dir: Path to candidate directory (with harness/ subdirectory)
        task_set_path: Path to task set JSON file
        output_dir: Where to write evaluation results
        dry_run: If True, validate structure without executing tasks
        verbose: Print progress
        timeout_minutes: Max time per task
    
    Returns:
        Evaluation summary dict
    """
    run_id = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    eval_dir = os.path.join(output_dir, "evaluation")
    os.makedirs(eval_dir, exist_ok=True)
    
    # Step 1: Validate candidate
    if verbose:
        print(f"[{run_id}] Validating candidate: {candidate_dir}")
    
    validation = validate_and_report(candidate_dir)
    Path(os.path.join(eval_dir, "validation.json")).write_text(
        json.dumps(validation, indent=2)
    )
    
    if not validation["is_valid"]:
        result = {
            "run_id": run_id,
            "candidate_dir": candidate_dir,
            "status": "invalid",
            "validation": validation,
            "scores": None,
        }
        Path(os.path.join(eval_dir, "aggregate.json")).write_text(
            json.dumps(result, indent=2)
        )
        return result
    
    # Step 2: Load prompts
    prompts = load_candidate_prompts(candidate_dir)
    if verbose:
        print(f"[{run_id}] Loaded {len(prompts)} prompts")
    
    # Step 3: Load tasks
    tasks = load_task_set(task_set_path)
    if verbose:
        print(f"[{run_id}] Loaded {len(tasks)} tasks from {task_set_path}")
    
    # Step 4: Create work directory for live execution
    work_dir = os.path.join(output_dir, "workspaces")
    os.makedirs(work_dir, exist_ok=True)
    
    # Step 5: Evaluate each task
    tasks_dir = os.path.join(eval_dir, "tasks")
    os.makedirs(tasks_dir, exist_ok=True)
    
    task_results = []
    pending_spawns = []
    
    for i, task in enumerate(tasks):
        if verbose:
            print(f"[{run_id}] Task {i+1}/{len(tasks)}: {task['id']} — {task['name']}")
        
        if dry_run:
            result = evaluate_task_dry_run(task, prompts, tasks_dir)
        else:
            result = evaluate_task_live(
                task, prompts, tasks_dir, work_dir,
                timeout_minutes=timeout_minutes,
                verbose=verbose,
            )
            if result.get("status") == "pending_execution":
                pending_spawns.append(result)
        
        task_results.append(result)
    
    # Step 6: Score what we have
    scores = score_candidate(eval_dir)
    
    # Step 7: Build aggregate
    aggregate = {
        "run_id": run_id,
        "candidate_dir": candidate_dir,
        "task_set": task_set_path,
        "status": "completed" if not pending_spawns else "pending_execution",
        "task_count": len(tasks),
        "pending_count": len(pending_spawns),
        "validation": validation,
        "scores": scores,
        "evaluated_at": datetime.now(timezone.utc).isoformat() + "Z",
    }
    
    if pending_spawns:
        aggregate["pending_spawns"] = [
            {
                "task_id": s["task_id"],
                "spawn_instruction": s.get("spawn_instruction"),
                "project_dir": s.get("project_dir"),
            }
            for s in pending_spawns
        ]
    
    Path(os.path.join(eval_dir, "aggregate.json")).write_text(
        json.dumps(aggregate, indent=2)
    )
    
    if verbose:
        print(f"\n[{run_id}] Evaluation complete")
        if pending_spawns:
            print(f"  ⏳ {len(pending_spawns)} tasks pending subagent execution")
            print(f"  📋 Spawn instructions written to evaluation/tasks/*/spawn_instruction.json")
            print(f"  🔄 Re-run after spawns complete to collect results")
        print(f"  📊 Scores: {json.dumps({k:v for k,v in scores.items() if k != 'task_results'}, indent=2)}")
    
    return aggregate


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Benchmark Runner for Meta-Harness")
    parser.add_argument("candidate_dir", help="Path to candidate harness directory")
    parser.add_argument("task_set", help="Path to task set JSON file")
    parser.add_argument("--output", "-o", default=None, help="Output directory (default: candidate_dir)")
    parser.add_argument("--dry-run", action="store_true", help="Validate without executing")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print progress")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout per task in minutes")
    
    args = parser.parse_args()
    output = args.output or args.candidate_dir
    
    result = run_benchmark(
        args.candidate_dir,
        args.task_set,
        output,
        dry_run=args.dry_run,
        verbose=args.verbose,
        timeout_minutes=args.timeout,
    )
    
    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get("status") != "invalid" else 1)
