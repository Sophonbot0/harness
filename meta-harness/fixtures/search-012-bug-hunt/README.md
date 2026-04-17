# Existing Codebase Bug Hunt

The test suite has 3 failing tests. Fix all 3 bugs without breaking anything else. The bugs are in different modules and have different root causes (off-by-one, race condition, type coercion).

- Category: bug_fix
- Difficulty: hard
- Verify: `cd . && python3 -m pytest -v`
