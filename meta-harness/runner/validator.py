#!/usr/bin/env python3
"""
Candidate Validator — Interface validation before expensive evaluation.

Validates that a candidate harness directory has the correct structure,
all required files exist, prompts are non-empty, and no forbidden
modifications were made.

Paper principle: "if H passes interface validation then evaluate"
"""

import json
import os
import sys
from pathlib import Path
from typing import List, Tuple


REQUIRED_FILES = [
    "SKILL.md",
    "prompts/planner-system.md",
    "prompts/generator-system.md",
    "prompts/adversary-system.md",
    "prompts/evaluator-system.md",
]

OPTIONAL_FILES = [
    "references/grading-criteria.md",
    "templates/plan-template.md",
    "templates/challenge-report-template.md",
    "templates/eval-report-template.md",
    "meta/policy.json",
]

# Patterns that should never appear in harness files
UNSAFE_PATTERNS = [
    "rm -rf",
    "os.system(",
    "subprocess.call(",
    "eval(",
    "__import__(",
    "exec(",
]

MIN_PROMPT_LENGTH = 50  # Minimum chars for a prompt to be considered non-empty


def validate_candidate(candidate_dir: str) -> Tuple[bool, List[str]]:
    """Validate a candidate harness directory.
    
    Returns:
        (is_valid, list_of_issues)
    """
    issues = []
    harness_dir = os.path.join(candidate_dir, "harness")
    
    if not os.path.isdir(harness_dir):
        return False, [f"Missing harness/ directory in {candidate_dir}"]
    
    # Check required files exist
    for req_file in REQUIRED_FILES:
        filepath = os.path.join(harness_dir, req_file)
        if not os.path.isfile(filepath):
            issues.append(f"MISSING required file: {req_file}")
    
    if issues:
        return False, issues
    
    # Check prompts are non-empty and meaningful
    for req_file in REQUIRED_FILES:
        filepath = os.path.join(harness_dir, req_file)
        try:
            content = Path(filepath).read_text()
            if len(content.strip()) < MIN_PROMPT_LENGTH:
                issues.append(f"TOO SHORT ({len(content.strip())} chars): {req_file}")
        except Exception as e:
            issues.append(f"UNREADABLE: {req_file} — {e}")
    
    # Check for unsafe patterns
    for root, _, files in os.walk(harness_dir):
        for fname in files:
            fpath = os.path.join(root, fname)
            rel = os.path.relpath(fpath, harness_dir)
            try:
                content = Path(fpath).read_text()
                for pattern in UNSAFE_PATTERNS:
                    if pattern in content:
                        issues.append(f"UNSAFE pattern '{pattern}' in {rel}")
            except (UnicodeDecodeError, PermissionError):
                pass  # Binary files or permission issues — skip
    
    # Check no files outside allowed directories
    allowed_dirs = {"prompts", "references", "templates", "meta"}
    for item in os.listdir(harness_dir):
        item_path = os.path.join(harness_dir, item)
        if os.path.isdir(item_path) and item not in allowed_dirs:
            issues.append(f"UNEXPECTED directory: {item}/")
    
    # Check metadata.json exists in candidate root
    meta_path = os.path.join(candidate_dir, "metadata.json")
    if not os.path.isfile(meta_path):
        issues.append("MISSING metadata.json in candidate root")
    else:
        try:
            meta = json.loads(Path(meta_path).read_text())
            if "id" not in meta:
                issues.append("metadata.json missing 'id' field")
            if "hypothesis" not in meta and "description" not in meta:
                issues.append("metadata.json missing 'hypothesis' or 'description'")
        except json.JSONDecodeError as e:
            issues.append(f"INVALID metadata.json: {e}")
    
    is_valid = len([i for i in issues if i.startswith(("MISSING", "UNSAFE", "INVALID", "TOO SHORT"))]) == 0
    return is_valid, issues


def validate_and_report(candidate_dir: str) -> dict:
    """Validate and return structured report."""
    is_valid, issues = validate_candidate(candidate_dir)
    
    report = {
        "candidate_dir": candidate_dir,
        "is_valid": is_valid,
        "issues": issues,
        "issue_count": len(issues),
        "critical_count": len([i for i in issues if i.startswith(("MISSING", "UNSAFE", "INVALID"))]),
        "warning_count": len([i for i in issues if i.startswith(("TOO SHORT", "UNEXPECTED"))]),
    }
    
    return report


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validator.py <candidate_dir>")
        sys.exit(1)
    
    report = validate_and_report(sys.argv[1])
    print(json.dumps(report, indent=2))
    sys.exit(0 if report["is_valid"] else 1)
