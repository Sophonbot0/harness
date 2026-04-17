#!/usr/bin/env python3
"""
Task Executor — benchmark task workspace setup, prompt assembly, and trace capture.

Phase 2 focus:
- deterministic, isolated workspaces
- replayable fixture materialization for thin fixtures
- richer trace capture for later diagnosis
"""

from __future__ import annotations

import json
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_README = """# {name}

{description}

## Benchmark Notes
- Category: {category}
- Difficulty: {difficulty}
- Failure modes under test: {failure_modes}
- Verify command: `{verify_command}`
"""


def build_orchestrator_prompt(task: dict[str, Any], prompts: dict[str, str], project_dir: str) -> str:
    """Build the full orchestrator prompt that a subagent will execute."""
    task_desc = task.get("description", "No description")
    task_name = task.get("name", task.get("id", "unknown"))

    planner_prompt = prompts.get("planner-system", "You are the PLANNER. Write plan.md.")
    generator_prompt = prompts.get("generator-system", "You are the GENERATOR. Implement plan.md.")
    adversary_prompt = prompts.get("adversary-system", "You are the ADVERSARY. Challenge the implementation.")
    evaluator_prompt = prompts.get("evaluator-system", "You are the EVALUATOR. Grade the work.")

    expected_artifacts = ", ".join(task.get("expected_artifacts", ["plan.md", "challenge-report.md", "eval-report.md", "scores.json"]))
    failure_modes = ", ".join(task.get("failure_modes", [])) or "general robustness"
    verify_command = task.get("verify_command", "cd {project_dir} && python3 -m pytest -q").replace("{project_dir}", project_dir)

    prompt = f"""# Benchmark Task Execution

You are executing a benchmark task. You MUST use tools (read, write, exec) to do real work.

**DO NOT just describe what you would do. Actually DO it.**
- Use `read` to read files
- Use `write` to create benchmark artifacts
- Use `exec` to run tests / verifiers
- Use `edit` to fix code

## Task
**ID:** {task.get('id', 'unknown')}
**Name:** {task_name}
**Category:** {task.get('category', 'feature')}
**Difficulty:** {task.get('difficulty', 'medium')}
**Description:** {task_desc}
**Failure modes under test:** {failure_modes}
**Working directory:** {project_dir}
**Expected artifacts:** {expected_artifacts}
**Verify command:** {verify_command}

## Instructions
Execute the following 4-phase pipeline IN ORDER.

### Phase 1: PLAN
<planner_instructions>
{planner_prompt}
</planner_instructions>
Write `plan.md` to {project_dir}/plan.md

### Phase 2: BUILD
<generator_instructions>
{generator_prompt}
</generator_instructions>
Implement the plan in the working directory and run verification as you go.

### Phase 3: CHALLENGE
<adversary_instructions>
{adversary_prompt}
</adversary_instructions>
Write `challenge-report.md` to {project_dir}/challenge-report.md

### Phase 4: EVALUATE
<evaluator_instructions>
{evaluator_prompt}
</evaluator_instructions>
Write `eval-report.md` to {project_dir}/eval-report.md

## CRITICAL RULES
1. Execute ALL 4 phases. Do not skip any.
2. Work only inside {project_dir}
3. Write all expected artifacts.
4. If the eval says FAIL and you have time, do ONE retry cycle.
5. Maximum 2 rounds total.
6. End by writing `scores.json` in this exact shape:

```json
{{
  "task_id": "{task.get('id', 'unknown')}",
  "status": "completed",
  "pass": true,
  "eval_grade": "PASS",
  "rounds": 1,
  "dod_total": {int(task.get('expected_dod_count', 0))},
  "dod_passed": {int(task.get('expected_dod_count', 0))},
  "notes": "brief summary"
}}
```

7. Start by reading the project files with the `read` tool.
"""
    return prompt


