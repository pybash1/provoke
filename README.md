# Provoke

A specialized web crawler and search engine designed to index high-quality personal blog content while filtering out corporate marketing and low-quality noise.

## Quick Start

```bash
# Run the web interface
uv run python scripts/app.py

# Crawl a URL
uv run python scripts/crawler.py https://example.com/blog 2

# Search from command line
uv run python scripts/indexer.py "your query"

# Train the ML classifier
uv run python scripts/train_classifier.py --export --limit 1000
# ... label data in data/to_label.csv ...
uv run python scripts/train_classifier.py --train
```

## Documentation

Comprehensive documentation is in the `docs/` directory:

- [WEB_INTERFACE.md](docs/WEB_INTERFACE.md) - Flask web app and admin dashboard
- [CRAWLING_SYSTEM.md](docs/CRAWLING_SYSTEM.md) - Web crawler documentation
- [SEARCH_ENGINE.md](docs/SEARCH_ENGINE.md) - Search implementation
- [CONFIG.md](docs/CONFIG.md) - Configuration and quality logic
- [ML_CLASSIFICATION.md](docs/ML_CLASSIFICATION.md) - ML classifier
- [TRAINING_WORKFLOW.md](docs/TRAINING_WORKFLOW.md) - ML training workflow
- [INDEX_MAINTENANCE.md](docs/INDEX_MAINTENANCE.md) - Database maintenance utilities

See [docs/README.md](docs/README.md) for full documentation index.

## Project Structure

```
provoke/               # Core application package
├── config.py          # Central configuration and quality logic
├── crawler.py         # Web crawling engine
├── indexer.py         # Search engine
├── ml/                # Machine learning components
├── utils/             # Utility modules
└── web/               # Flask web interface

scripts/               # Executable scripts and utilities
├── app.py             # Web interface entry point
├── crawler.py         # Crawler entry point
├── indexer.py         # Search entry point
├── train_classifier.py # ML training entry point
└── rerun_filters.py   # Database maintenance
```

## Requirements

- Python >= 3.9
- Dependencies managed with `uv` (see `pyproject.toml`)

## License

[Add your license here]
