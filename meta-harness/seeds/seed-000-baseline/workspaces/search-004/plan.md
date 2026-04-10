# CLI Tool Plan

## Features
1. `init` subcommand — create config.json with defaults
2. `run` subcommand — read config, simulate pipeline, print steps
3. `status` subcommand — read config + state file, show current state
4. `--help` flag at top level and per subcommand
5. `--verbose` flag for detailed output
6. Proper exit codes: 0=success, 1=error, 2=usage error

## Definition of Done
- [ ] cli.py exists with argparse-based CLI
- [ ] `init` creates config.json with default values
- [ ] `run` reads config and simulates pipeline with step output
- [ ] `status` reads config+state, shows current state
- [ ] `--verbose` flag produces extra output
- [ ] Exit codes: 0 on success, 1 on error (missing files etc), 2 on bad usage
- [ ] Tests pass for all subcommands and flags
