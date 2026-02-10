# Repository Documentation

Welcome to the documentation for the **inked** repository. This project appears to be a web crawler and search engine with advanced quality filtering and machine learning-based content classification.

## Documentation Structure

The documentation is organized to mirror the repository's file structure. Each file and major directory has its own dedicated documentation file:

- **Core Application**: [app.py](app-py.md) (The Flask web interface and API).
- **Crawling System**: [crawler.py](crawler-py.md) (The main crawler logic), [quality_filter.py](quality_filter-py.md) (Page quality assessment).
- **Quality Configuration**: [quality_config.py](quality_config-py.md) (Thresholds and rules).
- **Machine Learning**: [ml_classifier.py](ml_classifier-py.md), [ml_train.py](ml_train-py.md), [train_classifier.py](train_classifier-py.md).
- **Search Engine**: [indexer.py](indexer-py.md) (SQLite FTS search engine).
- **Data Management**: [ml_data_prep.py](ml_data_prep-py.md), [data/ Index](data-index.md).
- **UI & Templates**: [templates/ Index](templates-index.md).
- **Testing**: [tests/ Index](tests-index.md).

## File Mapping

| Repository File       | Documentation File                               |
| --------------------- | ------------------------------------------------ |
| `app.py`              | [app-py.md](app-py.md)                           |
| `crawler.py`          | [crawler-py.md](crawler-py.md)                   |
| `indexer.py`          | [indexer-py.md](indexer-py.md)                   |
| `ml_classifier.py`    | [ml_classifier-py.md](ml_classifier-py.md)       |
| `quality_filter.py`   | [quality_filter-py.md](quality_filter-py.md)     |
| `quality_config.py`   | [quality_config-py.md](quality_config-py.md)     |
| `ml_train.py`         | [ml_train-py.md](ml_train-py.md)                 |
| `ml_data_prep.py`     | [ml_data_prep-py.md](ml_data_prep-py.md)         |
| `train_classifier.py` | [train_classifier-py.md](train_classifier-py.md) |
| `reducing-errors.md`  | [reducing-errors.md](reducing-errors.md)         |

## Binary Assets

The following binary files are present in the repository:

- `index.db`: The SQLite database containing indexed pages and domain lists.
- `models/*.bin`: Trained FastText classification models.

## How to Regenerate Documentation

Currently, the documentation is generated manually or via AI assistance by scanning the codebase and extracting structural and logic information. To update:

1. Re-analyze the source files for API changes.
2. Update the corresponding `.md` file in `docs/`.
3. Update the `docs/README.md` if new files are added.

## Navigation

- [Root Documentation](README.md)
- [Reducing Errors Guide](reducing-errors.md)
- [System Architecture](crawler-py.md#architecture)
