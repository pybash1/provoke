# data/

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

- [ml_data_prep.py](../docs/ml_data_prep-py.md): The script that manages these files.
- [train_classifier.py](../docs/train_classifier-py.md): The CLI tool for processing this data.
