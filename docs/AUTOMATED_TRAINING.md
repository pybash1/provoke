# Automated Training (`train_until_ready.sh`)

## Summary

A bash script for automated iterative training of the content classifier.

## Description

`train_until_ready.sh` is designed to reach a high precision model by repeatedly running the training process. It parses the output of `train_classifier.py --train` to extract the precision score and continues until it hits the `TARGET_PRECISION` (default 0.998).

## Usage

```bash
./train_until_ready.sh
```

## Dependencies

- `bash`
- `python3`
- `grep`, `awk` (for parsing precision from output)
- `train_classifier.py`

## Notes

- Ensure `data/to_label.csv` has enough diverse data before running, otherwise, the model may overfit to reach the target precision.
