#!/usr/bin/env python3
"""
Benchmark Runner — evaluates a harness candidate against a benchmark task set.

Phase 2 upgrades:
- canonical task loading/validation
- dry-run, simulate, and live modes
- deterministic workspace manifests
- aggregate benchmark metadata for search/holdout discipline
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))

from scorer import score_candidate
from task_executor import (
    build_orchestrator_prompt,
    collect_traces,
    parse_scores_from_output,
    setup_project,
    simulate_task_result,
)
from task_registry import load_task_set
from validator import validate_and_report


META_HARNESS_DIR = Path(__file__).parent.parent
FIXTURES_DIR = META_HARNESS_DIR / "fixtures"
CONFIG_DIR = META_HARNESS_DIR / "config"


def load_candidate_prompts(candidate_dir: str) -> dict[str, str]:
    harness_dir = Path(candidate_dir) / "harness"
    prompts: dict[str, str] = {}
    for prompt_name in ["planner-system", "generator-system", "adversary-system", "evaluator-system"]:
        prompt_path = harness_dir / "prompts" / f"{prompt_name}.md"
        if prompt_path.is_file():
            prompts[prompt_name] = prompt_path.read_text()
    skill_path = harness_dir / "SKILL.md"
    if skill_path.is_file():
        prompts["skill"] = skill_path.read_text()
    return prompts


def evaluate_task_dry_run(task: dict[str, Any], prompts: dict[str, str], output_dir: str) -> dict[str, Any]:
    task_dir = Path(output_dir) / task["id"]
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "input.json").write_text(json.dumps(task, indent=2))
    (task_dir / "prompts_used.json").write_text(json.dumps({k: f"{len(v)} chars" for k, v in prompts.items()}, indent=2))

    result = {
        "task_id": task["id"],
        "status": "dry_run",
        "pass": False,
        "eval_grade": "N/A",
        "rounds": 0,
        "dod_total": int(task.get("expected_dod_count", 0)),
        "dod_passed": 0,
        "elapsed_seconds": 0.1,
        "total_tokens": 0,
        "artifact_validity": 0.0,
        "category": task.get("category"),
        "difficulty": task.get("difficulty"),
        "dry_run": True,
    }
    (task_dir / "scores.json").write_text(json.dumps(result, indent=2))
    return result


def evaluate_task_live(
    task: dict[str, Any],
    prompts: dict[str, str],
    output_dir: str,
    work_dir: str,
    timeout_minutes: int = 30,
    verbose: bool = False,
) -> dict[str, Any]:
    task_dir = Path(output_dir) / task["id"]
    task_dir.mkdir(parents=True, exist_ok=True)
    start_time = time.time()

    (task_dir / "input.json").write_text(json.dumps(task, indent=2))
    (task_dir / "prompts_used.json").write_text(json.dumps(prompts, indent=2))

    project_dir = setup_project(task, str(FIXTURES_DIR), work_dir)
    orchestrator_prompt = build_orchestrator_prompt(task, prompts, project_dir)

    spawn_instruction = {
        "task_id": task["id"],
        "task_name": task.get("name", task["id"]),
        "project_dir": project_dir,
        "orchestrator_prompt": orchestrator_prompt,
        "timeout_minutes": timeout_minutes,
        "created_at": datetime.now(timezone.utc).isoformat() + "Z",
        "verify_command": task.get("verify_command", "").replace("{project_dir}", project_dir),
        "expected_artifacts": task.get("expected_artifacts", []),
        "failure_modes": task.get("failure_modes", []),
    }

    instruction_path = task_dir / "spawn_instruction.json"
    instruction_path.write_text(json.dumps(spawn_instruction, indent=2))
    (task_dir / "orchestrator_prompt.md").write_text(orchestrator_prompt)

    if verbose:
        print(f"    → Project dir: {project_dir}")
        print(f"    → Prompt written: {task_dir / 'orchestrator_prompt.md'}")

    elapsed = time.time() - start_time
    scores = parse_scores_from_output(project_dir, task, elapsed)
    if scores.get("status") == "error" and "No scores.json" in scores.get("error", ""):
        scores = {
            "task_id": task["id"],
            "status": "pending_execution",
            "pass": False,
            "eval_grade": "N/A",
            "rounds": 0,
            "dod_total": int(task.get("expected_dod_count", 0)),
            "dod_passed": 0,
            "elapsed_seconds": round(elapsed, 2),
            "total_tokens": 0,
            "artifact_validity": 0.0,
            "spawn_instruction": str(instruction_path),
            "project_dir": project_dir,
            "category": task.get("category"),
            "difficulty": task.get("difficulty"),
        }
    else:
        scores.setdefault("category", task.get("category"))
        scores.setdefault("difficulty", task.get("difficulty"))
        scores.setdefault("artifact_validity", 0.0)
        collect_traces(project_dir, str(task_dir))

    (task_dir / "scores.json").write_text(json.dumps(scores, indent=2))
    return scores


def _write_benchmark_manifest(eval_dir: Path, aggregate: dict[str, Any]):
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat() + "Z",
        "task_count": aggregate.get("task_count", 0),
        "status": aggregate.get("status"),
        "task_set": aggregate.get("task_set"),
        "mode": aggregate.get("mode"),
        "validation_ok": aggregate.get("validation", {}).get("is_valid"),
    }
    (eval_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))


def _write_leaderboard(eval_dir: Path, candidate_dir: str, scores: dict[str, Any]):
    row = dict(scores.get("leaderboard_row", {}))
    row["candidate_dir"] = candidate_dir
    (eval_dir / "leaderboard.json").write_text(json.dumps({"rows": [row]}, indent=2))
    markdown = "\n".join([
        "# Leaderboard",
        "",
        "| candidate | composite | pass_rate | dod_coverage | artifact_validity | eval_grade | avg_rounds | avg_time_s | stuck_rate | regression_rate |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        f"| {Path(candidate_dir).name} | {row.get('composite', 0):.4f} | {row.get('pass_rate', 0):.4f} | {row.get('dod_coverage', 0):.4f} | {row.get('artifact_validity_rate', 0):.4f} | {row.get('eval_grade', 0):.4f} | {row.get('avg_rounds', 0):.2f} | {row.get('avg_time_seconds', 0):.2f} | {row.get('stuck_rate', 0):.4f} | {row.get('regression_rate', 0):.4f} |",
        "",
    ])
    (eval_dir / "leaderboard.md").write_text(markdown)


def run_benchmark(
    candidate_dir: str,
    task_set_path: str,
    output_dir: str,
    dry_run: bool = False,
    simulate: bool = False,
    verbose: bool = False,
    timeout_minutes: int = 30,
) -> dict[str, Any]:
    run_id = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    eval_dir = Path(output_dir) / "evaluation"
    eval_dir.mkdir(parents=True, exist_ok=True)

    validation = validate_and_report(candidate_dir)
    (eval_dir / "validation.json").write_text(json.dumps(validation, indent=2))
    if not validation["is_valid"]:
        result = {
            "run_id": run_id,
            "candidate_dir": candidate_dir,
            "status": "invalid",
            "mode": "dry_run" if dry_run else "simulate" if simulate else "live",
            "validation": validation,
            "scores": None,
        }
        (eval_dir / "aggregate.json").write_text(json.dumps(result, indent=2))
        _write_benchmark_manifest(eval_dir, result)
        return result

    task_bundle = load_task_set(task_set_path, FIXTURES_DIR)
    (eval_dir / "task-set.json").write_text(json.dumps(task_bundle, indent=2))
    if not task_bundle["is_valid"]:
        result = {
            "run_id": run_id,
            "candidate_dir": candidate_dir,
            "status": "invalid_task_set",
            "mode": "dry_run" if dry_run else "simulate" if simulate else "live",
            "validation": validation,
            "task_validation": task_bundle,
            "scores": None,
        }
        (eval_dir / "aggregate.json").write_text(json.dumps(result, indent=2))
        _write_benchmark_manifest(eval_dir, result)
        return result

    prompts = load_candidate_prompts(candidate_dir)
    tasks = task_bundle["tasks"]
    work_dir = Path(output_dir) / "workspaces"
    work_dir.mkdir(parents=True, exist_ok=True)
    tasks_dir = eval_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)

    task_results = []
    pending_spawns = []
    mode = "dry_run" if dry_run else "simulate" if simulate else "live"

    for i, task in enumerate(tasks):
        if verbose:
            print(f"[{run_id}] Task {i+1}/{len(tasks)}: {task['id']} — {task['name']} ({mode})")
        if dry_run:
            result = evaluate_task_dry_run(task, prompts, str(tasks_dir))
        elif simulate:
            task_dir = tasks_dir / task["id"]
            task_dir.mkdir(parents=True, exist_ok=True)
            (task_dir / "input.json").write_text(json.dumps(task, indent=2))
            (task_dir / "prompts_used.json").write_text(json.dumps({k: f"{len(v)} chars" for k, v in prompts.items()}, indent=2))
            result = simulate_task_result(task, prompts, str(tasks_dir))
        else:
            result = evaluate_task_live(task, prompts, str(tasks_dir), str(work_dir), timeout_minutes=timeout_minutes, verbose=verbose)
            if result.get("status") == "pending_execution":
                pending_spawns.append(result)
        task_results.append(result)

    scores = score_candidate(str(eval_dir), objectives_path=str(CONFIG_DIR / "objectives.json"), task_bundle=task_bundle)
    aggregate = {
        "run_id": run_id,
        "candidate_dir": candidate_dir,
        "task_set": task_set_path,
        "task_set_description": task_bundle.get("description"),
        "task_categories": task_bundle.get("categories", {}),
        "task_difficulties": task_bundle.get("difficulties", {}),
        "mode": mode,
        "status": "completed" if not pending_spawns else "pending_execution",
        "task_count": len(tasks),
        "pending_count": len(pending_spawns),
        "validation": validation,
        "scores": scores,
        "evaluated_at": datetime.now(timezone.utc).isoformat() + "Z",
    }
    if pending_spawns:
        aggregate["pending_spawns"] = [{
            "task_id": s["task_id"],
            "spawn_instruction": s.get("spawn_instruction"),
            "project_dir": s.get("project_dir"),
        } for s in pending_spawns]

    (eval_dir / "aggregate.json").write_text(json.dumps(aggregate, indent=2))
    _write_benchmark_manifest(eval_dir, aggregate)
    _write_leaderboard(eval_dir, candidate_dir, scores)

    if verbose:
        print(f"\n[{run_id}] Evaluation complete — status={aggregate['status']}")
        summary = {k: v for k, v in scores.items() if k not in {"task_results", "category_breakdown", "difficulty_breakdown"}}
        print(json.dumps(summary, indent=2))

    return aggregate


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Benchmark Runner for Meta-Harness")
    parser.add_argument("candidate_dir", help="Path to candidate harness directory")
    parser.add_argument("task_set", help="Path to task set JSON file")
    parser.add_argument("--output", "-o", default=None, help="Output directory (default: candidate_dir)")
    parser.add_argument("--dry-run", action="store_true", help="Validate without executing")
    parser.add_argument("--simulate", action="store_true", help="Simulate deterministic benchmark results")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print progress")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout per task in minutes")

    args = parser.parse_args()
    output = args.output or args.candidate_dir

    result = run_benchmark(
        args.candidate_dir,
        args.task_set,
        output,
        dry_run=args.dry_run,
        simulate=args.simulate,
        verbose=args.verbose,
        timeout_minutes=args.timeout,
    )
    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get("status") not in {"invalid", "invalid_task_set"} else 1)
