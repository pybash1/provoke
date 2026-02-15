# ML Training Workflow (`scripts/train_classifier.py`)

## Summary

The high-level CLI workflow for managing the lifecycle of the content classifier, from data export to model training.

## Description

The ML training workflow involves collecting quality data, labeling it, and training a FastText model. This process is orchestrated by `scripts/train_classifier.py`, which provides a three-step workflow:

1.  **Export**: Gathers URLs from the index and rejected logs for manual labeling.
2.  **Train**: Converts labeled CSV data into FastText format, splits it into training/test sets, and trains the model.
3.  **Evaluate**: Runs the trained model against a test set to determine accuracy.

## CLI Usage

```bash
uv run python scripts/train_classifier.py --export [--limit N]
uv run python scripts/train_classifier.py --train
uv run python scripts/train_classifier.py --evaluate
```

#### Commands:

- `--export`: Creates `data/to_label.csv`. It takes a mix of indexed pages (likely good) and rejected URLs (pre-filled as 'bad').
- `--train`:
  - Generates training files from the CSV.
  - Trains the model and saves it to `models/model.bin`.
- `--evaluate`: Runs evaluation metrics on the current model and test set.

## Dependencies

- `provoke.ml.trainer`: Core orchestration logic.
- `provoke.ml.data_prep`: For data manipulation and file generation.
- `provoke.ml.training`: For core FastText training and evaluation.
- `provoke.config`: For file paths and configuration.

## Examples

### Complete Training Cycle:

1.  **Export data**:
    ```bash
    uv run python scripts/train_classifier.py --export --limit 1000
    ```
2.  **Manual Step**: Open `data/to_label.csv` or use the Admin Labeling UI (`/admin/label`) to fill in the `quality` column.
3.  **Train Model**:
    ```bash
    uv run python scripts/train_classifier.py --train
    ```
4.  **Verify**: Check the precision and F1 score output at the end of the training.

## Notes/Limitations

- Running `--export` will overwrite `data/to_label.csv`. Be careful if you have unsaved progress.
- The default split ratio is 75% training and 25% testing.

## Related

- [ML_TRAINING.md](ML_TRAINING.md)
- [DATA_MANAGEMENT.md](DATA_MANAGEMENT.md)
- [ML_CLASSIFICATION.md](ML_CLASSIFICATION.md)
