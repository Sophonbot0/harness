#!/usr/bin/env python3
"""
Scorer — canonical Phase 2 scoring for benchmark candidates.

Computes multi-objective metrics from per-task scores and exposes richer
breakdowns so the benchmark suite can act as a real control surface.
"""

from __future__ import annotations

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
    "PASS": 1.0, "FAIL": 0.0, "PARTIAL": 0.5, "N/A": 0.0,
}


def _load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text())


def _load_objectives(objectives_path: str | Path | None) -> dict[str, Any]:
    if objectives_path and Path(objectives_path).is_file():
        return _load_json(objectives_path)
    return {
        "objectives": [
            {"id": "pass_rate", "weight": 0.35},
            {"id": "eval_grade", "weight": 0.25},
            {"id": "avg_rounds", "weight": 0.1, "direction": "minimize"},
            {"id": "avg_time_seconds", "weight": 0.05, "direction": "minimize"},
            {"id": "stuck_rate", "weight": 0.08, "direction": "minimize"},
            {"id": "dod_coverage", "weight": 0.07},
            {"id": "artifact_validity_rate", "weight": 0.05},
            {"id": "regression_rate", "weight": 0.05, "direction": "minimize"},
        ],
        "pareto_dimensions": ["pass_rate", "avg_time_seconds", "token_cost", "dod_coverage"],
    }


def _collect_task_results(evaluation_dir: str) -> list[dict[str, Any]]:
    tasks_dir = Path(evaluation_dir) / "tasks"
    if not tasks_dir.is_dir():
        return []

    task_results: list[dict[str, Any]] = []
    for task_name in sorted(os.listdir(tasks_dir)):
        scores_path = tasks_dir / task_name / "scores.json"
        if scores_path.is_file():
            try:
                scores = _load_json(scores_path)
                scores.setdefault("task_id", task_name)
                task_results.append(scores)
            except json.JSONDecodeError:
                task_results.append({"task_id": task_name, "status": "error", "pass": False, "eval_grade": "F"})
    return task_results


def _safe_avg(values: list[float], default: float = 0.0) -> float:
    return sum(values) / len(values) if values else default


def _norm_minimize(value: float, lower: float, upper: float) -> float:
    if upper <= lower:
        return 1.0
    clamped = min(max(value, lower), upper)
    return max(0.0, 1.0 - ((clamped - lower) / (upper - lower)))


def _build_breakdown(task_results: list[dict[str, Any]], key: str) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for task in task_results:
        group = str(task.get(key) or "unknown")
        grouped.setdefault(group, []).append(task)

    breakdown = {}
    for group, items in grouped.items():
        total = len(items)
        passed = sum(1 for item in items if item.get("pass", False))
        dod_total = sum(int(item.get("dod_total", 0) or 0) for item in items)
        dod_passed = sum(int(item.get("dod_passed", 0) or 0) for item in items)
        breakdown[group] = {
            "task_count": total,
            "passed": passed,
            "pass_rate": round(passed / total if total else 0.0, 4),
            "dod_coverage": round(dod_passed / dod_total if dod_total else 1.0, 4),
        }
    return breakdown


