#!/bin/bash
# find-markers.sh - search for git conflict markers in the current directory
# Excludes .git and other common binary/dependency directories

grep -rE "<<<<<<<|=======|>>>>>>>" . \
    --exclude-dir=.git \
    --exclude-dir=.venv \
    --exclude-dir=node_modules \
    --exclude-dir=__pycache__ \
    --exclude=*.pyc \
    --color=always
