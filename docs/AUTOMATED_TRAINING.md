# Automated Training (`scripts/train_until_ready.sh`)

## Summary

A secondary automation script for iterative training of the content classifier.

## Description

`scripts/train_until_ready.sh` is designed to reach a high precision model by repeatedly running the training process. It parses the output of the training script to extract the precision score and continues until it hits the `TARGET_PRECISION` (default 0.998).

## Usage

```bash
cd scripts
./train_until_ready.sh
```

Or from the project root:

```bash
bash scripts/train_until_ready.sh
```

## Dependencies

- `bash`
- `uv`: For running the python training script.
- `bc`: For floating-point comparisons in the shell.
- `scripts/train_classifier.py` (via `uv run`)

## Notes

- Ensure `data/to_label.csv` has enough diverse data before running, otherwise, the model may overfit to reach the target precision.
