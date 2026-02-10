# Utility Scripts

This project includes several utility scripts for maintenance, testing, and data engineering.

## Automated Training

### [train_until_ready.sh](train_until_ready-sh.md)

A shell script that loops `train_classifier.py --train` until a target precision threshold is met.

## Data Maintenance

### [cleanup.py](cleanup-py.md)

Removes pages from the search index if they belong to newly blacklisted domains or fail current quality checks.

### [mark_dotink_good.py](mark_dotink_good.py)

A helper to bulk-label URLs ending in `.ink` (or other specific patterns) as 'good' in the labeling CSV.

## Diagnostics

### [check_csv_stats.py](check_csv_stats.md)

Analyzes `to_label.csv` to find corrupted rows, duplicate URLs, or distribution imbalances.

### [check_model_stats.py](check_model_stats.md)

Runs the current model against the existing indexed database to find "uncertain" pages or potential misclassifications.

### [test_csv.py](test_csv.md)

A basic script to verify the integrity of the data labeling CSV.

## Experimentation

### [hyperparameter_tuning.py](hyperparameter_tuning.md)

Loops through different FastText configurations (learning rate, N-grams, etc.) to find the optimal settings for training.

### [url_fetching_temp.py](url_fetching_temp.md)

A temporary playground script for testing URL fetching and BeautifulSoup extraction logic.

### [add_landing_pages.py](add_landing_pages.md)

Bulk adds known commercial/landing page URLs to the labeling CSV to improve the 'bad' training set.

## Configuration & Setup

- [requirements.txt](requirements-txt.md): Python dependency list.
- [.gitignore](gitignore.md): Version control exclusions.
