# Eval Report: search-012

## Summary
Successfully created a buggy codebase with 3 intentional bugs across 3 different modules, confirmed exactly 3 test failures, then fixed all bugs to achieve 10/10 passing tests.

## Results

| Phase | Status |
|-------|--------|
| Plan written | ✅ |
| Buggy codebase created | ✅ |
| 3 tests failing confirmed | ✅ (3 failed, 7 passed) |
| All 3 bugs fixed | ✅ |
| All 10 tests passing | ✅ |
| Challenge report | ✅ |

## Test Run (post-fix)
```
10 passed in 0.01s
```

## DoD Items: 9/9 passed
1. ✅ array_utils.py created with off-by-one bug
2. ✅ counter.py created with race condition bug
3. ✅ parser.py created with type coercion bug
4. ✅ test_bugs.py created (10 tests: 3 failing, 7 passing)
5. ✅ Test run confirmed exactly 3 failures
6. ✅ All 3 bugs fixed
7. ✅ Test run confirms all 10 pass
8. ✅ challenge-report.md documents all root causes
9. ✅ eval-report.md and scores.json complete

## Grade: PASS
