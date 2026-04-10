"""
dashboard.py — Baseline (slow) dashboard.

Simulates a dashboard that:
- Loads data with a blocking delay (simulates slow DB query)
- Recomputes all aggregations on every call (no caching)
- Returns all records at once (no pagination)
"""

import time
import random

_DATASET_SIZE = 10_000

def _load_data():
    """Simulate a slow DB query by sleeping and returning a large dataset."""
    time.sleep(0.1)  # simulate 100ms DB round-trip
    random.seed(42)
    return [
        {
            "id": i,
            "user": f"user_{i % 200}",
            "category": random.choice(["A", "B", "C", "D"]),
            "value": random.uniform(1, 1000),
            "active": random.choice([True, False]),
        }
        for i in range(_DATASET_SIZE)
    ]


def get_summary():
    """Load all data and compute aggregated summary. Slow on every call."""
    data = _load_data()
    total = len(data)
    total_value = sum(r["value"] for r in data)
    avg_value = total_value / total if total else 0
    active_count = sum(1 for r in data if r["active"])
    by_category = {}
    for r in data:
        cat = r["category"]
        by_category[cat] = by_category.get(cat, 0) + r["value"]
    top_users = {}
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


def get_page(page: int = 0, page_size: int = 20):
    """Return a page of records. Loads ALL data every time."""
    data = _load_data()
    start = page * page_size
    return data[start: start + page_size]


if __name__ == "__main__":
    t0 = time.perf_counter()
    summary = get_summary()
    t1 = time.perf_counter()
    print(f"Summary loaded in {t1 - t0:.3f}s")
    print(f"Total records: {summary['total_records']}")
    print(f"Avg value: {summary['avg_value']:.2f}")
