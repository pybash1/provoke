#!/usr/bin/env python3
import sys
import os

# Add project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(PROJECT_ROOT)

from provoke.crawler import main

if __name__ == "__main__":
    main()
