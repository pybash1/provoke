# Data Storage (`data/`)

## Purpose

The `data/` directory stores all persistent datasets, including manual labels, logs, and formatted machine learning training/test sets.

## Files

- **`to_label.csv`**: The primary working file for manual content classification.
  - Columns: `url`, `title`, `snippet`, `quality` (`good`, `bad`, or `unsure`).
- **`to_label_done.csv`**: A backup or archive of URLs that have already been labeled.
- **`training_data.txt`**: The combined labeled data formatted for FastText.
- **`train.txt`**: The 75% split used for model training.
- **`test.txt`**: The 25% split used for model evaluation.

## Related Documentation

- [DATA_MANAGEMENT.md](DATA_MANAGEMENT.md): Documentation for `provoke/ml/data_prep.py`.
- [TRAINING_WORKFLOW.md](TRAINING_WORKFLOW.md): Documentation for `provoke/ml/trainer.py`.