def _write_file(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _materialize_minimal_fixture(task: dict[str, Any], task_work: Path):
    """Create a deterministic minimal project scaffold for thin fixtures.

    This is intentionally generic-but-replayable. It gives the harness a stable
    offline sandbox even when the benchmark task is described primarily via
    metadata rather than a full source tree.
    """
    verify_command = str(task.get("verify_command", "cd {project_dir} && python3 -m pytest -q")).replace("{project_dir}", str(task_work))
    readme = DEFAULT_README.format(
        name=task.get("name", task.get("id", "Task")),
        description=task.get("description", ""),
        category=task.get("category", "feature"),
        difficulty=task.get("difficulty", "medium"),
        failure_modes=", ".join(task.get("failure_modes", [])),
        verify_command=verify_command,
    )
    _write_file(task_work / "README.md", readme)
    _write_file(task_work / ".meta-harness-fixture.json", json.dumps({
        "task_id": task.get("id"),
        "category": task.get("category"),
        "difficulty": task.get("difficulty"),
        "materialized_at": datetime.now(timezone.utc).isoformat() + "Z",
        "verify_command": verify_command,
    }, indent=2))

    category = task.get("category", "feature")
    slug = str(task.get("id", "task")).replace("-", "_")
    module_path = task_work / f"{slug}.py"
    test_path = task_work / f"test_{slug}.py"

    if category == "bug_fix":
        _write_file(module_path, """def solve(items):
    # Intentionally broken baseline for bug-fix tasks.
    if items is None:
        raise TypeError('items must not be None')
    return sorted(set(items))
""")
        _write_file(test_path, f"""from {slug} import solve


def test_smoke_list_roundtrip():
    assert solve([3, 1, 2]) == [1, 2, 3]


def test_duplicates_are_preserved():
    assert solve([3, 1, 2, 1, 3]) == [1, 1, 2, 3, 3]
""")
    elif category == "ambiguous":
        _write_file(module_path, """def current_state():
    return {'status': 'baseline', 'note': 'Task intentionally ambiguous'}
""")
        _write_file(test_path, f"""from {slug} import current_state


def test_fixture_loads():
    data = current_state()
    assert data['status'] == 'baseline'
""")
    elif category == "project":
        _write_file(task_work / "app" / "__init__.py", "")
        _write_file(task_work / "app" / "service.py", """def healthcheck():
    return {'ok': True}
""")
        _write_file(task_work / "tests" / "test_service.py", """from app.service import healthcheck


def test_healthcheck():
    assert healthcheck() == {'ok': True}
""")
    else:
        _write_file(module_path, """def baseline_status():
    return {'implemented': False, 'message': 'benchmark scaffold'}
""")
        _write_file(test_path, f"""from {slug} import baseline_status


def test_baseline_status():
    data = baseline_status()
    assert data['implemented'] is False
""")


def _copy_fixture_contents(fixture_dir: Path, task_work: Path):
    for item in fixture_dir.iterdir():
        if item.name == "task.json":
            continue
        dest = task_work / item.name
        if item.is_dir():
            shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dest)


def _write_workspace_manifest(task: dict[str, Any], task_work: Path, source_fixture: Path):
    files = sorted([str(p.relative_to(task_work)) for p in task_work.rglob("*") if p.is_file()])
    manifest = {
        "task_id": task.get("id"),
        "fixture_dir": str(source_fixture),
        "workspace_dir": str(task_work),
        "created_at": datetime.now(timezone.utc).isoformat() + "Z",
        "scaffold_type": task.get("scaffold_type", "copied"),
        "verify_command": str(task.get("verify_command", "")).replace("{project_dir}", str(task_work)),
        "files": files,
    }
    _write_file(task_work / "workspace-manifest.json", json.dumps(manifest, indent=2))


def setup_project(task: dict[str, Any], fixtures_base: str, work_dir: str) -> str:
    """Set up an isolated project directory from fixture or deterministic materialization."""
    fixture_dir = Path(task.get("fixture_dir") or (Path(fixtures_base) / Path(task.get("scaffold", "")).name))
    task_work = Path(work_dir) / task["id"]
    if task_work.exists():
        shutil.rmtree(task_work)
    task_work.mkdir(parents=True, exist_ok=True)

    if fixture_dir.is_dir():
        _copy_fixture_contents(fixture_dir, task_work)

    materialized_files = [p for p in task_work.rglob("*") if p.is_file()]
    if len(materialized_files) == 0:
        _materialize_minimal_fixture(task, task_work)
        task["scaffold_type"] = "materialized"
    else:
        task["scaffold_type"] = task.get("scaffold_type", "copied")

    _write_workspace_manifest(task, task_work, fixture_dir)
    return str(task_work)


def parse_scores_from_output(project_dir: str, task: dict[str, Any], elapsed: float) -> dict[str, Any]:
    """Parse scores.json written by the subagent, with structured fallbacks."""
    task_id = task["id"]
    scores_path = Path(project_dir) / "scores.json"
    if scores_path.is_file():
        try:
            scores = json.loads(scores_path.read_text())
            scores["elapsed_seconds"] = round(elapsed, 2)
            scores.setdefault("task_id", task_id)
            return scores
        except json.JSONDecodeError:
            pass

    eval_path = Path(project_dir) / "eval-report.md"
    challenge_path = Path(project_dir) / "challenge-report.md"
    plan_path = Path(project_dir) / "plan.md"
    if eval_path.is_file():
        content = eval_path.read_text()
        lower = content.lower()
        passed = "overall: pass" in lower or "## overall: pass" in lower
        pass_count = content.count("✅")
        fail_count = content.count("❌")
        total = pass_count + fail_count
        artifact_valid = sum(int((Path(project_dir) / name).exists()) for name in task.get("expected_artifacts", []))

        return {
            "task_id": task_id,
            "status": "completed",
            "pass": passed,
            "eval_grade": "PASS" if passed else "FAIL",
            "rounds": 1,
            "dod_total": total or int(task.get("expected_dod_count", 0)),
            "dod_passed": pass_count if total else (int(task.get("expected_dod_count", 0)) if passed else 0),
            "artifact_validity": artifact_valid / max(1, len(task.get("expected_artifacts", []))),
            "elapsed_seconds": round(elapsed, 2),
            "total_tokens": 0,
            "parsed_from": "eval-report.md",
            "notes": f"Fallback parsed from eval report; plan={plan_path.exists()} challenge={challenge_path.exists()}",
        }

    return {
        "task_id": task_id,
        "status": "error",
        "pass": False,
        "eval_grade": "F",
        "rounds": 0,
        "dod_total": int(task.get("expected_dod_count", 0)),
        "dod_passed": 0,
        "artifact_validity": 0.0,
        "elapsed_seconds": round(elapsed, 2),
        "total_tokens": 0,
        "error": "No scores.json or eval-report.md found",
    }


