# tests/test_landing_page_filter.py

## Summary

Unit tests for the `landing_page_filter` module.

## Description

This test suite verifies the "hard rejection" logic used to filter out commercial and low-quality content. It uses simulated HTML fragments for well-known page types (E-commerce, Spam services) to ensure they are detected correctly.

## Test Cases

- `test_ecommerce_detection`: Checks for cart buttons, payment icons, and Schema.org `Product` metadata.
- `test_spam_service_detection`: Verifies rejection of URLs and text related to SEO spam, fake social media signals, and AI humanizers.
- `test_homepage_logic`: Ensures that generic root-domain pages without substantial content are marked as non-articles.

## How to Run

```bash
pytest tests/test_landing_page_filter.py
```
