# quality_filter.py

## Summary

The decision engine for determining the quality and suitability of a web page for the search index.

## Description

`quality_filter.py` provides a suite of heuristic and machine learning tools to assess whether a page is high-quality "blog-like" content or low-quality "corporate/marketing" noise. It calculates multiple sub-scores (readability, text-to-HTML ratio, corporate signals, etc.) and combines them into a **Unified Quality Score**.

### Key Phases:

1.  **Phase 1: Hard Rejections**: Immediate rejection based on landing page indicators (e-commerce, spam services, corporate frontpages).
2.  **Phase 2: Heuristic Analysis**: Calculates scores for content density, length, readability, and identity signals.
3.  **Phase 3: ML Refinement**: (Optional) Uses a FastText classifier to confirm or rescue pages based on learned patterns.

## Public API / Interfaces

### `evaluate_page_quality(url, html, text, whitelist=None)`

The primary entry point.

- **Arguments**:
  - `url` (str): The page URL.
  - `html` (str): Full HTML source.
  - `text` (str): Cleaned visible text.
  - `whitelist` (list/set): Optional list of domains to bypass certain filters.
- **Returns**: A dictionary containing `is_acceptable` (bool), `scores` (dict), `rejection_reasons` (list), and `quality_tier` (str: high, medium, low).

### Individual Heuristics:

- `calculate_text_ratio(html)`: Ratio of visible text to structural HTML.
- `check_content_length(text)`: Word count check.
- `calculate_corporate_score(url, html, text)`: Penalizes typical marketing language and CTAs.
- `check_personal_blog_signals(url, html)`: Credits RSS feeds, author tags, and "About" pages.
- `calculate_readability(text)`: Flesch Reading Ease score.
- `calculate_unified_score(scores)`: Final aggregation logic.

## Dependencies

- `textstat`: For readability calculations.
- `BeautifulSoup` (bs4): For HTML analysis.
- `quality_config`: For threshold values and patterns.
- `landing_page_filter`: For hard-rejection logic.
- `ml_classifier`: For machine learning predictions.

## Notes/Limitations

- The `unified_score` is a weighted average of various heuristics. It can be tuned in `quality_config.py`.
- Whitelisted domains bypass most filters but are still checked for blacklisted title patterns.

## Related

- [quality_config-py.md](quality_config-py.md)
- [landing_page_filter-py.md](landing_page_filter-py.md)
- [ml_classifier-py.md](ml_classifier-py.md)
