"""test_migration.py – pytest suite for the migration pipeline."""
import sqlite3
import json
import os
import pytest

from seed_db import seed
from migrate import migrate
from rollback import rollback

DB = "/tmp/test_migration_test.db"


@pytest.fixture(autouse=True)
def fresh_db():
    if os.path.exists(DB):
        os.remove(DB)
    yield
    if os.path.exists(DB):
        os.remove(DB)


def get_cols(db_path):
    conn = sqlite3.connect(db_path)
    cols = [r[1] for r in conn.execute("PRAGMA table_info(posts)").fetchall()]
    conn.close()
    return cols


# ── Seed tests ────────────────────────────────────────────────────────────────

def test_seed_creates_table():
    seed(DB, row_count=100)
    cols = get_cols(DB)
    assert "id" in cols
    assert "title" in cols
    assert "category" in cols


def test_seed_row_count():
    seed(DB, row_count=500)
    conn = sqlite3.connect(DB)
    count = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
    conn.close()
    assert count == 500


def test_seed_no_tags_column_initially():
    seed(DB, row_count=50)
    assert "tags" not in get_cols(DB)


# ── Migration tests ───────────────────────────────────────────────────────────

def test_migrate_adds_tags_column():
    seed(DB, row_count=100)
    migrate(DB)
    assert "tags" in get_cols(DB)


def test_migrate_populates_tags_from_category():
    seed(DB, row_count=200)
    migrate(DB)
    conn = sqlite3.connect(DB)
    rows = conn.execute("SELECT category, tags FROM posts LIMIT 50").fetchall()
    conn.close()
    for category, tags_json in rows:
        tags = json.loads(tags_json)
        assert isinstance(tags, list)
        assert len(tags) == 1
        assert tags[0] == category


def test_migrate_no_null_tags_after_migration():
    seed(DB, row_count=300)
    migrate(DB)
    conn = sqlite3.connect(DB)
    nulls = conn.execute("SELECT COUNT(*) FROM posts WHERE tags IS NULL").fetchone()[0]
    conn.close()
    assert nulls == 0


def test_migrate_idempotent():
    seed(DB, row_count=100)
    migrate(DB)
    migrate(DB)  # Second call should not raise
    assert "tags" in get_cols(DB)


def test_migrate_preserves_row_count():
    seed(DB, row_count=1000)
    conn = sqlite3.connect(DB)
    before = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
    conn.close()
    migrate(DB)
    conn = sqlite3.connect(DB)
    after = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
    conn.close()
    assert before == after


# ── Rollback tests ────────────────────────────────────────────────────────────

def test_rollback_removes_tags_column():
    seed(DB, row_count=100)
    migrate(DB)
    rollback(DB)
    assert "tags" not in get_cols(DB)


def test_rollback_preserves_category_data():
    seed(DB, row_count=200)
    conn = sqlite3.connect(DB)
    before_cats = set(r[0] for r in conn.execute("SELECT category FROM posts").fetchall())
    conn.close()
    migrate(DB)
    rollback(DB)
    conn = sqlite3.connect(DB)
    after_cats = set(r[0] for r in conn.execute("SELECT category FROM posts").fetchall())
    conn.close()
    assert before_cats == after_cats


def test_rollback_preserves_row_count():
    seed(DB, row_count=500)
    conn = sqlite3.connect(DB)
    before = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
    conn.close()
    migrate(DB)
    rollback(DB)
    conn = sqlite3.connect(DB)
    after = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
    conn.close()
    assert before == after


def test_rollback_idempotent():
    seed(DB, row_count=100)
    migrate(DB)
    rollback(DB)
    rollback(DB)  # Second call should not raise
    assert "tags" not in get_cols(DB)


# ── Large table test ──────────────────────────────────────────────────────────

def test_large_table_migration():
    """Simulate 100K+ row migration and verify all tags populated correctly."""
    seed(DB, row_count=110_000)
    migrate(DB)
    conn = sqlite3.connect(DB)
    total = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
    migrated = conn.execute("SELECT COUNT(*) FROM posts WHERE tags IS NOT NULL").fetchone()[0]
    # Spot-check 1000 rows
    rows = conn.execute("SELECT category, tags FROM posts ORDER BY RANDOM() LIMIT 1000").fetchall()
    conn.close()
    assert total == 110_000
    assert migrated == 110_000
    for category, tags_json in rows:
        tags = json.loads(tags_json)
        assert tags == [category]
