#!/usr/bin/env python3
"""
Auto-Promote — Automatically promote winning candidates after evaluation.

Called after all candidate evaluations complete. Compares candidates against
the current baseline, computes the Pareto frontier, and promotes the winner
if it strictly improves on the baseline.

Flow:
  1. Load all candidate scores from workspaces (scores.json per task)
  2. Load baseline scores (current seed-000 or active harness)
  3. Compare using multi-objective scoring
  4. If winner improves: copy harness → active, update frontier, log promotion
  5. If no improvement: log DISCARD with reason

This replaces manual "should I promote?" decisions with deterministic rules.
"""

import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add runner dir to path
sys.path.insert(0, str(Path(__file__).parent))

from scorer import score_candidate, compare_candidates, GRADE_MAP
from frontier import update_frontier_file, compute_frontier


META_HARNESS_DIR = Path(__file__).parent.parent
CANDIDATES_DIR = META_HARNESS_DIR / "candidates"
SEEDS_DIR = META_HARNESS_DIR / "seeds"
ACTIVE_DIR = META_HARNESS_DIR / "active"
FRONTIER_PATH = META_HARNESS_DIR / "frontier.json"
PROMOTIONS_LOG = META_HARNESS_DIR / "promotions.jsonl"


def collect_candidate_scores(candidate_dir: Path) -> dict:
    """Collect scores from a candidate's workspace task results.
    
    Reads scores.json from each task workspace and computes aggregates.
    Returns a scores dict compatible with scorer.score_candidate().
    """
    workspaces = candidate_dir / "workspaces"
    if not workspaces.is_dir():
        return {"error": f"No workspaces dir in {candidate_dir}"}
    
    task_results = []
    for task_dir in sorted(workspaces.iterdir()):
        scores_path = task_dir / "scores.json"
        if scores_path.is_file():
            try:
                scores = json.loads(scores_path.read_text())
                task_results.append(scores)
            except json.JSONDecodeError:
                task_results.append({
                    "task_id": task_dir.name,
                    "status": "error",
                    "pass": False,
                })
    
    if not task_results:
        return {"error": "No task results found"}
    
    total = len(task_results)
    passed = sum(1 for t in task_results if t.get("pass", False))
    pass_rate = passed / total if total > 0 else 0.0
    
    grades = [GRADE_MAP.get(t.get("eval_grade", "F"), 0.0) for t in task_results]
    avg_grade = sum(grades) / len(grades) if grades else 0.0
    
    rounds = [t.get("rounds", 1) for t in task_results if t.get("status") != "error"]
    avg_rounds = sum(rounds) / len(rounds) if rounds else 1.0
    
    total_dod = sum(t.get("dod_total", 0) for t in task_results)
    passed_dod = sum(t.get("dod_passed", 0) for t in task_results)
    avg_dod = total_dod / total if total > 0 else 0
    
    total_tests = sum(t.get("tests_passed", t.get("tests_total", 0)) for t in task_results)
    avg_tests = total_tests / total if total > 0 else 0
    
    retries = sum(1 for t in task_results if t.get("rounds", 1) > 1)
    timeouts = sum(1 for t in task_results if t.get("status") in ("timeout", "error"))
    
    scores = {
        "task_count": total,
        "passed": passed,
        "pass_rate": round(pass_rate, 4),
        "eval_grade": round(avg_grade, 4),
        "avg_rounds": round(avg_rounds, 2),
        "avg_dod_per_task": round(avg_dod, 1),
        "total_dod": total_dod,
        "total_tests": total_tests,
        "avg_tests_per_task": round(avg_tests, 1),
        "retries": retries,
        "timeouts": timeouts,
        "stuck_rate": round(timeouts / total if total > 0 else 0, 4),
        "task_results": task_results,
    }
    
    # Composite score (enhanced with DoD granularity)
    dod_score = min(1.0, avg_dod / 20)  # normalize: 20 DoD/task = 1.0
    scores["composite"] = round(
        0.30 * pass_rate +
        0.25 * avg_grade +
        0.20 * dod_score +
        0.10 * max(0, 1 - (avg_rounds - 1) / 4) +
        0.10 * (1 - (retries / total if total > 0 else 0)) +
        0.05 * (1 - (timeouts / total if total > 0 else 0)),
        4
    )
    
    return scores


