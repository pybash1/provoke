---
description: Commit and push all changes in the codebase upstream
---

Follow these steps to safely commit and push changes, handling authentication nuances in headless environments.

1.  **Check Status**:
    Run `git status` to see pending changes.

2.  **Create/Checkout Branch**:
    Ensure you are on a feature branch, not `main` directly.

    ```bash
    git checkout -b <feature-branch-name>
    ```

3.  **Stage Changes**:
    Stage all changes or specific files.

    ```bash
    git add .
    ```

4.  **Commit Changes (Headless Safe)**:
    Since this runs in a headless environment, GPG signing might fail if it requires an interactive prompt (Touch ID/Passphrase).
    Use the `--no-gpg-sign` flag to bypass this issue if necessary.
    Follow [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `docs:`, etc.

    ```bash
    git commit --no-gpg-sign -m "<type>: <description>"
    ```

5.  **Push Changes**:
    Push the branch to origin, setting the upstream.

    ```bash
    git push -u origin <feature-branch-name>
    ```

6.  **Create Pull Request**:
    Use the GitHub CLI to create a PR immediately.
    ```bash
    gh pr create --title "<PR Title>" --body "<Detailed description of changes>"
    ```
