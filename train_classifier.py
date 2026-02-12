#!/usr/bin/env python3
"""
Backward-compatible shim for provoke.ml.trainer

The training workflow has moved to the provoke package.
This file is maintained for backward compatibility.

Usage:
    uv run python train_classifier.py --export
    uv run python train_classifier.py --train
    uv run python train_classifier.py --evaluate
"""

from provoke.ml.trainer import main

if __name__ == "__main__":
    main()