def load_baseline_scores() -> tuple:
    """Load the current baseline (active or seed-000) scores.
    
    Returns (baseline_id, scores_dict).
    """
    # Check active first
    active_meta = ACTIVE_DIR / "promotion.json"
    if active_meta.is_file():
        meta = json.loads(active_meta.read_text())
        baseline_id = meta.get("promoted_candidate", "active")
        # Re-score from active's evaluation if available
        active_eval = ACTIVE_DIR / "evaluation"
        if active_eval.is_dir():
            return baseline_id, score_candidate(str(active_eval))
    
    # Fall back to seed-000-baseline workspace scores
    baseline_dir = SEEDS_DIR / "seed-000-baseline"
    if baseline_dir.is_dir():
        scores = collect_candidate_scores(baseline_dir)
        return "seed-000-baseline", scores
    
    return "none", {"error": "No baseline found"}


def find_winner(candidates: dict, baseline_scores: dict) -> tuple:
    """Find the best candidate that improves over baseline.
    
    Returns (winner_id, winner_scores, decision_reason) or (None, None, reason).
    """
    if not candidates:
        return None, None, "No candidates to evaluate"
    
    # Rank by composite score
    ranked = sorted(
        candidates.items(),
        key=lambda x: x[1].get("composite", 0),
        reverse=True,
    )
    
    best_id, best_scores = ranked[0]
    baseline_composite = baseline_scores.get("composite", 0)
    best_composite = best_scores.get("composite", 0)
    
    # Must improve composite score
    if best_composite <= baseline_composite:
        return None, None, (
            f"Best candidate ({best_id}) composite {best_composite:.4f} "
            f"<= baseline {baseline_composite:.4f}"
        )
    
    # Must maintain pass rate
    if best_scores.get("pass_rate", 0) < baseline_scores.get("pass_rate", 0):
        return None, None, (
            f"Best candidate ({best_id}) regresses on pass rate: "
            f"{best_scores.get('pass_rate', 0):.2%} < {baseline_scores.get('pass_rate', 0):.2%}"
        )
    
    # Must not have excessive timeouts
    if best_scores.get("timeouts", 0) > 1:
        return None, None, (
            f"Best candidate ({best_id}) has {best_scores['timeouts']} timeouts (max 1)"
        )
    
    reason = (
        f"Candidate {best_id} improves over baseline: "
        f"composite {baseline_composite:.4f} → {best_composite:.4f} "
        f"(+{best_composite - baseline_composite:.4f}), "
        f"DoD/task {baseline_scores.get('avg_dod_per_task', 0):.1f} → {best_scores.get('avg_dod_per_task', 0):.1f}"
    )
    
    return best_id, best_scores, reason


def promote(winner_id: str, winner_scores: dict, reason: str, dry_run: bool = False) -> dict:
    """Promote winner to active harness."""
    candidate_dir = CANDIDATES_DIR / winner_id
    candidate_harness = candidate_dir / "harness"
    
    if not candidate_harness.is_dir():
        return {"promoted": False, "error": f"No harness dir in {candidate_dir}"}
    
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        "promoted": True,
        "promoted_candidate": winner_id,
        "reason": reason,
        "scores": {k: v for k, v in winner_scores.items() if k != "task_results"},
        "dry_run": dry_run,
    }
    
    if dry_run:
        record["action"] = "DRY_RUN — would promote"
        return record
    
    # Backup current active
    if ACTIVE_DIR.is_dir():
        backup_name = f"backup-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}"
        backup_dir = META_HARNESS_DIR / "backups" / backup_name
        backup_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(ACTIVE_DIR, backup_dir)
    
    # Copy winner's harness to active
    active_harness = ACTIVE_DIR / "harness"
    ACTIVE_DIR.mkdir(parents=True, exist_ok=True)
    if active_harness.is_dir():
        shutil.rmtree(active_harness)
    shutil.copytree(candidate_harness, active_harness)
    
    # Also copy the REAL skill files to the live harness location
    live_skill_dir = META_HARNESS_DIR.parent  # ~/.openclaw/skills/harness/
    for prompt_file in (candidate_harness / "prompts").glob("*.md"):
        dst = live_skill_dir / "prompts" / prompt_file.name
        if dst.is_file():
            shutil.copy2(prompt_file, dst)
    
    skill_md = candidate_harness / "SKILL.md"
    if skill_md.is_file():
        dst = live_skill_dir / "SKILL.md"
        if dst.is_file():
            shutil.copy2(skill_md, dst)
    
    # Write promotion record
    (ACTIVE_DIR / "promotion.json").write_text(json.dumps(record, indent=2))
    
    # Append to promotions log
    PROMOTIONS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(PROMOTIONS_LOG, "a") as f:
        f.write(json.dumps(record) + "\n")
    
    # Update frontier
    frontier_entry = {
        "id": winner_id,
        "scores": {k: v for k, v in winner_scores.items() if k != "task_results"},
    }
    update_frontier_file(str(FRONTIER_PATH), frontier_entry)
    
    record["action"] = "PROMOTED"
    return record


