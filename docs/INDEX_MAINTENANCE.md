# Index Maintenance

## Summary

Utilities for maintaining and analyzing the search index database.

## Description

The project provides tools for cleaning up the database, checking model performance against indexed data, and monitoring quality statistics. Most maintenance operations are performed via scripts in the `scripts/` directory.

## Available Utilities

### Re-filtering & Cleanup (`scripts/rerun_filters.py`)

Re-evaluates all indexed pages against current quality filters and removes low-quality entries or updates their scores/tiers.

**Usage:**

```bash
# Dry run (show what would be changed)
uv run python scripts/rerun_filters.py

# Live run (apply changes to database)
uv run python scripts/rerun_filters.py --live
```

**When to use:**

- After tightening quality thresholds in `provoke/config.py`.
- After blacklisting a domain that already has pages in the index.
- When you want to re-validate the entire index with updated filters.

---

### Internal Cleanup Logic (`provoke/utils/cleanup.py`)

This module contains the logic for purging individual domains or stale pages, primarily used by the Admin UI (`/admin/cleanup` route).

---

### Model Stats (`provoke/utils/model_stats.py`)

Analyzes the current ML model's predictions on all indexed pages.

**Usage:**

```bash
uv run python -m provoke.utils.model_stats
```

**Output:**

- Total pages classified as good/bad/uncertain.
- Confidence breakdown.
- List of URLs classified as bad (sorted by confidence).

---

### Quality Logger (`provoke/utils/logger.py`)

Tracks acceptance/rejection statistics during crawling.

**Logs to:**

- `data/quality_stats.csv`: Structured rejection data.
- `data/rejected_urls.log`: Human-readable rejection log.

## Dependencies

- `sqlite3`: Database operations.
- `provoke.config`: Quality evaluation logic and paths.
- `provoke.ml.classifier`: Model loading for `model_stats.py`.

## Related

- [UTILITY_SCRIPTS.md](UTILITY_SCRIPTS.md)
- [CRAWLING_SYSTEM.md](CRAWLING_SYSTEM.md)
- [ML_CLASSIFICATION.md](ML_CLASSIFICATION.md)
