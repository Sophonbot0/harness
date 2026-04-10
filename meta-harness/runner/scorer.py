#!/usr/bin/env python3
"""
Scorer — Multi-objective scoring for harness candidates.

Computes per-candidate scores from evaluation results and maintains
a leaderboard. Follows the paper's multi-objective / Pareto approach.
"""

import json
import os
from pathlib import Path
from typing import Any


GRADE_MAP = {
    "A+": 1.0, "A": 0.95, "A-": 0.9,
    "B+": 0.85, "B": 0.8, "B-": 0.75,
    "C+": 0.7, "C": 0.65, "C-": 0.6,
    "D+": 0.55, "D": 0.5, "D-": 0.45,
    "F": 0.0,
    "PASS": 1.0, "FAIL": 0.0, "PARTIAL": 0.5,
}


def score_candidate(evaluation_dir: str) -> dict:
    """Compute scores for a candidate from its evaluation directory.
    
    Reads task results from evaluation/tasks/*/scores.json and computes aggregates.
    """
    tasks_dir = os.path.join(evaluation_dir, "tasks")
    if not os.path.isdir(tasks_dir):
        return {"error": f"No tasks directory found in {evaluation_dir}"}
    
    task_results = []
    for task_name in sorted(os.listdir(tasks_dir)):
        scores_path = os.path.join(tasks_dir, task_name, "scores.json")
        if os.path.isfile(scores_path):
            try:
                scores = json.loads(Path(scores_path).read_text())
                task_results.append(scores)
            except json.JSONDecodeError:
                task_results.append({"task_id": task_name, "status": "error", "pass": False})
    
    if not task_results:
        return {"error": "No task results found"}
    
    total = len(task_results)
    passed = sum(1 for t in task_results if t.get("pass", False))
    
    # Core metrics
    pass_rate = passed / total if total > 0 else 0.0
    
    # Average eval grade
    grades = [GRADE_MAP.get(t.get("eval_grade", "F"), 0.0) for t in task_results]
    avg_grade = sum(grades) / len(grades) if grades else 0.0
    
    # Average rounds
    rounds = [t.get("rounds", 1) for t in task_results if t.get("status") != "error"]
    avg_rounds = sum(rounds) / len(rounds) if rounds else 1.0
    
    # Average time
    times = [t.get("elapsed_seconds", 0) for t in task_results if t.get("status") != "error"]
    avg_time = sum(times) / len(times) if times else 0.0
    
    # Stuck rate
    stuck = sum(1 for t in task_results if t.get("status") in ("stuck", "timeout", "error"))
    stuck_rate = stuck / total if total > 0 else 0.0
    
    # Token cost
    tokens = [t.get("total_tokens", 0) for t in task_results]
    avg_tokens = sum(tokens) / len(tokens) if tokens else 0
    
    scores = {
        "task_count": total,
        "passed": passed,
        "pass_rate": round(pass_rate, 4),
        "eval_grade": round(avg_grade, 4),
        "avg_rounds": round(avg_rounds, 2),
        "avg_time_seconds": round(avg_time, 1),
        "stuck_rate": round(stuck_rate, 4),
        "token_cost": round(avg_tokens, 0),
        "task_results": task_results,
    }
    
    # Composite score
    scores["composite"] = round(
        0.4 * pass_rate +
        0.3 * avg_grade +
        0.1 * max(0, 1 - (avg_rounds - 1) / 4) +  # normalize: 1 round = 1.0, 5 rounds = 0.0
        0.1 * max(0, 1 - avg_time / 3600) +         # normalize: 0s = 1.0, 3600s = 0.0
        0.1 * (1 - stuck_rate),
        4
    )
    
    return scores


def compare_candidates(scores_a: dict, scores_b: dict) -> dict:
    """Compare two candidates, return deltas."""
    deltas = {}
    for key in ["pass_rate", "eval_grade", "avg_rounds", "avg_time_seconds", "stuck_rate", "composite"]:
        a_val = scores_a.get(key, 0)
        b_val = scores_b.get(key, 0)
        deltas[key] = round(b_val - a_val, 4)
    return deltas