def discard(candidates: dict, reason: str) -> dict:
    """Log discard decision when no candidate improves."""
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        "promoted": False,
        "reason": reason,
        "candidates_evaluated": list(candidates.keys()),
    }
    
    PROMOTIONS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(PROMOTIONS_LOG, "a") as f:
        f.write(json.dumps(record) + "\n")
    
    return record


def run_auto_promote(dry_run: bool = False, verbose: bool = False) -> dict:
    """Main entry point — evaluate all candidates and promote or discard.
    
    Returns the promotion/discard decision record.
    """
    if verbose:
        print("=" * 60)
        print("  AUTO-PROMOTE — Evaluating candidates")
        print("=" * 60)
    
    # 1. Load baseline
    baseline_id, baseline_scores = load_baseline_scores()
    if "error" in baseline_scores:
        return {"error": f"Cannot load baseline: {baseline_scores['error']}"}
    
    if verbose:
        print(f"\nBaseline: {baseline_id}")
        print(f"  composite: {baseline_scores.get('composite', 0):.4f}")
        print(f"  pass_rate: {baseline_scores.get('pass_rate', 0):.2%}")
        print(f"  avg_dod: {baseline_scores.get('avg_dod_per_task', 0):.1f}")
    
    # 2. Collect all candidate scores
    candidates = {}
    if CANDIDATES_DIR.is_dir():
        for cand_dir in sorted(CANDIDATES_DIR.iterdir()):
            if cand_dir.is_dir() and cand_dir.name.startswith("cand-"):
                meta_path = cand_dir / "metadata.json"
                if meta_path.is_file():
                    scores = collect_candidate_scores(cand_dir)
                    if "error" not in scores:
                        candidates[cand_dir.name] = scores
                        if verbose:
                            print(f"\nCandidate: {cand_dir.name}")
                            print(f"  composite: {scores.get('composite', 0):.4f}")
                            print(f"  pass_rate: {scores.get('pass_rate', 0):.2%}")
                            print(f"  avg_dod: {scores.get('avg_dod_per_task', 0):.1f}")
                            print(f"  total_dod: {scores.get('total_dod', 0)}")
                            print(f"  retries: {scores.get('retries', 0)}")
    
    if not candidates:
        return discard({}, "No valid candidates found")
    
    # 3. Find winner
    winner_id, winner_scores, reason = find_winner(candidates, baseline_scores)
    
    if verbose:
        print(f"\n{'=' * 60}")
        if winner_id:
            print(f"  WINNER: {winner_id}")
        else:
            print(f"  NO WINNER")
        print(f"  Reason: {reason}")
        print(f"{'=' * 60}")
    
    # 4. Promote or discard
    if winner_id:
        return promote(winner_id, winner_scores, reason, dry_run=dry_run)
    else:
        return discard(candidates, reason)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Auto-promote winning harness candidate")
    parser.add_argument("--dry-run", action="store_true", help="Evaluate but don't promote")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print progress")
    
    args = parser.parse_args()
    result = run_auto_promote(dry_run=args.dry_run, verbose=args.verbose)
    
    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get("promoted", False) or result.get("dry_run", False) else 1)
