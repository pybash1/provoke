# Quality Logging (`quality_logger.py`)

## Summary

A logging utility for tracking crawler performance, specifically focusing on page acceptances, rejections, and quality tiers.

## Description

`QualityLogger` is used by the crawler to maintain transparency about its decisions. It writes detailed logs to a text file for debugging and captures structured statistics in a CSV file for analytical purposes (like training machine learning models).

### Outputs:

1.  **`rejected_urls.log`**: A human-readable text file with timestamps and specific rejection reasons for every URL that failed the quality check.
2.  **`quality_stats.csv`**: A structured dataset including URLs, rejection reasons, and various heuristic scores (unified score, text ratio, word count, etc.).

## Public API / Interfaces

### `QualityLogger` Class

#### Methods:

- `__init__(log_file="rejected_urls.log", csv_file="quality_stats.csv")`: Initializes logging paths and CSV headers.
- `log_rejection(url, reasons, scores)`: Records a failure to both the log and CSV.
- `log_acceptance(url, tier)`: Increments the success counter for the current session.
- `print_summary()`: Outputs a session summary to the console (Total accepted/rejected, most common rejection reasons).

## Dependencies

- `logging`: Python standard library for text logs.
- `csv`: For managing the stats file.
- `config`: For file paths.

## Notes/Limitations

- The `quality_stats.csv` file is a critical source for building the `to_label.csv` dataset via `ml_data_prep.py`.

## Related

- [CRAWLING_SYSTEM.md](CRAWLING_SYSTEM.md)
- [DATA_MANAGEMENT.md](DATA_MANAGEMENT.md)
