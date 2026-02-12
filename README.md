# Provoke

A specialized web crawler and search engine designed to index high-quality personal blog content while filtering out corporate marketing and low-quality noise.

## Quick Start

```bash
# Run the web interface
uv run python provoke/web/app.py

# Crawl a URL
uv run python provoke/crawler.py https://example.com/blog 2

# Search from command line
uv run python provoke/indexer.py "your query"

# Train the ML classifier
uv run python -m provoke.ml.trainer --export --limit 1000
# ... label data in data/to_label.csv ...
uv run python -m provoke.ml.trainer --train
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
provoke/
├── config.py          # Central configuration and quality logic
├── crawler.py         # Web crawling engine
├── indexer.py         # Search engine
├── ml/                # Machine learning components
│   ├── classifier.py
│   ├── data_prep.py
│   ├── trainer.py
│   └── training.py
├── utils/             # Utility modules
│   ├── cleanup.py
│   ├── logger.py
│   ├── model_stats.py
│   └── landing_page.py
└── web/               # Flask web interface
    └── app.py
```

## Requirements

- Python >= 3.9
- Dependencies managed with `uv` (see `pyproject.toml`)

## License

[Add your license here]
