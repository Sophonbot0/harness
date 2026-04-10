#!/usr/bin/env python3
"""
Meta-Harness — Outer loop for harness evolution.

Based on Khattab & Finn (2026) "Meta-Harness: End-to-End Optimization
of Model Harnesses" (arXiv:2603.28052).

Usage:
    python3 run_meta_harness.py --seed-eval          # Evaluate all seeds
    python3 run_meta_harness.py --iterate 5           # Run 5 proposer iterations
    python3 run_meta_harness.py --promote             # Run promotion gate
    python3 run_meta_harness.py --status              # Show current state
    python3 run_meta_harness.py --dry-run --seed-eval # Validate without execution

Algorithm (from the paper):
    1. Initialize population H with seed harnesses
    2. Evaluate all seeds on search set, store in filesystem D
    3. For t = 1..N:
       a. Proposer reads filesystem D (code, scores, traces)
       b. Proposer proposes k new candidates
       c. Validate each candidate
       d. Evaluate valid candidates on search set
       e. Store results in D, update frontier
    4. Evaluate Pareto frontier on holdout set
    5. Promote best candidate if it passes holdout gate
"""

import argparse
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Setup paths
SCRIPT_DIR = Path(__file__).parent
META_HARNESS_DIR = SCRIPT_DIR
RUNNER_DIR = META_HARNESS_DIR / "runner"
CONFIG_DIR = META_HARNESS_DIR / "config"
SEEDS_DIR = META_HARNESS_DIR / "seeds"
CANDIDATES_DIR = META_HARNESS_DIR / "candidates"
RUNS_DIR = META_HARNESS_DIR / "runs"
ACTIVE_DIR = META_HARNESS_DIR / "active"

sys.path.insert(0, str(RUNNER_DIR))

from benchmark_runner import run_benchmark
from validator import validate_and_report
from scorer import score_candidate
from frontier import update_frontier_file, load_frontier
from promotion import evaluate_promotion, promote_candidate, generate_promotion_report


def ensure_dirs():
    """Ensure all required directories exist."""
    for d in [CANDIDATES_DIR, RUNS_DIR, ACTIVE_DIR, ACTIVE_DIR / "backups"]:
        d.mkdir(parents=True, exist_ok=True)


def load_config():
    """Load meta-harness configuration."""
    import yaml
    config_path = CONFIG_DIR / "meta-harness.yaml"
    if config_path.exists():
        return yaml.safe_load(config_path.read_text())
    # Fallback to defaults
    return {
        "iterations": 10,
        "candidates_per_iteration": 2,
    }


def get_next_candidate_id() -> str:
    """Generate next candidate ID."""
    existing = sorted(CANDIDATES_DIR.glob("cand-*")) if CANDIDATES_DIR.exists() else []
    if not existing:
        return "cand-0001"
    last_num = max(int(d.name.split("-")[1]) for d in existing)
    return f"cand-{last_num + 1:04d}"


def seed_eval(dry_run: bool = False, verbose: bool = False):
    """Evaluate all seed harnesses on the search set."""
    print("=" * 60)
    print("  Meta-Harness: Seed Evaluation")
    print("=" * 60)
    
    search_set = str(CONFIG_DIR / "search-set.json")
    frontier_path = str(META_HARNESS_DIR / "frontier.json")
    
    seeds = sorted(SEEDS_DIR.glob("seed-*"))
    print(f"\nFound {len(seeds)} seeds")
    
    for seed_dir in seeds:
        print(f"\n{'─' * 40}")
        print(f"  Evaluating: {seed_dir.name}")
        print(f"{'─' * 40}")
        
        result = run_benchmark(
            str(seed_dir),
            search_set,
            str(seed_dir),
            dry_run=dry_run,
            verbose=verbose,
        )
        
        if result.get("scores"):
            scores = result["scores"]
            print(f"  Pass rate:  {scores.get('pass_rate', 0):.1%}")
            print(f"  Composite:  {scores.get('composite', 0):.4f}")
            print(f"  Avg rounds: {scores.get('avg_rounds', 0):.1f}")
            
            # Add to frontier
            entry = {
                "id": seed_dir.name,
                "type": "seed",
                "dir": str(seed_dir),
                "scores": scores,
            }
            update_frontier_file(frontier_path, entry)
        else:
            print(f"  ⚠️  Invalid: {result.get('validation', {}).get('issues', [])}")
    
    # Show frontier
    frontier = load_frontier(frontier_path)
    print(f"\n{'=' * 60}")
    print(f"  Frontier: {frontier.get('frontier_size', 0)} candidates")
    print(f"  Total evaluated: {frontier.get('total_evaluated', 0)}")
    print(f"{'=' * 60}")


def iterate(n_iterations: int, dry_run: bool = False, verbose: bool = False):
    """Run N proposer iterations."""
    print("=" * 60)
    print(f"  Meta-Harness: {n_iterations} Evolution Iterations")
    print("=" * 60)
    
    # Create run manifest
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    run_dir = RUNS_DIR / f"run-{run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)
    
    manifest = {
        "run_id": run_id,
        "started_at": datetime.now(timezone.utc).isoformat() + "Z",
        "iterations_planned": n_iterations,
        "iterations_completed": 0,
        "candidates_proposed": 0,
        "candidates_valid": 0,
        "dry_run": dry_run,
    }
    
    search_set = str(CONFIG_DIR / "search-set.json")
    frontier_path = str(META_HARNESS_DIR / "frontier.json")
    
    for i in range(n_iterations):
        print(f"\n{'━' * 60}")
        print(f"  Iteration {i + 1}/{n_iterations}")
        print(f"{'━' * 60}")
        
        # In production: spawn proposer agent with filesystem access
        # For now: log that this needs agent execution
        print(f"  → Proposer would inspect filesystem and propose candidates")
        print(f"  → Frontier: {META_HARNESS_DIR / 'frontier.json'}")
        print(f"  → Seeds: {SEEDS_DIR}")
        print(f"  → Candidates: {CANDIDATES_DIR}")
        
        if not dry_run:
            print(f"  ⚠️  Full execution requires spawning proposer agent")
            print(f"     Use: sessions_spawn with proposer-skill.md")
            print(f"     Then: validate + benchmark each proposed candidate")
        
        manifest["iterations_completed"] = i + 1
    
    manifest["completed_at"] = datetime.now(timezone.utc).isoformat() + "Z"
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    
    print(f"\n  Run manifest: {run_dir / 'manifest.json'}")


