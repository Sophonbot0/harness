# Plan: CLI Tool with Subcommands

## Assumptions
- Python 3.9+ with argparse (stdlib only)
- Config file is JSON, written to `./pipeline.json`
- `run` reads config and simulates a pipeline (prints stages)
- `status` reads config and reports state
- Exit codes: 0=success, 1=error, 2=usage error

## Features & Coverage Matrix

| # | Feature | DoD |
|---|---------|-----|
| F1 | Subcommand: init | Creates `pipeline.json` with default config; exits 0; overwrites if exists |
| F2 | Subcommand: run | Reads config, executes pipeline stages, prints output; exits 1 if no config; respects --verbose |
| F3 | Subcommand: status | Reads config, prints current state; exits 1 if no config |
| F4 | Global flags | --help shows usage for main and each subcommand; --verbose increases output detail |
| F5 | Exit codes & error handling | 0 on success, 1 on runtime error, 2 on bad usage; stderr for errors |
