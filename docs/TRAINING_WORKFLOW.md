# ML Training Workflow (`train_classifier.py`)

## Summary

The high-level CLI workflow for managing the lifecycle of the content classifier, from data export to model training.

## Description

`train_classifier.py` orchestrates the process of creating a custom machine learning model for content quality. It provides a three-step workflow:

1.  **Export**: Gathers URLs from the index and rejected logs (via `ml_data_prep.py`) for manual labeling.
2.  **Train**: Converts labeled CSV data into FastText format, splits it into training/test sets, and trains the model (via `ml_train.py`).
3.  **Evaluate**: Runs the trained model against a test set to determine accuracy.

## Public API / Interfaces

### CLI Usage:

```bash
uv run python train_classifier.py --export [--limit N]
uv run python train_classifier.py --train
uv run python train_classifier.py --evaluate
```

#### Commands:

- `--export`: Creates `data/to_label.csv` (path from `config.py`). It takes a mix of indexed pages (likely good) and rejected URLs (pre-filled as 'bad').
- `--train`:
  - Generates `data/training_data.txt` from the CSV.
  - Creates `data/train.txt` and `data/test.txt`.
  - Trains the model and saves it to `models/model.bin`.
- `--evaluate`: Runs evaluation metrics on the current model and test set.

## Dependencies

- `ml_data_prep`: For data manipulation and file generation.
- `ml_train`: For core FastText training and evaluation.
- `config`: For file paths and configuration.

## Examples

### Complete Training Cycle:

1.  **Export data**:
    ```bash
    uv run python train_classifier.py --export --limit 1000
    ```
2.  **Manual Step**: Open `data/to_label.csv` and fill in the `quality` column (`good` or `bad`).
3.  **Train Model**:
    ```bash
    uv run python train_classifier.py --train
    ```
4.  **Verify**: Check the precision and F1 score output at the end of the training.

## Notes/Limitations

- Running `--export` will overwrite `data/to_label.csv`. Be careful if you have unsaved progress.
- The default split ratio is 75% training and 25% testing.

## Related

- [ML_TRAINING.md](ML_TRAINING.md)
- [DATA_MANAGEMENT.md](DATA_MANAGEMENT.md)
- [ML_CLASSIFICATION.md](ML_CLASSIFICATION.md)
