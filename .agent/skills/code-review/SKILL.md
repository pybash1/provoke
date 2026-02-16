---
name: code-review
description: Review GitHub pull requests, submit feedback, approve/request changes, and manage upstream updates using git and gh. Always uses --no-gpt-sign for commits.
---

# Code Review Skill

This skill provides a structured workflow for reviewing GitHub Pull Requests using the `gh` CLI and `git`, with a strict requirement for unsigned commits.

## Triggers

- "Review PR #123"
- "What are the open pull requests?"
- "Approve the current PR"
- "Request changes on PR #5"
- "Push my review changes to upstream"

## Workflow

### 1. List and Select PRs

Identify which PRs need attention.

```bash
gh pr list
```

### 2. Local Checkout and Inspection

Always inspect code locally to run tests or verify behavior.

```bash
gh pr checkout <PR_NUMBER>
```

To view the changes:

```bash
gh pr diff
```

### 3. Submitting the Review

Provide feedback through formal reviews.

**Approve:**

```bash
gh pr review <PR_NUMBER> --approve --body "LGTM"
```

**Request Changes:**

```bash
gh pr review <PR_NUMBER> --request-changes --body "Detailed explanation of changes needed..."
```

### 4. Making Changes & Committing

If you need to fix something in the PR before approving/merging, you MUST use the `--no-gpt-sign` flag for every commit.

A helper script is available:

```bash
# Usage: .agent/skills/code-review/scripts/commit-no-sign.sh "message"
./.agent/skills/code-review/scripts/commit-no-sign.sh "Apply review fixes"
```

Manual command:

```bash
git commit -m "Your message" --no-gpt-sign
```

### 5. Pushing and Merging

Once the review is complete, push to upstream.

**Push branch:**

```bash
git push upstream <branch-name>
```

**Merge via PR CLI (if authorized):**

```bash
gh pr merge <PR_NUMBER> --merge --delete-branch
```

## Policy Notes

- **SIGNING**: Do NOT use GPG signing. Always use `--no-gpt-sign` as requested by the user.
- **CLI TOOLS**: Prefer `gh` over the web UI for speed and consistency.
