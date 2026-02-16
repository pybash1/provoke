---
name: conflict-resolution
description: Advanced tools and scripts for identifying and resolving complex merge conflicts across multiple files.
---

# Conflict Resolution Skill

This skill provides automated ways to identify and manage merge conflicts that arise during PR lifecycle or branch syncing.

## Triggers

- "Fix merge conflicts with main"
- "Where are the conflicts?"
- "Help me resolve this merge"
- "Abort the current merge"

## Tools & Scripts

### 1. Identify Conflicts

Quickly find every file and line number containing a conflict marker.

```bash
# Usage: .agent/skills/conflict-resolution/scripts/find-markers.sh
./.agent/skills/conflict-resolution/scripts/find-markers.sh
```

### 2. Check Merge Status

Confirm if the repository is currently in a "merging" state.

```bash
git status | grep "You have unmerged paths"
```

## Step-by-Step Guide

### 1. Sync & Merge

Fetch the latest changes from the target and attempt a merge.

```bash
git fetch origin main
git merge origin/main
```

### 2. Automated Search

Use the `find-markers.sh` script to list all work items.

### 3. File-by-File Resolution

For each file:

1. Open the file using `view_file` or `view_file_outline`.
2. Locate markers using `grep` or by scrolling to the line numbers found in step 2.
3. Use `multi_replace_file_content` to remove the markers and settle on the final code.

### 4. Verification

Ensure the code is valid Python/JS and that the logic is sound.

### 5. Finalizing

```bash
git add .
git commit --no-gpg-sign -m "merge: resolve conflicts with main"
git push origin <your-branch>
```

## Tips

- **Abort**: If the merge is too messy and you want to start over: `git merge --abort`.
- **Strategy**: If you know you want to favor one side globally (rarely recommended):
  - Favor your branch: `git merge origin/main -X ours`
  - Favor their branch: `git merge origin/main -X theirs`
