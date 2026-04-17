#!/usr/bin/env python3
"""
Frontier — Pareto frontier tracking for Meta-Harness candidates.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_DIRECTIONS = {
    "pass_rate": "maximize",
    "eval_grade": "maximize",
    "dod_coverage": "maximize",
    "artifact_validity_rate": "maximize",
    "avg_rounds": "minimize",
    "avg_time_seconds": "minimize",
    "stuck_rate": "minimize",
    "token_cost": "minimize",
    "regression_rate": "minimize",
    "composite": "maximize",
}


def load_objective_directions(objectives_path: str | Path | None = None) -> dict[str, str]:
    directions = dict(DEFAULT_DIRECTIONS)
    if objectives_path and Path(objectives_path).is_file():
        payload = json.loads(Path(objectives_path).read_text())
        for objective in payload.get("objectives", []):
            directions[objective["id"]] = objective.get("direction", directions.get(objective["id"], "maximize"))
    return directions


def is_dominated(a: dict[str, Any], b: dict[str, Any], dimensions: list[str], directions: dict[str, str] | None = None) -> bool:
    directions = directions or DEFAULT_DIRECTIONS
    at_least_one_better = False
    for dim in dimensions:
        direction = directions.get(dim, "maximize")
        av = float(a.get(dim, 0) or 0)
        bv = float(b.get(dim, 0) or 0)
        if direction == "minimize":
            av, bv = -av, -bv
        if bv < av:
            return False
        if bv > av:
            at_least_one_better = True
    return at_least_one_better


def compute_frontier(candidates: list[dict[str, Any]], dimensions: list[str] | None = None, directions: dict[str, str] | None = None) -> list[dict[str, Any]]:
    if dimensions is None:
        dimensions = ["pass_rate", "avg_time_seconds", "token_cost"]
    frontier: list[dict[str, Any]] = []
    for i, candidate in enumerate(candidates):
        scores_c = candidate.get("scores", candidate)
        dominated = False
        for j, other in enumerate(candidates):
            if i == j:
                continue
            scores_o = other.get("scores", other)
            if is_dominated(scores_c, scores_o, dimensions, directions):
                dominated = True
                break
        if not dominated:
            frontier.append(candidate)
    return frontier


def update_frontier_file(
    frontier_path: str,
    new_candidate: dict[str, Any],
    dimensions: list[str] | None = None,
    objectives_path: str | Path | None = None,
):
    existing = []
    frontier_file = Path(frontier_path)
    if frontier_file.is_file():
        try:
            data = json.loads(frontier_file.read_text())
            existing = data.get("all_candidates_full", []) if isinstance(data, dict) else list(data)
        except json.JSONDecodeError:
            existing = []

    deduped: dict[str, dict[str, Any]] = {}
    for candidate in existing:
        deduped[str(candidate.get("id", "unknown"))] = candidate
    deduped[str(new_candidate.get("id", "unknown"))] = new_candidate

    all_candidates = sorted(deduped.values(), key=lambda c: str(c.get("id", "")))
    directions = load_objective_directions(objectives_path)
    frontier = compute_frontier(all_candidates, dimensions, directions)

    result = {
        "updated_at": datetime.now(timezone.utc).isoformat() + "Z",
        "total_evaluated": len(all_candidates),
        "frontier_size": len(frontier),
        "dimensions": dimensions or ["pass_rate", "avg_time_seconds", "token_cost"],
        "directions": directions,
        "frontier": frontier,
        "all_candidates_full": all_candidates,
        "all_candidates": [
            {
                "id": c.get("id", "unknown"),
                "composite": c.get("scores", c).get("composite", 0),
                "pass_rate": c.get("scores", c).get("pass_rate", 0),
                "dod_coverage": c.get("scores", c).get("dod_coverage", 0),
                "artifact_validity_rate": c.get("scores", c).get("artifact_validity_rate", 0),
                "on_frontier": any(f.get("id") == c.get("id") for f in frontier),
            }
            for c in all_candidates
        ],
    }
    frontier_file.write_text(json.dumps(result, indent=2))
    return result


def load_frontier(frontier_path: str) -> dict[str, Any]:
    path = Path(frontier_path)
    if not path.is_file():
        return {"frontier": [], "total_evaluated": 0, "frontier_size": 0}
    return json.loads(path.read_text())
