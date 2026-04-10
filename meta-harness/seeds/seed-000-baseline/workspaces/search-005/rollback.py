"""rollback.py – Reverse migration: remove tags column via table rebuild."""
import sqlite3

def rollback(db_path="test.db"):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cols = [row[1] for row in cur.execute("PRAGMA table_info(posts)").fetchall()]
    if "tags" not in cols:
        print("Nothing to roll back.")
        conn.close()
        return

    # SQLite doesn't support DROP COLUMN before 3.35; use table rebuild
    cur.execute("BEGIN")
    cur.execute("""
        CREATE TABLE posts_backup (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            title    TEXT NOT NULL,
            category TEXT NOT NULL
        )
    """)
    cur.execute("INSERT INTO posts_backup (id, title, category) SELECT id, title, category FROM posts")
    cur.execute("DROP TABLE posts")
    cur.execute("ALTER TABLE posts_backup RENAME TO posts")
    conn.commit()
    print("Rollback complete. 'tags' column removed.")
    conn.close()

if __name__ == "__main__":
    rollback()
