#!/bin/zsh

# push-upstream.sh
# Safely push the current branch to the 'upstream' remote.

CURRENT_BRANCH=$(git branch --show-current)

if [ -z "$CURRENT_BRANCH" ]; then
    echo "Error: Not on a branch."
    exit 1
fi

echo "Pushing $CURRENT_BRANCH to upstream..."
git push upstream "$CURRENT_BRANCH"
