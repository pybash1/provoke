# Utility Scripts

This project centralizes executable scripts in the `scripts/` directory. These scripts serve as entry points for the core functionality and provide various maintenance tools.

## Core Entry Points

- `scripts/app.py`: Runs the Flask web application (Search UI and Admin Dashboard).
- `scripts/crawler.py`: CLI entry point for the web crawler.
- `scripts/indexer.py`: CLI tool for testing search queries directly.
- `scripts/train_classifier.py`: Management script for exporting data and training/evaluating the ML model.

## Maintenance & Diagnostics

- `scripts/rerun_filters.py`: Re-evaluates all indexed pages against current `config` rules. It can update scores or delete rejected pages. Use `--live` to apply changes.
- `scripts/train_until_ready.sh`: A shell script that loops training until a precision threshold is met. See [AUTOMATED_TRAINING.md](AUTOMATED_TRAINING.md).
- `scripts/index_from_rss.py`: Specialized script to index pages directly from RSS feeds, bypassing standard filters but applying ML checks.
- `scripts/list_feeds_and_sitemaps.py`: Discovers and lists RSS feeds and sitemaps from indexed pages.

## Internal Utility Modules

These are located in `provoke/utils/` and are generally used per-package or by the scripts above:

- `provoke/utils/cleanup.py`: Internal logic for purging the index (used by the Admin UI).
- `provoke/utils/model_stats.py`: Analyzes current model predictions on indexed data.
- `provoke/utils/logger.py`: Implements the `QualityLogger` for tracking crawl rejections.

## Configuration & Setup

- `pyproject.toml` & `uv.lock`: Project metadata and dependency management (using `uv`).
- `.gitignore`: Version control exclusions.
