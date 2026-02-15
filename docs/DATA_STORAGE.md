# Data Storage

The project uses a mix of root-level and `data/` directory files for persistence and logging.

## Core Database

- **`index.db`**: The primary SQLite database containing indexed pages, FTS tables, and domain metadata (blacklists/whitelists).

## Machine Learning Data (`data/`)

- **`data/to_label.csv`**: The primary working file for manual content classification.
- **`data/to_label_done.csv`**: A backup or archive of URLs that have already been labeled.
- **`data/training_data.txt`**: The combined labeled data formatted for FastText.
- **`data/train.txt`**: The split used for model training.
- **`data/test.txt`**: The split used for model evaluation.

## Logs & Statistics

- **`quality_stats.csv`**: Structured CSV log tracking every URL rejection with reasons and heuristic scores.
- **`rejected_urls.log`**: Human-readable log of rejected URLs for quick diagnostic review.

## Related Documentation

- [DATA_MANAGEMENT.md](DATA_MANAGEMENT.md): Documentation for `provoke/ml/data_prep.py`.
- [TRAINING_WORKFLOW.md](TRAINING_WORKFLOW.md): Documentation for the ML lifecycle scripts.
