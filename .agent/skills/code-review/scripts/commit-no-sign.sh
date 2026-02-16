#!/bin/zsh

# commit-no-sign.sh
# Wrapper to ensure every commit is made with the --no-gpt-sign flag as per project policy.

if [ "$#" -lt 1 ]; then
    echo "Usage: $0 \"commit message\" [other git commit args...]"
    exit 1
fi

MESSAGE=$1
shift

git commit -m "$MESSAGE" --no-gpt-sign "$@"
