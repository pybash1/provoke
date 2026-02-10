# tests/test_quality_filter.py

## Summary

Integration tests for the `quality_filter` module and its unified scoring system.

## Description

This test suite uses realistic samples of high-quality blog posts (inspired by real sites like danluu.com) to verify that the `evaluate_page_quality` function behaves as expected. It checks that positive signals (identity, length, date indicators) outweigh any minor penalties.

## Test Cases

- `test_personal_blog`: Validates that a genuine personal article with metadata is accepted.
- `test_low_quality_content`: (Assumed) Verifies that pages with high marketing density or low text-to-HTML ratios are rejected.

## How to Run

```bash
pytest tests/test_quality_filter.py
```

## Related

- [quality_filter-py.md](../docs/quality_filter-py.md)