def do_promote(dry_run: bool = False, verbose: bool = False):
    """Run promotion gate on frontier candidates."""
    print("=" * 60)
    print("  Meta-Harness: Promotion Gate")
    print("=" * 60)
    
    frontier_path = str(META_HARNESS_DIR / "frontier.json")
    frontier = load_frontier(frontier_path)
    
    if not frontier.get("frontier"):
        print("  No candidates on frontier. Run --seed-eval first.")
        return
    
    # Find baseline (seed-000)
    baseline = None
    best_candidate = None
    best_composite = -1
    
    for entry in frontier.get("all_candidates", []):
        if entry.get("id") == "seed-000-baseline":
            baseline = entry
        if entry.get("composite", 0) > best_composite:
            best_composite = entry["composite"]
            best_candidate = entry
    
    if not baseline:
        print("  ⚠️  No baseline found in frontier")
        return
    
    if best_candidate["id"] == baseline["id"]:
        print("  Baseline is still the best. No promotion needed.")
        return
    
    print(f"\n  Baseline:  {baseline['id']} (composite: {baseline.get('composite', 0):.4f})")
    print(f"  Candidate: {best_candidate['id']} (composite: {best_candidate.get('composite', 0):.4f})")
    
    # TODO: Run holdout evaluation on the candidate
    # For now, compare search-set scores
    print(f"\n  ⚠️  Holdout evaluation not yet implemented")
    print(f"     Would evaluate {best_candidate['id']} on holdout-set.json")


def show_status():
    """Show current Meta-Harness state."""
    print("=" * 60)
    print("  Meta-Harness Status")
    print("=" * 60)
    
    # Seeds
    seeds = sorted(SEEDS_DIR.glob("seed-*")) if SEEDS_DIR.exists() else []
    print(f"\n  Seeds: {len(seeds)}")
    for s in seeds:
        meta = {}
        meta_path = s / "metadata.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
        print(f"    {s.name}: {meta.get('name', '?')} — {meta.get('description', '')[:60]}")
    
    # Candidates
    candidates = sorted(CANDIDATES_DIR.glob("cand-*")) if CANDIDATES_DIR.exists() else []
    print(f"\n  Candidates: {len(candidates)}")
    
    # Frontier
    frontier_path = META_HARNESS_DIR / "frontier.json"
    if frontier_path.exists():
        frontier = json.loads(frontier_path.read_text())
        print(f"\n  Frontier: {frontier.get('frontier_size', 0)} / {frontier.get('total_evaluated', 0)} evaluated")
        for entry in frontier.get("all_candidates", []):
            marker = "★" if entry.get("on_frontier") else " "
            print(f"    {marker} {entry['id']}: composite={entry.get('composite', 0):.4f}, pass_rate={entry.get('pass_rate', 0):.1%}")
    else:
        print("\n  Frontier: not yet computed (run --seed-eval)")
    
    # Runs
    runs = sorted(RUNS_DIR.glob("run-*")) if RUNS_DIR.exists() else []
    print(f"\n  Runs: {len(runs)}")
    for r in runs[-5:]:  # Last 5
        manifest_path = r / "manifest.json"
        if manifest_path.exists():
            m = json.loads(manifest_path.read_text())
            print(f"    {r.name}: {m.get('iterations_completed', 0)}/{m.get('iterations_planned', 0)} iterations")
    
    # Active
    active_promotion = ACTIVE_DIR / "promotion.json"
    if active_promotion.exists():
        promo = json.loads(active_promotion.read_text())
        print(f"\n  Active: promoted from {promo.get('candidate_id', '?')}")
    else:
        print(f"\n  Active: baseline (no promotion yet)")


def main():
    parser = argparse.ArgumentParser(
        description="Meta-Harness: Automated Harness Evolution",
        epilog="Based on Khattab & Finn (2026) arXiv:2603.28052"
    )
    
    parser.add_argument("--seed-eval", action="store_true",
                       help="Evaluate all seed harnesses on search set")
    parser.add_argument("--iterate", type=int, metavar="N",
                       help="Run N proposer iterations")
    parser.add_argument("--promote", action="store_true",
                       help="Run promotion gate on frontier candidates")
    parser.add_argument("--status", action="store_true",
                       help="Show current Meta-Harness state")
    parser.add_argument("--dry-run", action="store_true",
                       help="Validate without executing tasks")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Verbose output")
    
    args = parser.parse_args()
    
    ensure_dirs()
    
    if args.status:
        show_status()
    elif args.seed_eval:
        seed_eval(dry_run=args.dry_run, verbose=args.verbose)
    elif args.iterate:
        iterate(args.iterate, dry_run=args.dry_run, verbose=args.verbose)
    elif args.promote:
        do_promote(dry_run=args.dry_run, verbose=args.verbose)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
