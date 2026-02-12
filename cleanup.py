#!/usr/bin/env python3
"""
Cleanup utility for re-evaluating indexed pages against current quality filters.

This is a backward-compatible wrapper that delegates to provoke.utils.cleanup.
"""

from provoke.utils.cleanup import main

if __name__ == "__main__":
    main()
