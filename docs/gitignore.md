# .gitignore

## Summary

Specifies which files and directories should be ignored by Git.

## Key Exclusions

- **Environment**: `.venv/`, `venv/`, `__pycache__/`, `.DS_Store`.
- **Large Data**: `index.db` (The SQLite database, though some versions may include it, it's generally large).
- **Logs**: `rejected_urls.log`.
- **Trained Models**: High-frequency training output (models are often stored in `models/`).
- **Temporary Files**: `crawl_urls.txt`, `quality_stats.csv`.

## Related

- Project developers should ensure they have their own local `index.db` or obtain a seed version.
