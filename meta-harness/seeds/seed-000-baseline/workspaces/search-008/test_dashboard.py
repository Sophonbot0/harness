"""
test_dashboard.py — pytest suite for dashboard optimization.

Tests:
1. Optimized returns same results as baseline
2. Cached calls are faster than cold calls (≥5× speedup)
3. Pagination returns correct subsets
4. Cache invalidation forces a fresh load
5. Large dataset handled without error
6. Multiple pages return non-overlapping records
7. Page boundary correctness
"""

import sys
import os
import time
import pytest

sys.path.insert(0, os.path.dirname(__file__))

import dashboard as slow
import dashboard_optimized as fast


@pytest.fixture(autouse=True)
def reset_cache():
    """Ensure cache is cleared before each test."""
    fast.invalidate_cache()
    yield
    fast.invalidate_cache()


# ── Test 1: correctness ───────────────────────────────────────────────────────

def test_summary_total_records_match():
    slow_s = slow.get_summary()
    fast_s = fast.get_summary()
    assert slow_s["total_records"] == fast_s["total_records"]


def test_summary_avg_value_match():
    slow_s = slow.get_summary()
    fast_s = fast.get_summary()
    assert abs(slow_s["avg_value"] - fast_s["avg_value"]) < 0.001


def test_summary_active_count_match():
    slow_s = slow.get_summary()
    fast_s = fast.get_summary()
    assert slow_s["active_count"] == fast_s["active_count"]


def test_summary_by_category_match():
    slow_s = slow.get_summary()
    fast_s = fast.get_summary()
    for cat in slow_s["by_category"]:
        assert abs(slow_s["by_category"][cat] - fast_s["by_category"][cat]) < 0.001


def test_summary_top_users_match():
    slow_s = slow.get_summary()
    fast_s = fast.get_summary()
    slow_top = dict(slow_s["top_users"])
    fast_top = dict(fast_s["top_users"])
    assert set(slow_top.keys()) == set(fast_top.keys())
    for user in slow_top:
        assert abs(slow_top[user] - fast_top[user]) < 0.001


# ── Test 2: caching speedup ───────────────────────────────────────────────────

def test_cached_call_faster_than_cold():
    # cold call
    fast.invalidate_cache()
    t0 = time.perf_counter()
    fast.get_summary()
    cold_time = time.perf_counter() - t0

    # warm call (cached)
    times = []
    for _ in range(5):
        t0 = time.perf_counter()
        fast.get_summary()
        times.append(time.perf_counter() - t0)
    warm_avg = sum(times) / len(times)

    speedup = cold_time / warm_avg if warm_avg > 0 else float("inf")
    assert speedup >= 5, f"Expected ≥5× speedup, got {speedup:.1f}×"


def test_warm_summary_under_1ms():
    fast.get_summary()  # prime
    t0 = time.perf_counter()
    fast.get_summary()
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert elapsed_ms < 1.0, f"Warm call took {elapsed_ms:.2f}ms, expected <1ms"


# ── Test 3: pagination ────────────────────────────────────────────────────────

def test_page_size_correct():
    page = fast.get_page(0, 20)
    assert len(page) == 20


def test_page_0_starts_at_id_0():
    page = fast.get_page(0, 20)
    assert page[0]["id"] == 0
    assert page[19]["id"] == 19


def test_page_1_starts_at_id_20():
    page = fast.get_page(1, 20)
    assert page[0]["id"] == 20


def test_pages_non_overlapping():
    p0 = fast.get_page(0, 50)
    p1 = fast.get_page(1, 50)
    ids_0 = {r["id"] for r in p0}
    ids_1 = {r["id"] for r in p1}
    assert ids_0.isdisjoint(ids_1)


def test_pagination_matches_baseline():
    slow_page = slow.get_page(2, 20)
    fast_page = fast.get_page(2, 20)
    assert len(slow_page) == len(fast_page)
    for s, f in zip(slow_page, fast_page):
        assert s["id"] == f["id"]
        assert abs(s["value"] - f["value"]) < 0.0001


# ── Test 4: cache invalidation ────────────────────────────────────────────────

def test_invalidate_forces_reload():
    fast.get_summary()  # prime cache
    fast.invalidate_cache()
    # After invalidation, cold load should take ≥ 80ms (sleep is 100ms)
    t0 = time.perf_counter()
    fast.get_summary()
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert elapsed_ms >= 80, f"Expected cold load ≥80ms after invalidate, got {elapsed_ms:.1f}ms"


def test_second_call_after_invalidate_is_fast():
    fast.get_summary()  # cold
    fast.invalidate_cache()
    fast.get_summary()  # cold again after invalidate
    t0 = time.perf_counter()
    fast.get_summary()  # now warm
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert elapsed_ms < 1.0


# ── Test 5: large dataset ─────────────────────────────────────────────────────

def test_large_dataset_no_error():
    summary = fast.get_summary()
    assert summary["total_records"] == 10_000
    assert summary["total_value"] > 0
    assert len(summary["by_category"]) == 4
    assert len(summary["top_users"]) == 10


def test_last_page_partial():
    # 10000 records / 300 per page → last full page index = 33 (9900-10199, but only 100 remain)
    last_page = fast.get_page(33, 300)
    assert len(last_page) == 100  # 10000 - 33*300 = 100
