# Plan: Fix 3 Bugs in Different Modules

## Task
Fix 3 intentional bugs across different modules, each with a different root cause.

## Bugs
1. **Off-by-one** in `array_utils.py` — sliding window includes one extra element
2. **Race condition** in `counter.py` — thread-safe counter missing lock on increment
3. **Type coercion** in `parser.py` — string "0" treated as falsy (falsy check instead of None check)

## Definition of Done
1. `array_utils.py` created with off-by-one bug
2. `counter.py` created with race condition bug
3. `parser.py` created with type coercion bug
4. `test_bugs.py` created with 9 tests (3 failing, 6 passing)
5. Test run confirms exactly 3 failures
6. All 3 bugs fixed
7. Test run confirms all 9 pass
8. `challenge-report.md` documents root causes
9. `eval-report.md` and `scores.json` complete
