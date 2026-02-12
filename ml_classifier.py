# Backward compatibility shim - moved to provoke.ml.classifier
from provoke.ml.classifier import (
    ContentClassifier,
    get_classifier,
    is_commercial_or_low_quality,
    is_likely_homepage,
    is_special_good_format,
)

__all__ = [
    "ContentClassifier",
    "get_classifier",
    "is_commercial_or_low_quality",
    "is_likely_homepage",
    "is_special_good_format",
]
