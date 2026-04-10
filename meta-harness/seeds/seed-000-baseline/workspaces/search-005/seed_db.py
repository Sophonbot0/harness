"""seed_db.py – Create test.db with a posts table and sample data."""
import sqlite3
import json
import random

CATEGORIES = ["tech", "science", "sports", "politics", "entertainment", "health", "finance"]

def seed(db_path="test.db", row_count=110_000):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS posts")
    cur.execute("""
        CREATE TABLE posts (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            title    TEXT NOT NULL,
            category TEXT NOT NULL
        )
    """)
    batch = []
    for i in range(1, row_count + 1):
        cat = random.choice(CATEGORIES)
        batch.append((f"Post {i}", cat))
        if len(batch) == 5000:
            cur.executemany("INSERT INTO posts (title, category) VALUES (?, ?)", batch)
            conn.commit()
            batch = []
    if batch:
        cur.executemany("INSERT INTO posts (title, category) VALUES (?, ?)", batch)
        conn.commit()
    count = cur.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
    print(f"Seeded {count} rows into {db_path}")
    conn.close()

if __name__ == "__main__":
    seed()
