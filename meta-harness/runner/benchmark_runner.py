#!/usr/bin/env python3
"""
Benchmark Runner — Evaluates a harness candidate against a task set.

This is the core evaluation engine. It takes a candidate harness directory
and a set of benchmark tasks, runs each task through the harness pipeline,
and captures full execution traces.

Paper principle: "Each evaluated harness contributes a directory containing
its source code, scores, and execution traces."

For v1, "evaluation" simulates the harness pipeline by:
1. Loading the candidate's prompts
2. For each task: spawning a planner→generator→adversary→evaluator chain
3. Capturing all outputs as traces
4. Scoring results

In production, this would use the actual OpenClaw harness pipeline.
For Meta-Harness search, we use a lightweight simulation that captures
the same signals at lower cost.
"""

import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Add runner dir to path
sys.path.insert(0, str(Path(__file__).parent))

from validator import validate_and_report
from scorer import score_candidate


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


def evaluate_task(task: dict, prompts: dict, output_dir: str, dry_run: bool = False) -> dict:
    """Evaluate a single task with the given harness prompts.
    
    In dry-run mode, returns a synthetic result without actual execution.
    In full mode, this would spawn actual subagents.
    """
    task_id = task["id"]
    task_dir = os.path.join(output_dir, task_id)
    os.makedirs(task_dir, exist_ok=True)
    
    start_time = time.time()
    
    # Save task input
    Path(os.path.join(task_dir, "input.json")).write_text(
        json.dumps(task, indent=2)
    )
    
    # Save prompts used (for trace)
    Path(os.path.join(task_dir, "prompts_used.json")).write_text(
        json.dumps({k: f"{len(v)} chars" for k, v in prompts.items()}, indent=2)
    )
    
    if dry_run:
        # Synthetic result for validation
        elapsed = 0.1
        result = {
            "task_id": task_id,
            "status": "dry_run",
            "pass": False,
            "eval_grade": "N/A",
            "rounds": 0,
            "elapsed_seconds": elapsed,
            "total_tokens": 0,
            "dry_run": True,
        }
    else:
        # TODO: In production, this spawns actual subagents via OpenClaw
        # For now, we create a placeholder that captures the structure
        elapsed = time.time() - start_time
        
        # Create trace artifacts (empty templates)
        for artifact in ["plan.md", "challenge-report.md", "eval-report.md"]:
            artifact_path = os.path.join(task_dir, "run-artifacts", artifact)
            os.makedirs(os.path.dirname(artifact_path), exist_ok=True)
            Path(artifact_path).write_text(f"# {artifact}\n\n[Awaiting execution]\n")
        
        result = {
            "task_id": task_id,
            "status": "pending_execution",
            "pass": False,
            "eval_grade": "N/A",
            "rounds": 0,
            "elapsed_seconds": round(elapsed, 2),
            "total_tokens": 0,
            "needs_execution": True,
        }
    
    # Save scores
    Path(os.path.join(task_dir, "scores.json")).write_text(
        json.dumps(result, indent=2)
    )
    
    return result


def run_benchmark(
    candidate_dir: str,
    task_set_path: str,
    output_dir: str,
    dry_run: bool = False,
    verbose: bool = False,
) -> dict:
    """Run a full benchmark evaluation of a candidate harness.
    
    Args:
        candidate_dir: Path to candidate directory (with harness/ subdirectory)
        task_set_path: Path to task set JSON file
        output_dir: Where to write evaluation results
        dry_run: If True, validate structure without executing tasks
        verbose: Print progress
    
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
    
    # Step 4: Evaluate each task
    tasks_dir = os.path.join(eval_dir, "tasks")
    os.makedirs(tasks_dir, exist_ok=True)
    
    task_results = []
    for i, task in enumerate(tasks):
        if verbose:
            print(f"[{run_id}] Task {i+1}/{len(tasks)}: {task['id']} — {task['name']}")
        
        result = evaluate_task(task, prompts, tasks_dir, dry_run=dry_run)
        task_results.append(result)
    
    # Step 5: Score
    scores = score_candidate(eval_dir)
    
    # Step 6: Build aggregate
    aggregate = {
        "run_id": run_id,
        "candidate_dir": candidate_dir,
        "task_set": task_set_path,
        "status": "completed" if not dry_run else "dry_run",
        "task_count": len(tasks),
        "validation": validation,
        "scores": scores,
        "evaluated_at": datetime.now(timezone.utc).isoformat() + "Z",
    }
    
    Path(os.path.join(eval_dir, "aggregate.json")).write_text(
        json.dumps(aggregate, indent=2)
    )
    
    if verbose:
        print(f"[{run_id}] Evaluation complete: {json.dumps(scores, indent=2)}")
    
    return aggregate


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Benchmark Runner for Meta-Harness")
    parser.add_argument("candidate_dir", help="Path to candidate harness directory")
    parser.add_argument("task_set", help="Path to task set JSON file")
    parser.add_argument("--output", "-o", default=None, help="Output directory (default: candidate_dir)")
    parser.add_argument("--dry-run", action="store_true", help="Validate without executing")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print progress")
    
    args = parser.parse_args()
    output = args.output or args.candidate_dir
    
    result = run_benchmark(
        args.candidate_dir,
        args.task_set,
        output,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )
    
    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get("status") != "invalid" else 1)
