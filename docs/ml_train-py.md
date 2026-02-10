# ml_train.py

## Summary

The training and evaluation module for the FastText content classifier.

## Description

`ml_train.py` contains the logic for training a supervised FastText model and evaluating its performance on a held-out test set. It provides detailed metrics including Precision, Recall, and F1 Score, along with a confusion matrix and URL-level error analysis.

### Training Features:

- **Tuning Parameters**: Supports adjusting learning rate (`lr`), epochs, embedding dimension (`dim`), and word n-grams.
- **Bi-grams**: By default, uses `wordNgrams=2` to capture context like "buy now" or "blog post".
- **NumPy 2.0 Patch**: Re-implements the NumPy patch found in other ML modules for consistency.

### Evaluation Features:

- **Confusion Matrix**: Breaks down results into True Positives, True Negatives, False Positives, and False Negatives.
- **Error Tracking**: Lists specific URLs that were misclassified (False Positives and False Negatives) to help debug training data quality.

## Public API / Interfaces

### `train_fasttext_model(...)`

Trains a new model.

- **Arguments**:
  - `train_file` (str): Path to the FastText-formatted training data.
  - `model_path` (str): Where to save the resulting `.bin` file.
  - `lr`, `epoch`, `wordNgrams`, `dim`: Hyperparameters.
- **Returns**: The trained model object.

### `evaluate_model(model_path, test_file)`

Evaluates an existing model.

- **Arguments**:
  - `model_path` (str): Path to the `.bin` model.
  - `test_file` (str): Path to the FastText-formatted test data.
- **Outputs**: Prints statistics and returns `(precision, recall)`.

## Dependencies

- `fasttext`: The machine learning engine.
- `numpy`: Data processing.

## Examples

Training a model via script:

```python
from ml_train import train_fasttext_model, evaluate_model

train_fasttext_model("data/train.txt", "models/content_classifier.bin")
evaluate_model("models/content_classifier.bin", "data/test.txt")
```

## Related

- [ml_classifier-py.md](ml_classifier-py.md)
- [train_classifier-py.md](train_classifier-py.md)
- [ml_data_prep-py.md](ml_data_prep-py.md)
