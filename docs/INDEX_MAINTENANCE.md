# Index Maintenance

## Summary

Utilities for maintaining and analyzing the search index database.

## Description

The `provoke/utils/` directory contains scripts for cleaning up the database, checking model performance against indexed data, and monitoring quality statistics.

## Available Utilities

### Cleanup (`provoke/utils/cleanup.py`)

Re-evaluates all indexed pages against current quality filters and removes low-quality entries.

**Usage:**
```bash
uv run python -m provoke.utils.cleanup
```

**When to use:**
- After tightening quality thresholds in `config.py`
- After blacklisting a domain that already has pages in the index
- When you want to re-validate the entire index with updated filters

**How it works:**
1. Loads blacklist and whitelist from database
2. Fetches all pages from the `pages` table
3. Re-evaluates each page using `evaluate_page_quality()` from `provoke.config`
4. Deletes pages that fail quality checks
5. For pages missing HTML content, attempts to re-fetch from the original URL

---

### Model Stats (`provoke/utils/model_stats.py`)

Analyzes the current ML model's predictions on all indexed pages.

**Usage:**
```bash
uv run python -m provoke.utils.model_stats
```

**Output:**
- Total pages classified as good/bad/uncertain
- Confidence breakdown (high/low confidence for each category)
- List of URLs classified as bad (sorted by confidence)

**When to use:**
- After training a new model to see how it performs on existing data
- To identify potentially misclassified pages
- To validate model quality before deployment

---

### Quality Logger (`provoke/utils/logger.py`)

Tracks acceptance/rejection statistics during crawling.

**Used by:** `provoke.crawler` (not typically run standalone)

**Logs to:**
- `quality_stats.csv`: Structured rejection data
- `rejected_urls.log`: Human-readable rejection log

## Dependencies

- `sqlite3`: Database operations
- `provoke.config`: Quality evaluation logic and paths
- `provoke.ml.classifier`: Model loading for `model_stats.py`
- `requests`: Re-fetching pages in `cleanup.py`

## Related

- [CLEANUP.md](CLEANUP.md) - Detailed cleanup documentation
- [CRAWLING_SYSTEM.md](CRAWLING_SYSTEM.md)
- [ML_CLASSIFICATION.md](ML_CLASSIFICATION.md)
