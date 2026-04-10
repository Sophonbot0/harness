"""
dashboard_optimized.py — Optimized dashboard.

Improvements:
1. Data is loaded once and cached in memory (simulated cache with TTL).
2. Aggregations are computed once and cached via functools.lru_cache.
3. Pagination slices the cached dataset — no re-load.
4. Cache can be invalidated explicitly.
"""

import time
import random
import functools
from typing import List, Dict, Any, Optional

_DATASET_SIZE = 10_000
_CACHE_TTL = 60  # seconds

# ---------- internal cache ----------
_data_cache: Optional[List[Dict]] = None
_cache_loaded_at: float = 0.0


def _load_data_cached(force: bool = False) -> List[Dict]:
    """Load data once; return cached copy on subsequent calls within TTL."""
    global _data_cache, _cache_loaded_at
    now = time.monotonic()
    if not force and _data_cache is not None and (now - _cache_loaded_at) < _CACHE_TTL:
        return _data_cache
    # Simulate DB query — only happens on cold load or after TTL
    time.sleep(0.1)
    random.seed(42)
    _data_cache = [
        {
            "id": i,
            "user": f"user_{i % 200}",
            "category": random.choice(["A", "B", "C", "D"]),
            "value": random.uniform(1, 1000),
            "active": random.choice([True, False]),
        }
        for i in range(_DATASET_SIZE)
    ]
    _cache_loaded_at = time.monotonic()
    # Invalidate derived caches when data reloads
    get_summary.cache_clear()
    return _data_cache


def invalidate_cache():
    """Force a fresh data load on next access."""
    global _data_cache, _cache_loaded_at
    _data_cache = None
    _cache_loaded_at = 0.0
    get_summary.cache_clear()


@functools.lru_cache(maxsize=1)
def _compute_summary_from_snapshot(snapshot_id: int):
    """
    Compute aggregations. snapshot_id ties this to a specific data generation
    so the cache is valid as long as the data hasn't changed.
    """
    data = _data_cache  # already loaded before this is called
    total = len(data)
    total_value = sum(r["value"] for r in data)
    avg_value = total_value / total if total else 0
    active_count = sum(1 for r in data if r["active"])
    by_category: Dict[str, float] = {}
    for r in data:
        cat = r["category"]
        by_category[cat] = by_category.get(cat, 0) + r["value"]
    top_users: Dict[str, float] = {}
    for r in data:
        u = r["user"]
        top_users[u] = top_users.get(u, 0) + r["value"]
    top_10 = sorted(top_users.items(), key=lambda x: x[1], reverse=True)[:10]
    return {
        "total_records": total,
        "total_value": total_value,
        "avg_value": avg_value,
        "active_count": active_count,
        "by_category": by_category,
        "top_users": top_10,
    }


# Wrap with a simpler public API that manages the snapshot_id
def get_summary():
    """Return cached aggregated summary."""
    _load_data_cached()
    # Use cache_loaded_at as a snapshot id (converted to int microseconds)
    snapshot_id = int(_cache_loaded_at * 1_000_000)
    return _compute_summary_from_snapshot(snapshot_id)


# Monkeypatch cache_clear onto get_summary so invalidate_cache can clear it
get_summary.cache_clear = _compute_summary_from_snapshot.cache_clear  # type: ignore


def get_page(page: int = 0, page_size: int = 20) -> List[Dict]:
    """Return a page of records using cached dataset — no re-load."""
    data = _load_data_cached()
    start = page * page_size
    return data[start: start + page_size]


if __name__ == "__main__":
    t0 = time.perf_counter()
    summary = get_summary()
    t1 = time.perf_counter()
    print(f"Cold load: {t1 - t0:.3f}s")

    t0 = time.perf_counter()
    summary2 = get_summary()
    t1 = time.perf_counter()
    print(f"Cached load: {t1 - t0:.6f}s")

    print(f"Total records: {summary['total_records']}")
    print(f"Avg value: {summary['avg_value']:.2f}")
