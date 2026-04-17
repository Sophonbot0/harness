#!/usr/bin/env python3
"""
Task Registry — canonical loading and validation for benchmark task sets.

Phase 2 goal: treat the benchmark suite as a first-class, reproducible surface.
This module merges task-set metadata with per-fixture task.json files, validates
search vs holdout discipline, and enriches tasks with deterministic defaults so
fixtures remain replayable even when they are intentionally thin.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ALLOWED_CATEGORIES = {
    "bug_fix",
    "feature",
    "refactor",
    "ambiguous",
    "project",
}

ALLOWED_DIFFICULTIES = {"easy", "medium", "hard"}

DEFAULT_FAILURE_MODES = {
    "bug_fix": ["correctness", "regression", "edge_case"],
    "feature": ["scope_miss", "integration", "artifact_gap"],
    "refactor": ["regression", "backwards_compatibility", "untested_path"],
    "ambiguous": ["assumption_quality", "scope_definition", "overbuild"],
    "project": ["planning", "multi_file_coordination", "partial_completion"],
}

DEFAULT_ARTIFACTS = [
    "plan.md",
    "challenge-report.md",
    "eval-report.md",
    "scores.json",
]

DEFAULT_VERIFY_BY_LANGUAGE = {
    "python": "cd {project_dir} && python3 -m pytest -q",
    "javascript": "cd {project_dir} && node --test",
    "typescript": "cd {project_dir} && node --test",
    "text": "cd {project_dir} && test -f README.md",
}


class TaskRegistryError(RuntimeError):
    pass


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _default_fixture_metadata(task: dict[str, Any]) -> dict[str, Any]:
    language = task.get("language") or "python"
    verify_command = DEFAULT_VERIFY_BY_LANGUAGE.get(language, DEFAULT_VERIFY_BY_LANGUAGE["python"])
    return {
        "task_description": task.get("description", ""),
        "verify_command": verify_command,
        "language": language,
        "scaffold_type": "minimal",
        "files": [],
        "expected_artifacts": list(DEFAULT_ARTIFACTS),
        "failure_modes": list(DEFAULT_FAILURE_MODES.get(task.get("category", "feature"), ["scope_miss"])),
        "tags": [task.get("category", "feature"), task.get("difficulty", "medium")],
        "baseline_expectation": "fail" if task.get("category") == "bug_fix" else "pass",
    }


def merge_task_definition(task_entry: dict[str, Any], fixtures_dir: Path) -> dict[str, Any]:
    scaffold = task_entry.get("scaffold")
    if not scaffold:
        raise TaskRegistryError(f"Task {task_entry.get('id', '<unknown>')} is missing scaffold")

    fixture_dir = fixtures_dir / Path(scaffold).name
    if not fixture_dir.is_dir():
        raise TaskRegistryError(f"Fixture directory missing for {task_entry.get('id')}: {fixture_dir}")

    fixture_task_path = fixture_dir / "task.json"
    fixture_meta: dict[str, Any] = {}
    if fixture_task_path.exists():
        fixture_meta = _load_json(fixture_task_path)

    merged = dict(task_entry)
    merged.update(_default_fixture_metadata(task_entry))
    merged.update(fixture_meta)
    merged["fixture_dir"] = str(fixture_dir)
    merged["fixture_task_path"] = str(fixture_task_path)
    merged["fixture_file_count"] = len([p for p in fixture_dir.rglob("*") if p.is_file()])
    merged["fixture_hash"] = compute_fixture_hash(fixture_dir)
    merged["expected_artifacts"] = list(dict.fromkeys(merged.get("expected_artifacts") or DEFAULT_ARTIFACTS))
    merged["failure_modes"] = list(dict.fromkeys(merged.get("failure_modes") or DEFAULT_FAILURE_MODES.get(merged["category"], [])))
    merged["tags"] = list(dict.fromkeys(merged.get("tags") or []))
    merged["verify_command"] = str(merged.get("verify_command") or DEFAULT_VERIFY_BY_LANGUAGE.get(merged.get("language", "python"), DEFAULT_VERIFY_BY_LANGUAGE["python"]))
    merged["language"] = str(merged.get("language") or "python")
    return merged


def validate_task(task: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ["id", "name", "category", "difficulty", "description", "scaffold"]:
        if not str(task.get(key, "")).strip():
            errors.append(f"task.{key} is required")

    if task.get("category") not in ALLOWED_CATEGORIES:
        errors.append(f"task.category must be one of {sorted(ALLOWED_CATEGORIES)}")
    if task.get("difficulty") not in ALLOWED_DIFFICULTIES:
        errors.append(f"task.difficulty must be one of {sorted(ALLOWED_DIFFICULTIES)}")

    for numeric_key in ["expected_dod_count", "expected_features"]:
        value = task.get(numeric_key)
        if not isinstance(value, int) or value < 0:
            errors.append(f"task.{numeric_key} must be a non-negative integer")

    if not str(task.get("verify_command", "")).strip():
        errors.append("task.verify_command is required")
    if "{project_dir}" not in str(task.get("verify_command", "")):
        errors.append("task.verify_command must include {project_dir} placeholder")
    if task.get("baseline_expectation") not in {"pass", "fail"}:
        errors.append("task.baseline_expectation must be 'pass' or 'fail'")

    fixture_dir = Path(task.get("fixture_dir", ""))
    if not fixture_dir.is_dir():
        errors.append(f"task.fixture_dir missing: {fixture_dir}")

    expected_artifacts = task.get("expected_artifacts")
    if not isinstance(expected_artifacts, list) or not expected_artifacts:
        errors.append("task.expected_artifacts must be a non-empty list")

    failure_modes = task.get("failure_modes")
    if not isinstance(failure_modes, list) or not failure_modes:
        errors.append("task.failure_modes must be a non-empty list")

    if task.get("category") == "ambiguous" and task.get("expected_dod_count", 0) != 0:
        errors.append("ambiguous tasks must set expected_dod_count to 0")
    if task.get("category") == "ambiguous" and task.get("expected_features", 0) != 0:
        errors.append("ambiguous tasks must set expected_features to 0")

    return errors


def load_task_set(task_set_path: str | Path, fixtures_dir: str | Path) -> dict[str, Any]:
    task_set_path = Path(task_set_path)
    fixtures_dir = Path(fixtures_dir)
    payload = _load_json(task_set_path)
    tasks = [merge_task_definition(task, fixtures_dir) for task in payload.get("tasks", [])]

    validation = []
    seen_ids: set[str] = set()
    seen_scaffolds: set[str] = set()
    for task in tasks:
        validation.extend([f"{task.get('id', '<unknown>')}: {err}" for err in validate_task(task)])
        task_id = task["id"]
        if task_id in seen_ids:
            validation.append(f"duplicate task id: {task_id}")
        seen_ids.add(task_id)
        scaffold = task["scaffold"]
        if scaffold in seen_scaffolds:
            validation.append(f"duplicate scaffold reference: {scaffold}")
        seen_scaffolds.add(scaffold)

    categories = {}
    difficulties = {}
    for task in tasks:
        categories[task["category"]] = categories.get(task["category"], 0) + 1
        difficulties[task["difficulty"]] = difficulties.get(task["difficulty"], 0) + 1

    return {
        "description": payload.get("description", ""),
        "version": payload.get("version", "1.0"),
        "source": str(task_set_path),
        "tasks": tasks,
        "task_count": len(tasks),
        "categories": categories,
        "difficulties": difficulties,
        "validation_errors": validation,
        "is_valid": len(validation) == 0,
    }


def validate_search_vs_holdout(search: dict[str, Any], holdout: dict[str, Any]) -> dict[str, Any]:
    search_ids = {task["id"] for task in search.get("tasks", [])}
    holdout_ids = {task["id"] for task in holdout.get("tasks", [])}
    search_scaffolds = {task["scaffold"] for task in search.get("tasks", [])}
    holdout_scaffolds = {task["scaffold"] for task in holdout.get("tasks", [])}

    overlap_ids = sorted(search_ids & holdout_ids)
    overlap_scaffolds = sorted(search_scaffolds & holdout_scaffolds)

    issues = []
    if overlap_ids:
        issues.append(f"search/holdout overlap on ids: {overlap_ids}")
    if overlap_scaffolds:
        issues.append(f"search/holdout overlap on scaffolds: {overlap_scaffolds}")

    return {
        "search_count": len(search_ids),
        "holdout_count": len(holdout_ids),
        "overlap_ids": overlap_ids,
        "overlap_scaffolds": overlap_scaffolds,
        "is_valid": len(issues) == 0,
        "issues": issues,
    }


def compute_fixture_hash(fixture_dir: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted([p for p in fixture_dir.rglob("*") if p.is_file()]):
        digest.update(str(path.relative_to(fixture_dir)).encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def load_benchmark_suite(config_dir: str | Path, fixtures_dir: str | Path) -> dict[str, Any]:
    config_dir = Path(config_dir)
    search = load_task_set(config_dir / "search-set.json", fixtures_dir)
    holdout = load_task_set(config_dir / "holdout-set.json", fixtures_dir)
    discipline = validate_search_vs_holdout(search, holdout)
    return {
        "search": search,
        "holdout": holdout,
        "discipline": discipline,
        "is_valid": search["is_valid"] and holdout["is_valid"] and discipline["is_valid"],
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Load and validate Meta-Harness task sets")
    parser.add_argument("config_dir", help="Path to config directory")
    parser.add_argument("fixtures_dir", help="Path to fixtures directory")
    args = parser.parse_args()

    suite = load_benchmark_suite(args.config_dir, args.fixtures_dir)
    print(json.dumps(suite, indent=2))
    raise SystemExit(0 if suite["is_valid"] else 1)