def score_candidate(
    evaluation_dir: str,
    objectives_path: str | Path | None = None,
    task_bundle: dict[str, Any] | None = None,
) -> dict[str, Any]:
    task_results = _collect_task_results(evaluation_dir)
    if not task_results:
        return {"error": f"No task results found in {evaluation_dir}"}

    objectives = _load_objectives(objectives_path)
    total = len(task_results)
    passed = sum(1 for t in task_results if t.get("pass", False))
    pending = sum(1 for t in task_results if t.get("status") == "pending_execution")
    pass_rate = passed / total if total else 0.0

    grades = [GRADE_MAP.get(str(t.get("eval_grade", "F")).upper(), 0.0) for t in task_results]
    avg_grade = _safe_avg(grades)

    completed_results = [t for t in task_results if t.get("status") not in ("error", "pending_execution")]
    rounds = [float(t.get("rounds", 1) or 1) for t in completed_results]
    times = [float(t.get("elapsed_seconds", 0) or 0) for t in completed_results]
    tokens = [float(t.get("total_tokens", 0) or 0) for t in task_results]

    stuck = sum(1 for t in task_results if t.get("status") in ("stuck", "timeout", "error"))
    stuck_rate = stuck / total if total else 0.0
    pending_rate = pending / total if total else 0.0

    dod_total = sum(int(t.get("dod_total", 0) or 0) for t in task_results)
    dod_passed = sum(int(t.get("dod_passed", 0) or 0) for t in task_results)
    dod_coverage = dod_passed / dod_total if dod_total else 1.0

    artifact_values = [float(t.get("artifact_validity", 0.0) or 0.0) for t in task_results]
    artifact_validity_rate = _safe_avg(artifact_values, default=0.0)

    expected_tasks = {}
    if task_bundle:
        expected_tasks = {task["id"]: task for task in task_bundle.get("tasks", [])}
    regressions = 0
    for result in task_results:
        baseline_pass = bool(expected_tasks.get(result.get("task_id"), {}).get("baseline_pass", False))
        if baseline_pass and not result.get("pass", False):
            regressions += 1
    regression_rate = regressions / total if total else 0.0

    scores = {
        "task_count": total,
        "passed": passed,
        "pass_rate": round(pass_rate, 4),
        "eval_grade": round(avg_grade, 4),
        "avg_rounds": round(_safe_avg(rounds, default=1.0), 2),
        "avg_time_seconds": round(_safe_avg(times, default=0.0), 2),
        "stuck_rate": round(stuck_rate, 4),
        "pending_rate": round(pending_rate, 4),
        "token_cost": round(_safe_avg(tokens, default=0.0), 2),
        "dod_coverage": round(dod_coverage, 4),
        "artifact_validity_rate": round(artifact_validity_rate, 4),
        "regression_rate": round(regression_rate, 4),
        "total_dod": dod_total,
        "total_dod_passed": dod_passed,
        "category_breakdown": _build_breakdown(task_results, "category"),
        "difficulty_breakdown": _build_breakdown(task_results, "difficulty"),
        "task_results": task_results,
    }

    weights = {obj["id"]: float(obj.get("weight", 0.0)) for obj in objectives.get("objectives", [])}
    composite = 0.0
    composite += weights.get("pass_rate", 0.35) * pass_rate
    composite += weights.get("eval_grade", 0.25) * avg_grade
    composite += weights.get("avg_rounds", 0.1) * _norm_minimize(scores["avg_rounds"], 1.0, 5.0)
    composite += weights.get("avg_time_seconds", 0.05) * _norm_minimize(scores["avg_time_seconds"], 60.0, 3600.0)
    composite += weights.get("stuck_rate", 0.08) * (1.0 - stuck_rate)
    composite += weights.get("artifact_validity_rate", 0.0) * artifact_validity_rate
    composite += weights.get("dod_coverage", 0.0) * dod_coverage
    composite += weights.get("regression_rate", 0.0) * (1.0 - regression_rate)
    scores["composite"] = round(composite, 4)
    scores["pareto_dimensions"] = objectives.get("pareto_dimensions", ["pass_rate", "avg_time_seconds", "token_cost", "dod_coverage"])
    scores["objectives_used"] = weights
    scores["leaderboard_row"] = {
        "composite": scores["composite"],
        "pass_rate": scores["pass_rate"],
        "dod_coverage": scores["dod_coverage"],
        "artifact_validity_rate": scores["artifact_validity_rate"],
        "eval_grade": scores["eval_grade"],
        "avg_rounds": scores["avg_rounds"],
        "avg_time_seconds": scores["avg_time_seconds"],
        "stuck_rate": scores["stuck_rate"],
        "regression_rate": scores["regression_rate"],
    }
    return scores


def compare_candidates(scores_a: dict[str, Any], scores_b: dict[str, Any]) -> dict[str, float]:
    deltas = {}
    for key in [
        "pass_rate",
        "eval_grade",
        "avg_rounds",
        "avg_time_seconds",
        "stuck_rate",
        "dod_coverage",
        "artifact_validity_rate",
        "regression_rate",
        "composite",
    ]:
        a_val = float(scores_a.get(key, 0) or 0)
        b_val = float(scores_b.get(key, 0) or 0)
        deltas[key] = round(b_val - a_val, 4)
    return deltas
