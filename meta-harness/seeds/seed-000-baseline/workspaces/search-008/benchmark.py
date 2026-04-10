"""
benchmark.py — Measures wall-clock performance of baseline vs optimised dashboard.
"""

import time
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import dashboard as slow
import dashboard_optimized as fast

RUNS = 5


def measure(fn, label, runs=RUNS):
    times = []
    for _ in range(runs):
        t0 = time.perf_counter()
        fn()
        times.append(time.perf_counter() - t0)
    avg = sum(times) / len(times)
    print(f"  {label:40s} avg={avg*1000:.1f}ms  min={min(times)*1000:.1f}ms")
    return avg


print("=" * 60)
print("BENCHMARK: Dashboard performance")
print("=" * 60)

print("\n[Baseline — no cache, reloads every call]")
slow_cold = measure(slow.get_summary, "get_summary() cold x5")

print("\n[Optimized — cold first call]")
fast.invalidate_cache()
fast_cold_times = []
for i in range(RUNS):
    fast.invalidate_cache()
    t0 = time.perf_counter()
    fast.get_summary()
    fast_cold_times.append(time.perf_counter() - t0)
avg_cold = sum(fast_cold_times) / len(fast_cold_times)
print(f"  {'get_summary() cold (invalidated)':40s} avg={avg_cold*1000:.1f}ms")

print("\n[Optimized — warm/cached calls]")
fast.invalidate_cache()
fast.get_summary()  # prime the cache
fast_warm = measure(fast.get_summary, "get_summary() warm (cached)")

print("\n[Pagination — baseline vs optimized]")
slow_page = measure(lambda: slow.get_page(0, 20), "baseline get_page(0,20)")
fast_page = measure(lambda: fast.get_page(0, 20), "optimized get_page(0,20)")

print("\n" + "=" * 60)
print("RESULTS SUMMARY")
print("=" * 60)
speedup_cached = slow_cold / fast_warm if fast_warm > 0 else float("inf")
speedup_page = slow_page / fast_page if fast_page > 0 else float("inf")
print(f"  Cached summary speedup vs baseline : {speedup_cached:.1f}×")
print(f"  Cached page speedup vs baseline    : {speedup_page:.1f}×")
print(f"  Cold optimized vs baseline         : {slow_cold/avg_cold:.1f}×  (should be ~1×)")
print("=" * 60)
