# Plan: Fix sort_utils.py

## Bugs Identified

1. **Crashes on empty input** — `len(numbers) == 1` check doesn't guard against empty list; `range(len([]))` would work but the early return skips empty case entirely (returns nothing for `[]`).
2. **Removes duplicates** — dedup block using `set()` strips duplicate values.
3. **Mutates input** — `result = numbers` aliases the input list instead of copying it.

## Definition of Done

- [ ] `sort_numbers([])` returns `[]`
- [ ] `sort_numbers([3,1,2,1,3])` returns `[1,1,2,3,3]`
- [ ] `sort_numbers([-3,-1,-2,0,1])` returns `[-3,-2,-1,0,1]`
- [ ] All 6 pytest tests pass
