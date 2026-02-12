# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Provoke** is a specialized web crawler and search engine designed to index high-quality personal blog content while filtering out corporate marketing and low-quality noise. It combines rule-based heuristics with machine learning (FastText) for content classification.

- **Package name**: `inked` (historical)
- **Python version**: >= 3.9
- **Dependency management**: `uv` (see `pyproject.toml` and `uv.lock`)

## Common Commands

### Development

```bash
# Run the web interface (Flask server on port 4000)
uv run python app.py

# Crawl a single URL (depth = crawl levels)
uv run python crawler.py <url> <depth>

# Crawl from a file containing seed URLs
uv run python crawler.py urls.txt 2

# Crawl with JavaScript rendering (Playwright)
uv run python crawler.py <url> 1 --dynamic

# Run tests
uv run pytest tests/

# Run a single test file
uv run pytest tests/test_quality_filter.py
```

### ML Training Workflow

```bash
# Step 1: Export data for labeling (creates data/to_label.csv)
uv run python train_classifier.py --export --limit 1000

# Step 2: Manually label data in data/to_label.csv (good/bad/unsure)

# Step 3: Train the model
uv run python train_classifier.py --train

# Step 4: Evaluate model performance
uv run python train_classifier.py --evaluate

# Automated training loop (trains until precision >= 0.998)
./train_until_ready.sh
```

### Utilities

```bash
# Check model performance against existing data
uv run python check_model_stats.py

# Clean up low-quality pages from database
uv run python cleanup.py

# Search from command line
python indexer.py "your search query"
```

## Project Structure

The codebase is organized into a main `provoke/` package with submodules:

```
provoke/
├── ml/                    # Machine learning components
│   ├── classifier.py     # FastText classifier with rule-based corrections
│   ├── data_prep.py      # Training data preparation utilities
│   ├── training.py       # Model training and evaluation
│   └── trainer.py        # CLI training orchestrator
└── utils/                 # Utility modules
    ├── logger.py         # Quality logging (was quality_logger.py)
    ├── cleanup.py        # Database cleanup utility
    ├── model_stats.py    # Model statistics checker
    └── landing_page.py   # Landing page detection filters

# Backward-compatible shims at root (for existing imports):
ml_classifier.py, ml_data_prep.py, ml_train.py, train_classifier.py,
quality_logger.py, cleanup.py, check_model_stats.py, landing_page_filter.py
```

### Core Components

1. **`config.py`** - Central nervous system containing:
   - All application settings (thresholds, paths, detection patterns)
   - Quality assessment algorithms (`evaluate_page_quality()`, `calculate_unified_score()`)
   - Environment-based configuration via `PROVOKE_ENV` (development/production)

2. **`crawler.py`** - Web crawling engine:
   - `SimpleCrawler` class handles recursive URL traversal
   - Quality evaluation before saving (via `config.evaluate_page_quality()`)
   - Auto-blacklisting: domains with too many rejections are automatically blocked
   - Global stop: crawl halts if `consecutive_rejection_threshold` (default 25) pages are rejected in a row
   - Optional Playwright integration for JavaScript-rendered content (`--dynamic` flag)

3. **`indexer.py`** - Search engine:
   - `SearchEngine` class implements two-stage search:
     - Stage 1: SQLite FTS5 with trigram tokenizer for fast substring matching
     - Stage 2: Fuzzy fallback using `difflib.SequenceMatcher` when FTS yields poor results
   - Snippet highlighting via FTS5 `snippet()` function

4. **`provoke/ml/classifier.py`** - Hybrid ML + Rule classifier:
   - FastText-based classification with `__label__good` / `__label__bad` labels
   - Rule-based corrections: rejects homepages/shallow URLs, rescues RSS feeds and About pages
   - NumPy 2.0 compatibility patch included

5. **`app.py`** - Flask web interface:
   - Search page (`/`)
   - Admin dashboard (`/admin`) with real-time stats
   - Domain management (blacklist/whitelist)
   - Crawl trigger with log streaming (`/admin/crawl`)
   - Manual labeling UI (`/admin/label`) updating `data/to_label.csv`
   - Manual page insertion (`/admin/manual_insert`)

### Training Pipeline

The ML training workflow spans multiple files:

1. **`train_classifier.py`** (or `python -m provoke.ml.trainer`) - Orchestrates the lifecycle:
   - `--export`: Gathers URLs from index + rejected logs via `provoke.ml.data_prep`
   - `--train`: Converts CSV to FastText format, splits train/test, trains model via `provoke.ml.training`
   - `--evaluate`: Runs model against test set

2. **`provoke/ml/data_prep.py`** - Data manipulation utilities

3. **`provoke/ml/training.py`** - Core FastText training and evaluation

### Data Storage

- **`index.db`** (SQLite): Contains:
  - `pages` table: indexed content with quality scores
  - `pages_trigram` (FTS5 virtual table): full-text search index (kept in sync via triggers)
  - `blacklisted_domains` / `whitelisted_domains` tables

- **`data/to_label.csv`** - Pending manual labels for training
- **`quality_stats.csv`** - Rejection statistics for analysis
- **`models/*.bin`** - Trained FastText models

### Quality Assessment

The unified quality score (0-100) combines:
- **Text ratio**: meaningful text vs HTML markup
- **Readability**: Flesch Reading Ease score
- **Ad score**: detection of ad networks and tracking scripts
- **Corporate score**: e-commerce detection, marketing language, CTA density

Thresholds defined in `config.THRESHOLDS`:
- `unified_score_threshold` (default 40): minimum score for indexing
- `min_words` (100), `max_words` (8000)
- `min_text_ratio` (0.1)

## Configuration

Environment variables (all optional):
- `PROVOKE_ENV`: `development` (default) or `production`
- `PROVOKE_DB_PATH`: database location (default: `index.db`)
- `PROVOKE_HOST`/`PROVOKE_PORT`: server binding (default: `127.0.0.1:4000`)

## Documentation

Comprehensive docs in `docs/` directory:
- `CONFIG.md`: Configuration and quality logic details
- `CRAWLING_SYSTEM.md`: Crawler architecture
- `ML_CLASSIFICATION.md`: ML module details
- `TRAINING_WORKFLOW.md`: Training pipeline
- `SEARCH_ENGINE.md`: Search implementation
- `WEB_INTERFACE.md`: Flask app details
