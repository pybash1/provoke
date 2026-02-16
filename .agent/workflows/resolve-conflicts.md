---
description: Resolve merge conflicts in the current branch with the target branch (usually main)
---

# Resolve Merge Conflicts Workflow

Follow these steps to safely identify and resolve merge conflicts when your branch is out of sync with the target branch.

1.  **Identify Target Branch**:
    Ensure you have the latest changes from the remote. Usually the target is `main`.
    // turbo

    ```bash
    git fetch origin main
    ```

2.  **Attempt Merge**:
    Try to merge the target branch into your current feature branch.

    ```bash
    git merge origin/main
    ```

3.  **Check for Conflict Status**:
    If the merge fails with CONFLICT messages, verify which files are affected.
    // turbo

    ```bash
    git status
    ```

4.  **Inspect Conflict Markers**:
    For each file in the "Unmerged paths" section, locate the conflict markers.
    Use tools like `grep` to find them if the file is large:

    ```bash
    grep -nE "<<<<<<<|=======|>>>>>>>" <file_path>
    ```

5.  **Resolve Conflicts**:
    Open the conflicting files and manually resolve the differences:
    - `<<<<<<< HEAD` : Current changes in your branch.
    - `=======` : Boundary between your changes and incoming changes.
    - `>>>>>>> origin/main` : Incoming changes from the target branch.

    Choose the correct logic, combine them if necessary, and **delete all markers**.

6.  **Verify Build/Tests**:
    Before committing, ensure the code is still functional.

    ```bash
    # Example for this project:
    uv run python -m provoke.crawler --help
    ```

7.  **Stage and Commit**:
    Mark the conflicts as resolved by staging the files. Use `--no-gpg-sign` to avoid interactive prompts in headless environments.

    ```bash
    git add <resolved-file-1> <resolved-file-2>
    git commit --no-gpg-sign -m "merge: resolve conflicts with main"
    ```

8.  **Push Updates**:
    Push the resolved merge to the remote to update the Pull Request.
    ```bash
    git push origin <your-current-branch>
    ```
