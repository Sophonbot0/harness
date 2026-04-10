# Challenge Report: sort_utils.py

## C1: Empty list
- **Risk**: Crash on `len()` of empty input
- **Repro**: `python3 -c "from sort_utils import sort_numbers; print(sort_numbers([]))"`
- **Status**: PASS — returns `[]`

## C2: Duplicate preservation
- **Risk**: Duplicates removed or collapsed
- **Repro**: `python3 -c "from sort_utils import sort_numbers; assert sort_numbers([3,1,2,1,3]) == [1,1,2,3,3]"`
- **Status**: PASS

## C3: Negative numbers
- **Risk**: Wrong ordering with mixed positive/negative
- **Repro**: `python3 -c "from sort_utils import sort_numbers; assert sort_numbers([-3,-1,-2,0,1]) == [-3,-2,-1,0,1]"`
- **Status**: PASS

## C4: Input mutation
- **Risk**: Original list modified in place
- **Repro**: `python3 -c "from sort_utils import sort_numbers; x=[3,1,2]; sort_numbers(x); assert x==[3,1,2]"`
- **Status**: PASS — uses `list(numbers)` copy

## C5: Single element
- **Repro**: `python3 -c "from sort_utils import sort_numbers; assert sort_numbers([42]) == [42]"`
- **Status**: PASS

## C6: Already sorted
- **Repro**: `python3 -c "from sort_utils import sort_numbers; assert sort_numbers([1,2,3,4,5]) == [1,2,3,4,5]"`
- **Status**: PASS

## Summary
All 6 challenges pass. No critical issues found.
