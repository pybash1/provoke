#!/usr/bin/env python3
"""
Training workflow for content quality classifier.

This is a backward-compatible wrapper that delegates to provoke.ml.trainer.

Usage:
    uv run python train_classifier.py --export     # Export pages for labeling
    uv run python train_classifier.py --train      # Train model after labeling
    uv run python train_classifier.py --evaluate   # Evaluate model
"""

from provoke.ml.trainer import main

if __name__ == "__main__":
    main()