def simulate_task_result(task: dict[str, Any], prompts: dict[str, str], output_dir: str) -> dict[str, Any]:
    """Deterministic cheap simulation for offline benchmark validation/tests."""
    task_dir = Path(output_dir) / task["id"]
    task_dir.mkdir(parents=True, exist_ok=True)
    run_artifacts = task_dir / "run-artifacts"
    run_artifacts.mkdir(parents=True, exist_ok=True)

    prompt_strength = sum(len(v) for v in prompts.values())
    difficulty_penalty = {"easy": 0, "medium": 1, "hard": 2}.get(task.get("difficulty", "medium"), 1)
    ambiguous_penalty = 1 if task.get("category") == "ambiguous" else 0
    rounds = 1 + (1 if prompt_strength < 6000 or difficulty_penalty + ambiguous_penalty > 1 else 0)
    pass_grade = prompt_strength >= 1500
    grade = "PASS" if pass_grade else "FAIL"
    dod_total = int(task.get("expected_dod_count", 0))
    dod_passed = dod_total if pass_grade else max(0, dod_total - max(1, difficulty_penalty + ambiguous_penalty))
    artifact_validity = 1.0

    _write_file(run_artifacts / "plan.md", f"# Plan\n\nSimulated plan for {task['id']}\n")
    _write_file(run_artifacts / "challenge-report.md", f"# Challenge Report\n\nConfidence Rating: 3\n")
    _write_file(run_artifacts / "eval-report.md", f"# Evaluation Report\n\n## Overall: {grade}\n")

    result = {
        "task_id": task["id"],
        "status": "completed",
        "pass": pass_grade,
        "eval_grade": grade,
        "rounds": rounds,
        "dod_total": dod_total,
        "dod_passed": dod_passed,
        "elapsed_seconds": float(60 + 45 * difficulty_penalty + 15 * ambiguous_penalty),
        "total_tokens": int(prompt_strength / 4),
        "artifact_validity": artifact_validity,
        "notes": f"simulated benchmark for {task['category']} / {task['difficulty']}",
        "category": task.get("category"),
        "difficulty": task.get("difficulty"),
    }
    _write_file(task_dir / "scores.json", json.dumps(result, indent=2))
    return result


def collect_traces(project_dir: str, output_dir: str):
    """Copy execution artifacts and workspace metadata into trace output directory."""
    project_dir = Path(project_dir)
    artifacts_dir = Path(output_dir) / "run-artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    for artifact in [
        "plan.md",
        "challenge-report.md",
        "eval-report.md",
        "scores.json",
        "workspace-manifest.json",
        ".meta-harness-fixture.json",
    ]:
        src = project_dir / artifact
        if src.is_file():
            shutil.copy2(src, artifacts_dir / artifact)

    project_snapshot = artifacts_dir / "project"
    for f in project_dir.rglob("*"):
        if not f.is_file():
            continue
        rel = f.relative_to(project_dir)
        if str(rel).startswith(".pytest_cache"):
            continue
        dst = project_snapshot / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, dst)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Execute or simulate a single benchmark task")
    parser.add_argument("task_json", help="Path to task.json or inline JSON")
    parser.add_argument("prompts_dir", help="Path to candidate harness/prompts/ directory")
    parser.add_argument("--output", "-o", default=".", help="Output directory")
    parser.add_argument("--simulate", action="store_true", help="Simulate instead of live execution")
    args = parser.parse_args()

    task_input = Path(args.task_json)
    if task_input.is_file():
        task = json.loads(task_input.read_text())
    else:
        task = json.loads(args.task_json)

    prompts = {}
    prompts_dir = Path(args.prompts_dir)
    for pfile in prompts_dir.glob("*.md"):
        prompts[pfile.stem] = pfile.read_text()

    if args.simulate:
        print(json.dumps(simulate_task_result(task, prompts, args.output), indent=2))
    else:
        print(build_orchestrator_prompt(task, prompts, args.output))
