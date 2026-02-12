# Utility Scripts

This project includes several utility scripts for maintenance, testing, and data engineering.

## Automated Training

### [AUTOMATED_TRAINING.md](AUTOMATED_TRAINING.md)

Documentation for `train_until_ready.sh`, a shell script that loops training until a precision threshold is met.

## Data Maintenance

### [CLEANUP.md](CLEANUP.md)

Documentation for `cleanup.py`, which purges invalid or low-quality pages from the database based on current `config` rules.

## Diagnostics

### `check_model_stats.py`

Runs the current model against the existing indexed database to find "uncertain" pages or potential misclassifications. It helps in auditing the model's performance on live data.

## Configuration & Setup

- `pyproject.toml` & `uv.lock`: Project metadata and dependency management (using `uv`).
- `.gitignore`: Version control exclusions.
