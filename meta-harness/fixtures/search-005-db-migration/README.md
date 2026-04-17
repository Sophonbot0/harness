# Database Migration Script

Write a database migration that adds a 'tags' column (JSON array), migrates existing 'category' data into tags, and provides a rollback script. Must handle tables with 100K+ rows.

- Category: feature
- Difficulty: medium
- Verify: `cd . && python3 -m pytest -v`
