#!/usr/bin/env python3
"""
Backward-compatible shim for provoke.web.app

The Flask web application has moved to the provoke package.
This file is maintained for backward compatibility.

Usage:
    uv run python app.py
"""

from provoke.web.app import app
from provoke.config import config

if __name__ == "__main__":
    app.run(debug=config.SERVER_DEBUG, host=config.SERVER_HOST, port=config.SERVER_PORT)
