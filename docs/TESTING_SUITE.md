# testing_suite/

## Purpose

The `tests/` directory contains unit and integration tests to ensure the reliability of the quality filtering logic.

## Test Files

- **test_landing_page_filter.py**: Verifies that corporate and commercial pages are correctly identified by the `landing_page_filter` module.
- **test_quality_filter.py**: Tests the unified scoring system (now in `config.py`) against various HTML samples.

## Running Tests

Tests are typically run using `pytest`:

```bash
pytest tests/
```

## Related Documentation

- [CONFIG.md](CONFIG.md)
