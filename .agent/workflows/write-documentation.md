---
description: AI agent scans code, extracts functions, parameters, and usage examples. It auto‑generates markdown docs, checks for consistency, and updates version notes. Team reviews in pull request, ensuring clarity before merge.
---

# How the Antigravity AI Agent Handles Code‑Base Documentation

**You** are the AI agent tasked with producing or updating documentation for a software project. Follow these steps to ensure a thorough, consistent result.

## 1. Gather the Project Context

| Step    | Action                    | Details                                                                                                                                                 |
| ------- | ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **1.1** | **Locate the repo**       | Accept the root path of the project as input (`/path/to/repo`).                                                                                         |
| **1.2** | **Scan for docs**         | Search recursively for `docs/` directories. Record any `.md` files found.                                                                               |
| **1.3** | **Identify the language** | Detect the primary language(s) (Python, JavaScript, Go, etc.) by file extensions and language hints in `package.json`, `requirements.txt`, or `go.mod`. |
| **1.4** | **Set output format**     | All documentation will be in Markdown (`.md`) with UTF‑8 encoding.                                                                                      |

## 2. Parse the Codebase

| Step    | Action                  | Tools                                                                               |
| ------- | ----------------------- | ----------------------------------------------------------------------------------- |
| **2.1** | **Parse files**         | For each source file, build an abstract syntax tree (AST).                          |
| **2.2** | **Extract API surface** | Capture functions, classes, methods, public constants, enums, and their signatures. |
| **2.3** | **Collect docstrings**  | Pull existing inline documentation (docstrings, comments).                          |
| **2.4** | **Map to modules**      | Organize extracted elements by module/package hierarchy.                            |

## 3. Cross‑Reference Existing Docs

| Step    | Action                      |
| ------- | --------------------------- | --------------------------------------------------------------- |
| **3.1** | **Match names**             | Compare extracted elements to headings in existing `.md` files. |
| **3.2** | **Identify gaps**           | Note functions or modules lacking documentation.                |
| **3.3** | **Detect obsolete entries** | Flag docs that reference removed or renamed elements.           |

## 4. Generate or Update Documentation

### 4.1 Decide Action

| Condition                    | Action                                            |
| ---------------------------- | ------------------------------------------------- |
| No existing `docs/`          | **Create** new `docs/` folder and initial README. |
| Existing docs but incomplete | **Update** – add missing sections.                |
| Existing docs but outdated   | **Rewrite** the affected sections.                |

### 4.2 Build Content

1. **Create a README**  
   _Project Overview_, installation, usage, contribution guidelines.
2. **Generate Module Pages**
   - For each package/module, create a Markdown file (`module_name.md`).
   - Include:
     - Module description (if available).
     - List of public classes/functions with signatures.
     - Inline examples or usage snippets.
     - Links to related modules.
3. **Add Cross‑Links**
   - Use relative Markdown links (`[ClassName](../module_name.md)`).
4. **Format**
   - Use tables for signatures.
   - Keep heading levels consistent (`#`, `##`, `###`).

### 4.3 Update Existing Docs

- Replace outdated sections entirely.
- Append new sections at the end of the file, preserving author comments (`<!-- Auto‑generated -->`).
- Maintain any custom sections not related to code APIs.

## 5. Verify and Commit

| Step    | Action              |
| ------- | ------------------- | ---------------------------------------------- |
| **5.1** | **Syntax check**    | Run a Markdown linter (`markdownlint`).        |
| **5.2** | **Link validation** | Ensure all internal links resolve.             |
| **5.3** | **Diff generation** | Show changes against the previous commit.      |
| **5.4** | **Commit**          | `git add docs/ && git commit -m "Update docs"` |

## 6. Notify the Team

- Push to a new branch (`docs-update`).
- Open a pull request with a concise description: _“Automated documentation generation/updating.”_
- Tag relevant maintainers for review.

---

Follow this workflow every time the codebase changes to keep the documentation accurate, complete, and easy to navigate.
