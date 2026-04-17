import json
import shutil
import tempfile
import unittest
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parents[1]
RUNNER_DIR = BASE / "runner"
sys.path.insert(0, str(RUNNER_DIR))

from benchmark_runner import run_benchmark  # noqa: E402
from task_registry import load_benchmark_suite, load_task_set  # noqa: E402
from task_executor import setup_project  # noqa: E402
from scorer import compare_candidates  # noqa: E402
from frontier import compute_frontier, load_objective_directions, update_frontier_file, load_frontier  # noqa: E402


class MetaHarnessPhase2Tests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="meta-harness-phase2-"))
        self.seed_dir = BASE / "seeds" / "seed-000-baseline"
        self.search_set = BASE / "config" / "search-set.json"
        self.holdout_set = BASE / "config" / "holdout-set.json"
        self.fixtures_dir = BASE / "fixtures"
        self.objectives = BASE / "config" / "objectives.json"

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_task_suite_is_valid_and_disjoint(self):
        suite = load_benchmark_suite(BASE / "config", self.fixtures_dir)
        self.assertTrue(suite["is_valid"], suite)
        self.assertEqual(suite["search"]["task_count"], 12)
        self.assertEqual(suite["holdout"]["task_count"], 8)
        self.assertTrue(suite["discipline"]["is_valid"], suite["discipline"])
        self.assertEqual(suite["discipline"]["overlap_ids"], [])
        self.assertEqual(suite["discipline"]["overlap_scaffolds"], [])

    def test_search_set_tasks_have_fixture_hashes_and_validation(self):
        bundle = load_task_set(self.search_set, self.fixtures_dir)
        self.assertTrue(bundle["is_valid"], bundle["validation_errors"])
        for task in bundle["tasks"]:
            self.assertTrue(task["fixture_hash"])
            self.assertIn("{project_dir}", task["verify_command"])
            self.assertGreaterEqual(task["fixture_file_count"], 1)
            self.assertTrue(task["expected_artifacts"])
            self.assertTrue(task["failure_modes"])

    def test_setup_project_materializes_isolated_workspace(self):
        bundle = load_task_set(self.holdout_set, self.fixtures_dir)
        task = next(t for t in bundle["tasks"] if t["id"] == "holdout-001")
        work_dir = self.tmpdir / "workspaces"
        project_dir = Path(setup_project(task, str(self.fixtures_dir), str(work_dir)))
        self.assertTrue(project_dir.exists())
        self.assertTrue((project_dir / "workspace-manifest.json").exists())
        manifest = json.loads((project_dir / "workspace-manifest.json").read_text())
        self.assertEqual(manifest["task_id"], "holdout-001")
        self.assertIn("README.md", manifest["files"])
        self.assertTrue(any(name.endswith(".py") for name in manifest["files"]))

    def test_benchmark_dry_run_search_set(self):
        out = self.tmpdir / "dry-search"
        result = run_benchmark(str(self.seed_dir), str(self.search_set), str(out), dry_run=True)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["task_count"], 12)
        aggregate = json.loads((out / "evaluation" / "aggregate.json").read_text())
        self.assertEqual(aggregate["mode"], "dry_run")
        self.assertIn("task_categories", aggregate)
        self.assertTrue((out / "evaluation" / "manifest.json").exists())

    def test_benchmark_simulate_holdout_set(self):
        out = self.tmpdir / "sim-holdout"
        result = run_benchmark(str(self.seed_dir), str(self.holdout_set), str(out), simulate=True)
        self.assertEqual(result["status"], "completed")
        scores = result["scores"]
        self.assertEqual(scores["task_count"], 8)
        self.assertIn("dod_coverage", scores)
        self.assertIn("artifact_validity_rate", scores)
        self.assertIn("category_breakdown", scores)
        self.assertIn("difficulty_breakdown", scores)
        self.assertGreaterEqual(scores["artifact_validity_rate"], 0.0)
        self.assertTrue((out / "evaluation" / "tasks" / "holdout-001" / "run-artifacts" / "plan.md").exists())
        self.assertTrue((out / "evaluation" / "leaderboard.json").exists())
        self.assertTrue((out / "evaluation" / "leaderboard.md").exists())

    def test_frontier_uses_configured_directions(self):
        directions = load_objective_directions(self.objectives)
        frontier = compute_frontier([
            {"id": "a", "scores": {"pass_rate": 0.8, "avg_time_seconds": 200, "token_cost": 1000}},
            {"id": "b", "scores": {"pass_rate": 0.8, "avg_time_seconds": 150, "token_cost": 900}},
            {"id": "c", "scores": {"pass_rate": 0.9, "avg_time_seconds": 400, "token_cost": 1200}},
        ], dimensions=["pass_rate", "avg_time_seconds", "token_cost"], directions=directions)
        ids = {entry["id"] for entry in frontier}
        self.assertIn("b", ids)
        self.assertIn("c", ids)
        self.assertNotIn("a", ids)

    def test_frontier_update_dedupes_by_candidate_id(self):
        frontier_path = self.tmpdir / "frontier.json"
        update_frontier_file(str(frontier_path), {"id": "seed-000-baseline", "scores": {"pass_rate": 0.8, "avg_time_seconds": 200, "token_cost": 100, "dod_coverage": 0.8}}, objectives_path=self.objectives)
        update_frontier_file(str(frontier_path), {"id": "seed-000-baseline", "scores": {"pass_rate": 0.9, "avg_time_seconds": 180, "token_cost": 90, "dod_coverage": 0.9}}, objectives_path=self.objectives)
        frontier = load_frontier(str(frontier_path))
        self.assertEqual(frontier["total_evaluated"], 1)
        self.assertEqual(frontier["all_candidates"][0]["pass_rate"], 0.9)

    def test_compare_candidates_includes_phase2_metrics(self):
        deltas = compare_candidates(
            {"pass_rate": 0.8, "dod_coverage": 0.7, "artifact_validity_rate": 0.8, "regression_rate": 0.1, "composite": 0.6},
            {"pass_rate": 0.9, "dod_coverage": 0.9, "artifact_validity_rate": 1.0, "regression_rate": 0.0, "composite": 0.8},
        )
        self.assertEqual(deltas["pass_rate"], 0.1)
        self.assertEqual(deltas["dod_coverage"], 0.2)
        self.assertEqual(deltas["artifact_validity_rate"], 0.2)
        self.assertEqual(deltas["regression_rate"], -0.1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
