# quality_config.py

## Summary

Central configuration file for crawling rules, quality thresholds, and filtering patterns.

## Description

`quality_config.py` acts as the "brain" for the project's tuning. It contains all the magic numbers, keywords, and regular expressions used by `crawler.py` and `quality_filter.py` to make decisions.

## Configurable Items

### `THRESHOLDS`

Dict containing core numeric limits:

- `min_words`: Minimum word count for a valid article.
- `max_words`: Maximum word count (to avoid huge files).
- `min_text_ratio`: Minimum ratio of text-to-HTML.
- `min_readability`: Flesch Reading Ease threshold.
- `unified_score_threshold`: The bar a page must pass to be indexed.
- `consecutive_rejection_threshold`: Global stop trigger for the crawler.

### `ML_CONFIG`

Settings for the machine learning classifier:

- `enabled`: Boolean to toggle ML.
- `model_path`: Path to the `.bin` model file.
- `use_for_uncertain_only`: Only run ML if the heuristic score is below a certain bar.

### Filter Patterns

- `CTA_PHRASES`: Phrases typical of marketing sites (e.g., "Get Started", "Free Trial").
- `MARKETING_TOOLS`: Fingerprints for tools like HubSpot, Marketo, Intercom.
- `AD_NETWORKS`: Tracking scripts (Google Ads, Facebook Pixel).
- `EXCLUDED_URL_PATTERNS`: Regex for tags, categories, and archive pages.
- `EXCLUDED_TITLE_PATTERNS`: Page titles that indicate non-content (e.g., "Privacy Policy", "Home - ").
- `BINARY_EXTENSIONS`: File types to ignore (zip, exe, etc.).

## Usage

Import these constants into other modules:

```python
from quality_config import THRESHOLDS, ML_CONFIG
```

## Notes

- To prioritize "Personal" blogs over "Corporate" ones, decrease `unified_score_threshold` and increase the penalties for `CTA_PHRASES`.
- Update `EXCLUDED_TITLE_PATTERNS` often to keep the index clean of generic utility pages.

## Related

- [quality_filter-py.md](quality_filter-py.md)
- [crawler-py.md](crawler-py.md)
