#!/usr/bin/env python3
"""
Frontier — Pareto frontier tracking for Meta-Harness candidates.

Maintains a population of evaluated harnesses and identifies the
Pareto-optimal set across multiple objectives.

Paper: "Meta-Harness maintains a population H and a Pareto frontier
over evaluated harnesses."
"""

import json
import os
from pathlib import Path
from typing import List


def is_dominated(a: dict, b: dict, dimensions: list) -> bool:
    """Return True if candidate b Pareto-dominates candidate a.
    
    b dominates a iff b is >= a on all dimensions and > a on at least one.
    For 'minimize' objectives, we negate values before comparison.
    """
    direction_map = {
        "pass_rate": "maximize",
        "eval_grade": "maximize",
        "avg_rounds": "minimize",
        "avg_time_seconds": "minimize",
        "stuck_rate": "minimize",
        "token_cost": "minimize",
        "composite": "maximize",
    }
    
    at_least_one_better = False
    for dim in dimensions:
        direction = direction_map.get(dim, "maximize")
        av = a.get(dim, 0)
        bv = b.get(dim, 0)
        
        if direction == "minimize":
            av, bv = -av, -bv
        
        if bv < av:
            return False  # b is worse on this dimension
        if bv > av:
            at_least_one_better = True
    
    return at_least_one_better


def compute_frontier(candidates: List[dict], dimensions: list = None) -> List[dict]:
    """Compute the Pareto frontier from a list of scored candidates.
    
    Each candidate dict must have a 'scores' key with the metric values.
    
    Returns the list of non-dominated candidates.
    """
    if dimensions is None:
        dimensions = ["pass_rate", "avg_time_seconds", "token_cost"]
    
    frontier = []
    for i, c in enumerate(candidates):
        scores_c = c.get("scores", c)
        dominated = False
        for j, other in enumerate(candidates):
            if i == j:
                continue
            scores_o = other.get("scores", other)
            if is_dominated(scores_c, scores_o, dimensions):
                dominated = True
                break
        if not dominated:
            frontier.append(c)
    
    return frontier


def update_frontier_file(frontier_path: str, new_candidate: dict, dimensions: list = None):
    """Add a new candidate to the frontier file and recompute."""
    existing = []
    if os.path.isfile(frontier_path):
        try:
            data = json.loads(Path(frontier_path).read_text())
            if isinstance(data, dict):
                existing = data.get("all_candidates_full", [])
            elif isinstance(data, list):
                existing = data
        except json.JSONDecodeError:
            existing = []
    
    all_candidates = existing + [new_candidate]
    frontier = compute_frontier(all_candidates, dimensions)
    
    result = {
        "updated_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "total_evaluated": len(all_candidates),
        "frontier_size": len(frontier),
        "frontier": frontier,
        "all_candidates_full": all_candidates,
        "all_candidates": [
            {
                "id": c.get("id", "unknown"),
                "composite": c.get("scores", c).get("composite", 0),
                "pass_rate": c.get("scores", c).get("pass_rate", 0),
                "on_frontier": c in frontier,
            }
            for c in all_candidates
        ]
    }
    
    Path(frontier_path).write_text(json.dumps(result, indent=2))
    return result


def load_frontier(frontier_path: str) -> dict:
    """Load the current frontier state."""
    if not os.path.isfile(frontier_path):
        return {"frontier": [], "total_evaluated": 0, "frontier_size": 0}
    return json.loads(Path(frontier_path).read_text())
