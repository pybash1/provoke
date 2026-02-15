# Database Cleanup Utilities

The project provides two levels of index maintenance: targeted cleanup and full index re-filtering.

## Full Index Re-filtering (`scripts/rerun_filters.py`)

This is the primary tool for bulk-updating the index after configuration changes.

- **Purpose**: Re-evaluates every page in the database against the latest `config.py` heuristics and ML models.
- **Actions**: Updates quality scores, changes quality tiers (e.g., from `ml_uncertain_accept` to `bad`), and optionally deletes rejected pages.
- **Usage**:
  ```bash
  uv run python scripts/rerun_filters.py --live
  ```

## Targeted Maintenance (`provoke/utils/cleanup.py`)

This utility handles specific maintenance tasks, such as purging pages from newly blacklisted domains.

- **Purpose**: Used by the Admin UI to perform streaming cleanup operations.
- **Features**:
  - Keeps track of previously checked URLs to avoid redundant work.
  - Can re-fetch HTML for pages that were indexed without source code.
- **Usage (CLI)**:
  ```bash
  uv run python -m provoke.utils.cleanup [--all]
  ```

## Dependencies

- `sqlite3`: Database operations.
- `provoke.config`: Quality evaluation logic and configuration paths.
- `requests`: For re-fetching pages that are missing HTML content.

## Notes

- Both scripts modify the primary database. It is recommended to back up `index.db` before running extensive re-filtering.
- For a complete re-sync of the index, `scripts/rerun_filters.py --live` is the recommended path.
