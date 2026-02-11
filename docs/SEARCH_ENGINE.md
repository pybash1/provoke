# Search Engine (`indexer.py`)

## Summary

The search engine module that provides full-text and fuzzy search capabilities over the indexed pages.

## Description

`indexer.py` implements the `SearchEngine` class, which uses SQLite's FTS5 (Full-Text Search) extension and a custom trigram tokenizer to find relevant pages. It also implements a fallback fuzzy matching system using `difflib` for when literal matches are insufficient.

### Search Logic:

1.  **Trigram FTS Search**: First, it performs a broad OR search using the `pages_trigram` virtual table. This is extremely fast and handles partial word matches.
2.  **Ranking**: Results are ranked using a combination of SQLite's `rank` (based on BM25) and a custom similarity score based on the query vs. the page title.
3.  **Fuzzy Fallback**: If the FTS search yields no results or very low scores, the engine performs a full-table scan using a custom `similarity` SQL function (registered via `difflib.SequenceMatcher`).
4.  **Snippets**: Uses SQLite's `snippet()` function to generate highlighted text fragments for the search results page.

## Public API / Interfaces

### `SearchEngine` Class

#### Methods:

- `__init__(db_file=None)`: Connect to the database specified in `config.DATABASE_PATH`.
- `search(query)`: Executes the two-stage search process.
  - **Returns**: A list of dictionaries containing `title`, `url`, `snippet`, and `score`.

### CLI Command:

```bash
python indexer.py "<query>"
```

Example:

```bash
python indexer.py "python web scraping"
```

## Dependencies

- `sqlite3`: Core database and FTS engine.
- `difflib`: For fuzzy string matching.
- `config`: For database path configuration.

## Notes/Limitations

- **Performance**: The fuzzy fallback performs a full scan of the `pages` table. This works well for a few thousand pages but may need optimization (e.g., more robust FTS) for much larger datasets.
- **Triggers**: The search relies on a virtual table `pages_trigram` which is kept in sync by SQL triggers defined in `crawler.py`.

## Suggested Tests

- Search for a word that appears only in a page's content (FTS check).
- Search for a misspelled version of a page title (Fuzzy fallback check).

## Related

- [CRAWLING_SYSTEM.md](CRAWLING_SYSTEM.md)
- [WEB_INTERFACE.md](WEB_INTERFACE.md)
