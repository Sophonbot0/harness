# Challenge Report: 3-Bug Fix Pipeline

## Bug 1 — Off-by-One (array_utils.py)

**Location:** `sliding_window_max`, line `window = arr[i:i + k + 1]`

**Root Cause:** The slice end index was `i + k + 1` instead of `i + k`. Python slices are exclusive at the end, so `arr[i:i+k]` gives exactly `k` elements. Using `k+1` includes one extra element in every window, producing incorrect maximums.

**Fix:** Change `arr[i:i + k + 1]` → `arr[i:i + k]`

---

## Bug 2 — Race Condition (counter.py)

**Location:** `ThreadSafeCounter.increment()`

**Root Cause:** The increment operation read `self._count` into a local variable, then wrote it back — both outside of the lock. With multiple threads, a classic read-modify-write race occurs: two threads read the same value, both increment it locally, and both write back the same result, losing one increment. The artificial `sleep(0.0001)` maximised interleaving to guarantee the failure.

**Fix:** Wrap the entire `self._count += 1` operation inside `with self._lock:`.

---

## Bug 3 — Type Coercion (parser.py)

**Location:** `parse_config`, line `if value:`

**Root Cause:** Python's truthiness check treats `0`, `""`, `False`, and `None` all as falsy. When a caller explicitly passes `timeout=0`, the check `if value:` evaluates to `False`, so the function silently discards the provided value and substitutes the default. The correct check is `if value is not None:`, which only falls back to the default when the key was truly absent from the config.

**Fix:** Change `if value:` → `if value is not None:`
