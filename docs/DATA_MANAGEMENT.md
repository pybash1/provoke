# ML Data Preparation (`provoke/ml/data_prep.py`)

## Summary

Utility module for managing machine learning datasets, including exporting data for labeling and formatting it for FastText training.

## Description

`provoke/ml/data_prep.py` provides the glue between the search index (SQLite), the crawler logs, and the ML training process. It handles the extraction of data from various sources to create a balanced labeling set and ensures the final training file is correctly formatted for FastText.

### Key Data Operations:

1.  **Exporting**: Pulls random samples from `index.db` into a CSV for manual labeling.
2.  **Augmentation**: Scans `quality_stats.csv` for URLs that the crawler rejected and adds them to the labeling pool (pre-marked as `bad`).
3.  **FastText Formatting**: Converts CSV rows into the special `__label__...` text format. It includes additional features like `url=` and `title=` prefixes to help the model learn from more than just the body text.
4.  **Splitting**: Shuffles and divides the finalized dataset into training and test files.

## Public API / Interfaces

### `export_indexed_pages(output_file, limit=500)`

Exports URLs currently in the index to a CSV.

### `augment_from_rejected_urls(output_file, limit=100)`

Fetches titles and snippets for recently rejected URLs and appends them to the CSV.

### `create_fasttext_training_file(labeled_csv, output_file)`

The core formatting function.

- **Workflow**: For each labeled row, it attempts to fetch the full page content from the DB (falling back to the snippet) and writes a single line to the output file.

### `split_training_data(input_file, train_file, test_file, test_ratio=0.25)`

Splits the formatted text file into two parts for training and evaluation.

## Dependencies

- `sqlite3`: To fetch indexed content.
- `requests` & `BeautifulSoup`: To fetch metadata for rejected URLs during augmentation.
- `csv`: For managing the labeling files.
- `config`: For file paths.

## Notes/Limitations

- `augment_from_rejected_urls` performs live HTTP requests to get titles/snippets for URLs that weren't saved to the DB.
- `create_fasttext_training_file` excludes rows in the CSV marked as `unsure`.

## Related

- [TRAINING_WORKFLOW.md](TRAINING_WORKFLOW.md)
- [ML_TRAINING.md](ML_TRAINING.md)
