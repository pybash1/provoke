# Backward compatibility shim - moved to provoke.ml.training
from provoke.ml.training import (
    evaluate_model,
    print_confusion_matrix,
    train_fasttext_model,
)

__all__ = [
    "evaluate_model",
    "print_confusion_matrix",
    "train_fasttext_model",
]
