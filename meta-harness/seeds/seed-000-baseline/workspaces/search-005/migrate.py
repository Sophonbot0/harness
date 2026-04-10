"""migrate.py – Forward migration: add tags column and populate from category."""
import sqlite3
import json

BATCH_SIZE = 5000

def migrate(db_path="test.db"):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Check if already migrated
    cols = [row[1] for row in cur.execute("PRAGMA table_info(posts)").fetchall()]
    if "tags" in cols:
        print("Migration already applied.")
        conn.close()
        return

    # Add tags column
    cur.execute("ALTER TABLE posts ADD COLUMN tags TEXT")
    conn.commit()
    print("Added 'tags' column.")

    # Migrate in batches
    total = cur.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
    migrated = 0
    offset = 0
    while offset < total:
        rows = cur.execute(
            "SELECT id, category FROM posts WHERE tags IS NULL LIMIT ?", (BATCH_SIZE,)
        ).fetchall()
        if not rows:
            break
        updates = [(json.dumps([row[1]]), row[0]) for row in rows]
        cur.executemany("UPDATE posts SET tags = ? WHERE id = ?", updates)
        conn.commit()
        migrated += len(rows)
        offset += len(rows)
        print(f"  Migrated {migrated}/{total} rows...")

    print(f"Migration complete. {migrated} rows updated.")
    conn.close()

if __name__ == "__main__":
    migrate()
