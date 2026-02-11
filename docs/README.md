# REPOSITORY DOCUMENTATION

Welcome to the documentation for the **Provoke** repository. This project is a specialized web crawler and search engine designed to index high-quality personal blog content while filtering out corporate marketing and low-quality noise.

## DOCUMENTATION STRUCTURE

The documentation is organized into functional modules. Each major component has its own dedicated documentation file:

- **WEB INTERFACE**: [WEB_INTERFACE.md](WEB_INTERFACE.md)
  Describes the Flask administrative dashboard, search UI, and manual labeling tools.
- **CRAWLING SYSTEM**: [CRAWLING_SYSTEM.md](CRAWLING_SYSTEM.md)
  Core logic for web traversal, URL normalization, and persistence.
- **CONFIGURATION & LOGIC**: [CONFIG.md](CONFIG.md)
  Central repository for settings, thresholds, and quality assessment logic (replacing `quality_config.py` and `quality_filter.py`).
- **SEARCH ENGINE**: [SEARCH_ENGINE.md](SEARCH_ENGINE.md)
  Implementation of the SQLite FTS5 and trigram-based search system.
- **MACHINE LEARNING**:
  - [ML_CLASSIFICATION.md](ML_CLASSIFICATION.md): The hybrid ML + Rule-based classifier.
  - [ML_TRAINING.md](ML_TRAINING.md): Training logic and evaluation metrics.
  - [TRAINING_WORKFLOW.md](TRAINING_WORKFLOW.md): Orchestration of the ML lifecycle.
- **DATA & MAINTENANCE**:
  - [DATA_MANAGEMENT.md](DATA_MANAGEMENT.md): Dataset export and augmentation utilities.
  - [DATA_STORAGE.md](DATA_STORAGE.md): Overview of the `data/` directory contents.
  - [INDEX_MAINTENANCE.md](INDEX_MAINTENANCE.md): Tools for purging the search index.
  - [QUALITY_LOGGING.md](QUALITY_LOGGING.md): Rejection tracking and statistics.

## QUICK NAVIGATION

- **[README.md](README.md)**: Root documentation.
- **[ERROR_REDUCTION_GUIDE.md](ERROR_REDUCTION_GUIDE.md)**: Strategies for improving crawler accuracy.
- **[UTILITY_SCRIPTS.md](UTILITY_SCRIPTS.md)**: Overview of diagnostic and maintenance scripts.
- **[TESTING_SUITE.md](TESTING_SUITE.md)**: Information on project tests.

## BINARY ASSETS

- `index.db`: SQLite database containing indexed pages.
- `models/*.bin`: Trained FastText classification models (see [MODELS_OVERVIEW.md](MODELS_OVERVIEW.md)).

## HOW TO UPDATE

To update this documentation:

1. Re-analyze source files for API or structural changes.
2. Modify the corresponding `.md` file in the `docs/` directory.
3. Ensure $README.md$ remains in sync with any new files or major architecture shifts.
