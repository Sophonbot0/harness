# Challenge Report: CLI Tool with Subcommands

## C1: Missing config on run
- **Severity**: Medium
- **Repro**: `python3 pipeline_cli.py run`
- **Expected**: Exit 1, error to stderr
- **Result**: PASS

## C2: Missing config on status
- **Repro**: `python3 pipeline_cli.py status`
- **Expected**: Exit 1, error to stderr
- **Result**: PASS

## C3: No subcommand given
- **Repro**: `python3 pipeline_cli.py`
- **Expected**: Exit 2, help printed
- **Result**: PASS

## C4: Double init overwrites
- **Repro**: `python3 pipeline_cli.py init && python3 pipeline_cli.py init`
- **Expected**: No crash, file overwritten
- **Result**: PASS

## C5: Verbose flag before subcommand
- **Repro**: `python3 pipeline_cli.py -v run`
- **Expected**: Verbose output with stage counters
- **Result**: PASS

## C6: --help on subcommand
- **Repro**: `python3 pipeline_cli.py init --help`
- **Expected**: Exit 0 with subcommand help
- **Result**: PASS

## C7: State persists after run
- **Repro**: `python3 pipeline_cli.py init && python3 pipeline_cli.py run && python3 pipeline_cli.py status`
- **Expected**: State shows "completed"
- **Result**: PASS
