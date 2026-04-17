#!/usr/bin/env python3
"""Verify that every benchmark fixture can be materialized in isolation and passes its baseline verify command."""

from __future__ import annotations

import json
import shlex
import subprocess
import tempfile
from pathlib import Path

from task_executor import setup_project
from task_registry import load_benchmark_suite


BASE = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE / "config"
FIXTURES_DIR = BASE / "fixtures"


def run_command(command: str, cwd: Path, timeout: int = 30) -> tuple[int, str, str]:
    proc = subprocess.run(
        command,
        cwd=str(cwd),
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return proc.returncode, proc.stdout, proc.stderr


def verify_task(task: dict, sandbox_root: Path) -> dict:
    project_dir = Path(setup_project(task, str(FIXTURES_DIR), str(sandbox_root)))
    command = str(task["verify_command"]).replace("{project_dir}", shlex.quote(str(project_dir)))
    code, out, err = run_command(command, project_dir)
    expectation = task.get("baseline_expectation", "pass")
    ok = (code == 0) if expectation == "pass" else (code != 0)
    return {
        "task_id": task["id"],
        "category": task.get("category"),
        "difficulty": task.get("difficulty"),
        "project_dir": str(project_dir),
        "verify_command": command,
        "baseline_expectation": expectation,
        "returncode": code,
        "ok": ok,
        "stdout": out[-4000:],
        "stderr": err[-4000:],
    }


def main():
    suite = load_benchmark_suite(CONFIG_DIR, FIXTURES_DIR)
    if not suite["is_valid"]:
        print(json.dumps({"ok": False, "error": "benchmark suite invalid", "suite": suite}, indent=2))
        raise SystemExit(1)

    results = []
    with tempfile.TemporaryDirectory(prefix="meta-harness-fixtures-") as tmp:
        sandbox_root = Path(tmp)
        for bucket in ["search", "holdout"]:
            for task in suite[bucket]["tasks"]:
                results.append(verify_task(dict(task), sandbox_root / bucket))

    failures = [r for r in results if not r["ok"]]
    report = {
        "ok": len(failures) == 0,
        "total": len(results),
        "passed": len(results) - len(failures),
        "failed": len(failures),
        "results": results,
    }
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["ok"] else 1)


if __name__ == "__main__":
    main()
