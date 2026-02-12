import fasttext
import os
import numpy as np
from provoke.config import config

# NumPy 2.0 Compatibility Patch for FastText
# FastText uses np.array(..., copy=False) which crashes in NumPy 2.0+
# when a copy is required. This patch makes it fallback to asarray.
_original_array = np.array


def _patched_array(obj, *args, **kwargs):
    if kwargs.get("copy") is False:
        return np.asarray(obj, dtype=kwargs.get("dtype"))
    return _original_array(obj, *args, **kwargs)


np.array = _patched_array


def train_fasttext_model(
    train_file: str,
    model_path: str,
    lr: float | None = None,
    epoch: int | None = None,
    wordNgrams: int | None = None,
    dim: int | None = None,
    verbose: int | None = None,
):
    """Train FastText supervised classifier."""
    lr = lr if lr is not None else config.ML_LEARNING_RATE
    epoch = epoch if epoch is not None else config.ML_EPOCHS
    wordNgrams = wordNgrams if wordNgrams is not None else config.ML_WORD_NGRAMS
    dim = dim if dim is not None else config.ML_EMBEDDING_DIM
    verbose = verbose if verbose is not None else config.ML_VERBOSE

    if not os.path.exists(train_file):
        print(f"Error: {train_file} not found.")
        return None

    print(f"Training FastText model on {train_file}...")

    os.makedirs(os.path.dirname(model_path), exist_ok=True)

    model = fasttext.train_supervised(
        input=train_file,
        lr=lr,  # Learning rate
        epoch=epoch,  # Training epochs
        wordNgrams=wordNgrams,  # Use bigrams (2) for better context
        dim=dim,  # Embedding dimension
        loss="softmax",  # Classification loss
        verbose=verbose,
    )

    # Save model
    model.save_model(model_path)
    print(f"Model saved to {model_path}")

    return model


def evaluate_model(model_path: str, test_file: str):
    """Evaluate FastText model on test set."""

    if not os.path.exists(model_path):
        print(f"Error: {model_path} not found.")
        return

    if not os.path.exists(test_file):
        print(f"Error: {test_file} not found.")
        return

    model = fasttext.load_model(model_path)

    # FastText built-in evaluation
    result = model.test(test_file)

    samples = result[0]
    precision = result[1]
    recall = result[2]

    print(f"\n=== Model Evaluation ===")
    print(f"Test samples: {samples}")
    print(f"Precision: {precision:.3f}")
    print(f"Recall: {recall:.3f}")

    f1 = 0
    if (precision + recall) > 0:
        f1 = 2 * (precision * recall) / (precision + recall)
    print(f"F1 Score: {f1:.3f}")

    # Manual confusion matrix
    print_confusion_matrix(model, test_file)

    return precision, recall


def print_confusion_matrix(model, test_file: str):
    """Print confusion matrix for detailed analysis."""

    true_pos = true_neg = false_pos = false_neg = 0
    fp_urls = []
    fn_urls = []

    with open(test_file, "r", encoding="utf-8") as f:
        for line in f:
            # Extract true label and text
            parts = line.strip().split(" ", 1)
            true_label = parts[0]
            text = parts[1] if len(parts) > 1 else ""

            # Extract URL if present
            url = "N/A"
            if "url=" in text:
                try:
                    url = text.split("url=")[1].split(" ")[0]
                except IndexError:
                    pass

            # Predict
            pred_labels, confidences = model.predict(text)

            if not pred_labels or len(pred_labels) == 0:
                continue

            pred_label = pred_labels[0]

            # Count
            if true_label == "__label__good" and pred_label == "__label__good":
                true_pos += 1
            elif true_label == "__label__bad" and pred_label == "__label__bad":
                true_neg += 1
            elif true_label == "__label__bad" and pred_label == "__label__good":
                false_pos += 1
                fp_urls.append(url)
            elif true_label == "__label__good" and pred_label == "__label__bad":
                false_neg += 1
                fn_urls.append(url)

    print(f"\nConfusion Matrix:")
    print(f"True Positives (good->good): {true_pos}")
    print(f"True Negatives (bad->bad): {true_neg}")
    print(f"False Positives (bad->good): {false_pos}")
    print(f"False Negatives (good->bad): {false_neg}")

    if fp_urls:
        print("\n--- False Positives (Bad URLs predicted as Good) ---")
        for u in fp_urls:
            print(u)

    if fn_urls:
        print("\n--- False Negatives (Good URLs predicted as Bad) ---")
        for u in fn_urls:
            print(u)
