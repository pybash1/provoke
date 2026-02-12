# ML Training Core (`provoke/ml/training.py`)

## Summary

Core FastText model training and evaluation functions used by the ML training workflow.

## Description

`provoke/ml/training.py` provides low-level functions for training FastText supervised classification models and evaluating their performance. It includes a NumPy 2.0 compatibility patch to ensure FastText works with modern NumPy versions.

This module is typically used via `provoke/ml/trainer.py` (the CLI orchestrator), but can be imported directly for custom training scripts.

## Public API / Interfaces

### Training Functions

#### `train_fasttext_model(train_file, model_path, lr=None, epoch=None, wordNgrams=None, dim=None, verbose=None)`

Trains a FastText supervised classifier.

**Parameters:**
- `train_file` (str): Path to FastText-format training data (from `create_fasttext_training_file()`)
- `model_path` (str): Where to save the trained `.bin` model
- `lr` (float): Learning rate (default: `config.ML_LEARNING_RATE` = 0.7)
- `epoch` (int): Training epochs (default: `config.ML_EPOCHS` = 25)
- `wordNgrams` (int): N-gram size (default: `config.ML_WORD_NGRAMS` = 2)
- `dim` (int): Embedding dimension (default: `config.ML_EMBEDDING_DIM` = 100)
- `verbose` (int): Verbosity level (default: `config.ML_VERBOSE` = 2)

**Returns:** Trained FastText model object, or None if training fails.

#### `evaluate_model(model_path, test_file)`

Evaluates a trained model against a test set and prints metrics.

**Parameters:**
- `model_path` (str): Path to the `.bin` model file
- `test_file` (str): Path to FastText-format test data

**Returns:** Tuple of `(precision, recall)`

**Output:**
- Test sample count
- Precision score
- Recall score
- F1 score
- Confusion matrix (TP/TN/FP/FN)
- Lists of false positive and false negative URLs

### Helper Functions

#### `print_confusion_matrix(model, test_file)`

Generates a detailed confusion matrix with misclassified URL lists.

## Training Data Format

FastText expects one sample per line:
```
__label__good url=https://example.com/post title=My Post Content here...
__label__bad url=https://example.com/pricing title=Pricing Content here...
```

Use `provoke.ml.data_prep.create_fasttext_training_file()` to convert from CSV.

## Dependencies

- `fasttext`: Facebook's FastText library
- `numpy`: Data processing (includes v2.0 compatibility patch)
- `provoke.config`: For hyperparameter defaults

## Example

```python
from provoke.ml.training import train_fasttext_model, evaluate_model
from provoke.config import config

# Train model
train_fasttext_model(
    train_file="data/train.txt",
    model_path="models/content_classifier.bin",
    lr=0.7,
    epoch=25
)

# Evaluate
evaluate_model("models/content_classifier.bin", "data/test.txt")
```

## Notes/Limitations

- **NumPy 2.0 Patch**: The module patches `np.array` at import time to handle FastText's use of `copy=False` which is incompatible with NumPy 2.0+.
- **Loss Function**: Uses `softmax` loss for multi-class classification.
- **Binary Models**: Models are saved as `.bin` files which can be loaded with `fasttext.load_model()`.

## Related

- [TRAINING_WORKFLOW.md](TRAINING_WORKFLOW.md)
- [ML_CLASSIFICATION.md](ML_CLASSIFICATION.md)
- [DATA_MANAGEMENT.md](DATA_MANAGEMENT.md)
