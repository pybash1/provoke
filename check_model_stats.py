#!/usr/bin/env python3
"""
Model statistics checker for evaluating ML classifier performance on indexed pages.

This is a backward-compatible wrapper that delegates to provoke.utils.model_stats.
"""

from provoke.utils.model_stats import main

if __name__ == "__main__":
    main()
