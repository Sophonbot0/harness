#!/usr/bin/env python3
"""CLI tool with init, run, and status subcommands."""

import argparse
import json
import os
import sys
import datetime

CONFIG_FILE = "config.json"
STATE_FILE = ".state.json"

DEFAULTS = {
    "project": "my-project",
    "version": "1.0.0",
    "pipeline": ["build", "test", "deploy"],
    "created_at": None,
}


def log(msg, verbose=False, force=False):
    if force or verbose:
        print(msg)


def cmd_init(args):
    if os.path.exists(CONFIG_FILE) and not args.force:
        print(f"ERROR: {CONFIG_FILE} already exists. Use --force to overwrite.", file=sys.stderr)
        sys.exit(1)
    config = dict(DEFAULTS)
    config["created_at"] = datetime.datetime.utcnow().isoformat()
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
    print(f"Initialized config at {CONFIG_FILE}")
    if args.verbose:
        print(f"  project : {config['project']}")
        print(f"  version : {config['version']}")
        print(f"  pipeline: {config['pipeline']}")
    sys.exit(0)


def cmd_run(args):
    if not os.path.exists(CONFIG_FILE):
        print(f"ERROR: {CONFIG_FILE} not found. Run 'init' first.", file=sys.stderr)
        sys.exit(1)
    with open(CONFIG_FILE) as f:
        config = json.load(f)
    steps = config.get("pipeline", [])
    print(f"Running pipeline for project '{config.get('project')}'...")
    results = []
    for i, step in enumerate(steps, 1):
        if args.verbose:
            print(f"  [{i}/{len(steps)}] Executing step: {step} ... ", end="", flush=True)
        else:
            print(f"  Step {i}: {step}")
        # simulate work
        results.append({"step": step, "status": "done"})
        if args.verbose:
            print("done")
    state = {
        "last_run": datetime.datetime.utcnow().isoformat(),
        "steps": results,
        "status": "completed",
    }
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
    print("Pipeline completed successfully.")
    sys.exit(0)


def cmd_status(args):
    if not os.path.exists(CONFIG_FILE):
        print(f"ERROR: {CONFIG_FILE} not found. Run 'init' first.", file=sys.stderr)
        sys.exit(1)
    with open(CONFIG_FILE) as f:
        config = json.load(f)
    print(f"Project : {config.get('project')}")
    print(f"Version : {config.get('version')}")
    if not os.path.exists(STATE_FILE):
        print("Status  : not run yet")
        if args.verbose:
            print("  (no state file found)")
        sys.exit(0)
    with open(STATE_FILE) as f:
        state = json.load(f)
    print(f"Status  : {state.get('status', 'unknown')}")
    print(f"Last run: {state.get('last_run', 'N/A')}")
    if args.verbose:
        for s in state.get("steps", []):
            print(f"  {s['step']}: {s['status']}")
    sys.exit(0)


def build_parser():
    parser = argparse.ArgumentParser(
        prog="cli",
        description="A simple pipeline CLI tool.",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")

    subs = parser.add_subparsers(dest="command", metavar="COMMAND")
    subs.required = True

    # init
    p_init = subs.add_parser("init", help="Create config.json with defaults")
    p_init.add_argument("--force", action="store_true", help="Overwrite existing config")
    p_init.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")

    # run
    p_run = subs.add_parser("run", help="Execute the pipeline")
    p_run.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")

    # status
    p_status = subs.add_parser("status", help="Show current pipeline state")
    p_status.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    # merge top-level verbose into subcommand namespace
    if not hasattr(args, "verbose"):
        args.verbose = False

    dispatch = {"init": cmd_init, "run": cmd_run, "status": cmd_status}
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
