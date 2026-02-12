# Crawling System (`crawler.py`)

## Summary

The core crawling engine that traverses the web, extracts content, and saves high-quality pages to the search index. The system includes built-in protections against low-quality domains and infinite crawling loops.

## Description

`crawler.py` implements the `SimpleCrawler` class, which handles the recursive traversal of URLs. It uses `requests` for static content and can optionally use Playwright for dynamic JavaScript-rendered pages. Every page found is evaluated for quality using `config.evaluate_page_quality` before being saved to the SQLite database (`index.db`).

### Key Features

- **Traversal**: Breadth-first or depth-first search up to a specified `max_depth`.
- **Normalization**: URLs are normalized (stripping params/fragments) to avoid duplicate crawling.
- **Persistence**: Pages are saved to a SQL table with full-text search (FTS5) triggers.
- **Dynamic Content**: Integration with Playwright via the `--dynamic` flag.
- **Safety**: Uses `QualityLogger` to track successes and rejections, and enforces "polite" crawling with delays.
- **Auto-Stopping**:
  - **Domain Blacklisting**: Automatically blacklists a domain if it produces too many rejected pages (`domain_rejection_threshold`).
  - **Global Rejection Stop**: Stops the entire crawl if a contiguous sequence of pages are rejected across the board (`consecutive_rejection_threshold`), preventing the crawler from getting stuck in a "bad neighborhood" of the web.

## Public API / Interfaces

### `SimpleCrawler` Class

#### Methods:

- **`__init__(base_url, max_depth=2, db_file="index.db", use_dynamic=False)`**: Initialize the crawler.
- **`crawl(url, depth=0)`**: Recursively crawl the given URL.
- **`is_valid_url(url)`**: Checks if a URL should be crawled based on domain, extension, and visited status. Includes checks against the blacklist.
- **`save_page(url, title, content, html, quality_score, quality_tier)`**: Persists page data to the DB and updates the FTS index.
- **`blacklist_domain(domain)`**: Adds a domain to the blacklist in the database.

### CLI Commands:

```bash
uv run python provoke/crawler.py <url_or_file> [max_depth] [--dynamic]
```

- **`<url_or_file>`**: A single URL or a path to a text file containing seed URLs.
- **`[max_depth]`**: Integer depth limit (default 1).
- **`--dynamic`**: Enable Playwright for JS execution (crawls SPA sites).

## Dependencies

- `requests`: HTTP client.
- `BeautifulSoup`: HTML parsing.
- `sqlite3`: Data storage.
- `playwright`: (Optional) Dynamic rendering.
- `provoke.config`: Central configuration and quality evaluation logic.
- `provoke.utils.logger`: Stats tracking.

## Examples

Crawl a specific blog:

```bash
uv run python provoke/crawler.py https://example.com/blog 2
```

Crawl from a list of seeds with dynamic rendering:

```bash
uv run python provoke/crawler.py seeds.txt 1 --dynamic
```

## Related

- [CONFIG.md](CONFIG.md)
- [SEARCH_ENGINE.md](SEARCH_ENGINE.md)
