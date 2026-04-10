"""Tests for cli.py"""
import json
import os
import subprocess
import sys
import tempfile
import pytest

CLI = os.path.join(os.path.dirname(__file__), "cli.py")
PYTHON = sys.executable


def run_cli(*args, cwd=None):
    result = subprocess.run(
        [PYTHON, CLI] + list(args),
        capture_output=True, text=True, cwd=cwd
    )
    return result


# ── init ──────────────────────────────────────────────────────────────────────

def test_init_creates_config(tmp_path):
    r = run_cli("init", cwd=tmp_path)
    assert r.returncode == 0
    cfg = json.loads((tmp_path / "config.json").read_text())
    assert cfg["project"] == "my-project"
    assert "pipeline" in cfg
    assert cfg["created_at"] is not None


def test_init_verbose(tmp_path):
    r = run_cli("init", "--verbose", cwd=tmp_path)
    assert r.returncode == 0
    assert "project" in r.stdout


def test_init_fails_if_exists(tmp_path):
    run_cli("init", cwd=tmp_path)
    r = run_cli("init", cwd=tmp_path)
    assert r.returncode == 1
    assert "already exists" in r.stderr


def test_init_force_overwrites(tmp_path):
    run_cli("init", cwd=tmp_path)
    r = run_cli("init", "--force", cwd=tmp_path)
    assert r.returncode == 0


# ── run ───────────────────────────────────────────────────────────────────────

def test_run_requires_config(tmp_path):
    r = run_cli("run", cwd=tmp_path)
    assert r.returncode == 1
    assert "not found" in r.stderr


def test_run_executes_pipeline(tmp_path):
    run_cli("init", cwd=tmp_path)
    r = run_cli("run", cwd=tmp_path)
    assert r.returncode == 0
    assert "completed" in r.stdout
    state = json.loads((tmp_path / ".state.json").read_text())
    assert state["status"] == "completed"
    assert len(state["steps"]) == 3


def test_run_verbose(tmp_path):
    run_cli("init", cwd=tmp_path)
    r = run_cli("run", "--verbose", cwd=tmp_path)
    assert r.returncode == 0
    assert "Executing step" in r.stdout


# ── status ────────────────────────────────────────────────────────────────────

def test_status_requires_config(tmp_path):
    r = run_cli("status", cwd=tmp_path)
    assert r.returncode == 1
    assert "not found" in r.stderr


def test_status_before_run(tmp_path):
    run_cli("init", cwd=tmp_path)
    r = run_cli("status", cwd=tmp_path)
    assert r.returncode == 0
    assert "not run yet" in r.stdout


def test_status_after_run(tmp_path):
    run_cli("init", cwd=tmp_path)
    run_cli("run", cwd=tmp_path)
    r = run_cli("status", cwd=tmp_path)
    assert r.returncode == 0
    assert "completed" in r.stdout
    assert "Last run" in r.stdout


def test_status_verbose(tmp_path):
    run_cli("init", cwd=tmp_path)
    run_cli("run", cwd=tmp_path)
    r = run_cli("status", "--verbose", cwd=tmp_path)
    assert r.returncode == 0
    assert "build" in r.stdout


# ── help ──────────────────────────────────────────────────────────────────────

def test_help_exits_zero():
    r = run_cli("--help")
    assert r.returncode == 0
    assert "init" in r.stdout
    assert "run" in r.stdout
    assert "status" in r.stdout


def test_subcommand_help():
    for sub in ["init", "run", "status"]:
        r = run_cli(sub, "--help")
        assert r.returncode == 0
        assert sub in r.stdout


# ── bad usage ─────────────────────────────────────────────────────────────────

def test_no_subcommand_exits_nonzero():
    r = run_cli()
    assert r.returncode != 0
