# Plan: Database Migration – tags column

## Task
Add a `tags` JSON array column to an existing SQLite table, migrate `category` data into it, and provide a rollback script. Must handle 100K+ rows efficiently via batching.

## Features
1. `seed_db.py` – Creates `test.db` with a `posts` table containing sample rows including a 100K+ row scenario.
2. `migrate.py` – Adds `tags TEXT` (JSON array) column, copies `category` → `["<category>"]` in batches of 5000.
3. `rollback.py` – Drops the `tags` column (via table rebuild) and restores state.
4. `test_migration.py` – pytest suite covering forward migration, data integrity, rollback, large table batching.

## Definition of Done
- [ ] `seed_db.py` creates `test.db` with 100K+ rows
- [ ] `migrate.py` adds `tags` column and migrates data without data loss
- [ ] Batching is used (chunk_size=5000) so 100K rows don't lock the DB
- [ ] `rollback.py` removes `tags` column and returns DB to prior state
- [ ] All pytest tests pass (test_migration.py)
