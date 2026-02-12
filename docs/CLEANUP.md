# cleanup.py

## Summary

A storage maintenance script for purging invalid or low-quality pages from the database.

## Description

`cleanup.py` scans the `pages` table in `index.db` and applies current filtering rules to existing entries. This is useful when:

1.  A new domain has been blacklisted.
2.  Quality thresholds in `config.py` have been tightened.
3.  The ML model has been updated and you want to re-evalute previous entries.

## Public API / Interfaces

- `cleanup_index()`:
  - Loads the blacklist from the database.
  - Iterates through all indexed pages.
  - If a page is blacklisted or fails `evaluate_page_quality` (from `config.py`), it is deleted from the DB.

## Dependencies

- `sqlite3`
- `config` (replaces `quality_filter`)

## Example

```bash
uv run python cleanup.py
```

## Notes/Limitations

- This script modifies the primary database. It is recommended to back up `index.db` before running.
