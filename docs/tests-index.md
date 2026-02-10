# tests/

## Purpose

The `tests/` directory contains unit and integration tests to ensure the reliability of the quality filtering logic.

## Test Files

- **[test_landing_page_filter.py](tests-test_landing_page_filter-py.md)**: Verifies that corporate and commercial pages are correctly identified.
- **[test_quality_filter.py](tests-test_quality_filter-py.md)**: Tests the unified scoring system against various HTML samples.

## Running Tests

Tests are typically run using `pytest`:

```bash
pytest tests/
```

## Related Documentation

- [quality_filter.py](../docs/quality_filter-py.md)
- [landing_page_filter.py](../docs/landing_page_filter-py.md)
