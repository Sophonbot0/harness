#!/usr/bin/env python3
"""Materialize deterministic scaffold files into thin benchmark fixtures."""

from __future__ import annotations

import json
from pathlib import Path

from task_registry import load_benchmark_suite


BASE = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE / "config"
FIXTURES_DIR = BASE / "fixtures"


def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def materialize_task(task: dict):
    fixture_dir = Path(task["fixture_dir"])
    existing_files = [p for p in fixture_dir.iterdir() if p.is_file() and p.name != "task.json"]
    existing_dirs = [p for p in fixture_dir.iterdir() if p.is_dir()]
    if existing_files or existing_dirs:
        return False

    slug = task["id"].replace("-", "_")
    verify = task["verify_command"].replace("{project_dir}", ".")
    readme = f"# {task['name']}\n\n{task['description']}\n\n- Category: {task['category']}\n- Difficulty: {task['difficulty']}\n- Verify: `{verify}`\n"
    write(fixture_dir / "README.md", readme)
    write(fixture_dir / ".fixture-manifest.json", json.dumps({
        "task_id": task["id"],
        "category": task["category"],
        "difficulty": task["difficulty"],
        "failure_modes": task["failure_modes"],
        "expected_artifacts": task["expected_artifacts"],
        "generated_by": "materialize_fixture_scaffolds.py",
    }, indent=2))

    category = task["category"]
    if category == "project":
        write(fixture_dir / "app" / "__init__.py", "")
        write(fixture_dir / "app" / "service.py", "def healthcheck():\n    return {'ok': True}\n")
        write(fixture_dir / "tests" / "test_service.py", "from app.service import healthcheck\n\n\ndef test_healthcheck():\n    assert healthcheck() == {'ok': True}\n")
    elif category == "bug_fix":
        write(fixture_dir / f"{slug}.py", "def solve(items):\n    if items is None:\n        raise TypeError('items must not be None')\n    return sorted(set(items))\n")
        write(fixture_dir / f"test_{slug}.py", f"from {slug} import solve\n\n\ndef test_roundtrip():\n    assert solve([3, 2, 1]) == [1, 2, 3]\n\n\ndef test_duplicates_are_preserved():\n    assert solve([3, 2, 1, 2]) == [1, 2, 2, 3]\n")
    elif category == "ambiguous":
        write(fixture_dir / f"{slug}.py", "def current_state():\n    return {'status': 'baseline'}\n")
        write(fixture_dir / f"test_{slug}.py", f"from {slug} import current_state\n\n\ndef test_fixture_loads():\n    assert current_state()['status'] == 'baseline'\n")
    else:
        write(fixture_dir / f"{slug}.py", "def baseline_status():\n    return {'implemented': False, 'message': 'benchmark scaffold'}\n")
        write(fixture_dir / f"test_{slug}.py", f"from {slug} import baseline_status\n\n\ndef test_baseline_status():\n    assert baseline_status()['implemented'] is False\n")
    return True


def main():
    suite = load_benchmark_suite(CONFIG_DIR, FIXTURES_DIR)
    changed = []
    for bucket in ["search", "holdout"]:
        for task in suite[bucket]["tasks"]:
            if materialize_task(task):
                changed.append(task["id"])
    print(json.dumps({"materialized": changed, "count": len(changed)}, indent=2))


if __name__ == "__main__":
    main()
