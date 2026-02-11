# ML Classifier (`ml_classifier.py`)

## Summary

The machine learning module that classifies web content as 'good' (article/blog) or 'bad' (spam/marketing/homepage) using Facebook's FastText.

## Description

`ml_classifier.py` provides an "enhanced check" system that combines raw machine learning predictions with rule-based heuristics. This hybrid approach helps reduce common ML errors, such as misclassifying homepages as high-quality content or overlooking short but valuable personal blog posts.

### Features:

- **FastText Integration**: Loads a supervised model to predict content labels based on text, title, and URL features.
- **Rule-Based Correction**:
  - **Homepage Detection**: Rejects shallow URLs or those with generic titles (e.g., "Home", "Welcome").
  - **Special Format Rescue**: Ensures RSS feeds and "About Me" pages from known good domains are preserved.
  - **Commercial Filter**: Penalizes e-commerce and legal pages (cart, checkout, privacy policy).
- **NumPy 2.0 Patch**: Includes a compatibility fix for FastText's use of non-copying arrays.

## Public API / Interfaces

### `ContentClassifier` Class

#### Methods:

- **`__init__(model_path)`**: Loads the `.bin` model file.
- **`predict(text, url="", title="", threshold=0.7)`**: Returns raw label and confidence.
- **`enhanced_check(url, title, content, ml_label, ml_confidence)`**: Adjusts confidence based on rules.
- **`is_acceptable(text, url="", title="")`**: Final boolean decision for the crawler.

### Global Interface

- `get_classifier(model_path)`: Returns a singleton instance of `ContentClassifier`.

## Dependencies

- `fasttext`: The core classification library.
- `numpy`: Data processing (patched for v2.0+).
- `beautifulsoup4`: For title/text extraction in certain checks.

## Examples

Using the classifier programmatically:

```python
from ml_classifier import get_classifier

clf = get_classifier("models/content_classifier.bin")
if clf:
    accepted, reason, confidence = clf.is_acceptable(text, url, title)
    print(f"Accepted: {accepted} ({reason})")
```

## Notes/Limitations

- The classifier requires a pre-trained model file in `models/`.
- FastText treats labels as `__label__good` and `__label__bad`.

## Suggested Tests

- Verify that a known marketing page (e.g., a pricing page) is correctly rejected with a combined ML + Rule score.
- Verify that a personal blog post with several "About" signals is accepted even if the ML confidence is borderline.

## Related

- [ML_TRAINING.md](ML_TRAINING.md)
- [CONFIG.md](CONFIG.md)
