# Data Pipeline

Build a 3-stage data pipeline: ingest (read JSON files from directory), transform (normalize dates, deduplicate, validate schema), load (write to SQLite). Include progress reporting and error recovery.

- Category: feature
- Difficulty: hard
- Verify: `cd . && python3 -m pytest -v`
