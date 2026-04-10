# Plan: Simple Bug Fix — sort_utils.py

## Requirements
Fix `sort_numbers` so it:
1. Handles empty input without crashing
2. Preserves duplicates in output
3. Correctly sorts negative numbers
4. Does not mutate the input list

## Coverage Matrix

| Feature | DoD |
|---|---|
| F1: Empty input | `sort_numbers([])` returns `[]` without error |
| F2: Duplicates | `sort_numbers([3,1,2,1,3])` == `[1,1,2,3,3]` |
| F3: Negative numbers | `sort_numbers([-3,-1,-2,0,1])` == `[-3,-2,-1,0,1]` |
| F4: Basic sort | `sort_numbers([3,1,2])` == `[1,2,3]` |
| F5: Edge cases | Single element and already-sorted lists work |

## Verify
```
python3 -m pytest test_sort.py -v
```

## Assumptions
- Python 3.9+ environment
- Only numeric lists need to be supported
