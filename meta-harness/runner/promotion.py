#!/usr/bin/env python3
"""
Promotion Gate — Decides when to promote a candidate to active harness.

Uses holdout set evaluation (never seen by proposer) and Pareto dominance
check against baseline.

Paper: "We run evolution for a fixed number of iterations and perform
a final test-set evaluation on the Pareto frontier."
"""

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from scorer import compare_candidates
from frontier import load_frontier


def evaluate_promotion(
    candidate_scores: dict,
    baseline_scores: dict,
    max_regression: float = 0.05,
    min_holdout_pass_rate: float = 0.7,
) -> dict:
    """Evaluate whether a candidate should be promoted over baseline.
    
    Returns:
        Promotion decision dict with rationale.
    """
    decision = {
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        "candidate_composite": candidate_scores.get("composite", 0),
        "baseline_composite": baseline_scores.get("composite", 0),
    }
    
    # Check pass rate on holdout
    holdout_pass_rate = candidate_scores.get("pass_rate", 0)
    if holdout_pass_rate < min_holdout_pass_rate:
        decision["promoted"] = False
        decision["reason"] = f"Holdout pass rate {holdout_pass_rate:.1%} < minimum {min_holdout_pass_rate:.1%}"
        return decision
    
    # Check for regressions
    deltas = compare_candidates(baseline_scores, candidate_scores)
    decision["deltas"] = deltas
    
    regressions = {}
    for metric in ["pass_rate", "eval_grade"]:
        if deltas.get(metric, 0) < -max_regression:
            regressions[metric] = deltas[metric]
    
    for metric in ["stuck_rate"]:
        if deltas.get(metric, 0) > max_regression:
            regressions[metric] = deltas[metric]
    
    if regressions:
        decision["promoted"] = False
        decision["reason"] = f"Regression on: {regressions}"
        decision["regressions"] = regressions
        return decision
    
    # Check overall improvement
    if candidate_scores.get("composite", 0) <= baseline_scores.get("composite", 0):
        decision["promoted"] = False
        decision["reason"] = "No improvement over baseline (composite score equal or lower)"
        return decision
    
    # All checks pass — promote
    decision["promoted"] = True
    decision["reason"] = (
        f"Candidate improves over baseline: "
        f"composite {baseline_scores.get('composite', 0):.4f} → {candidate_scores.get('composite', 0):.4f} "
        f"(+{deltas.get('composite', 0):+.4f})"
    )
    
    return decision


def promote_candidate(
    candidate_dir: str,
    active_dir: str,
    backup_dir: str,
    decision: dict,
):
    """Promote a candidate to active, backing up the current active version."""
    # Backup current active
    if os.path.exists(active_dir):
        backup_path = os.path.join(
            backup_dir,
            f"backup-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}"
        )
        shutil.copytree(active_dir, backup_path)
    
    # Copy candidate's harness to active
    candidate_harness = os.path.join(candidate_dir, "harness")
    active_harness = os.path.join(active_dir, "harness")
    
    if os.path.exists(active_harness):
        shutil.rmtree(active_harness)
    
    shutil.copytree(candidate_harness, active_harness)
    
    # Write promotion record
    Path(os.path.join(active_dir, "promotion.json")).write_text(
        json.dumps(decision, indent=2)
    )


def generate_promotion_report(decision: dict, candidate_id: str, baseline_id: str) -> str:
    """Generate human-readable promotion report."""
    status = "✅ PROMOTED" if decision.get("promoted") else "❌ NOT PROMOTED"
    
    report = f"""# Promotion Report

## Decision: {status}

## Candidate: {candidate_id}
## Baseline: {baseline_id}

## Reason
{decision.get('reason', 'N/A')}

## Score Comparison

| Metric | Baseline | Candidate | Delta |
|--------|----------|-----------|-------|
"""
    deltas = decision.get("deltas", {})
    for metric in ["pass_rate", "eval_grade", "avg_rounds", "avg_time_seconds", "stuck_rate", "composite"]:
        delta_val = deltas.get(metric, 0)
        direction = "↑" if delta_val > 0 else "↓" if delta_val < 0 else "→"
        report += f"| {metric} | {decision.get(f'baseline_{metric}', 'N/A')} | {decision.get(f'candidate_{metric}', 'N/A')} | {delta_val:+.4f} {direction} |\n"
    
    report += f"""
## Timestamp
{decision.get('timestamp', 'N/A')}
"""
    
    return report
