# crawler.py

## Summary

The core crawling engine that traverses the web, extracts content, and saves high-quality pages to the search index.

## Description

`crawler.py` implements the `SimpleCrawler` class, which handles the recursive traversal of URLs. It uses `requests` for static content and can optionally use Playwright for dynamic JavaScript-rendered pages. Every page found is evaluated for quality using `quality_filter.py` before being saved to the SQLite database (`index.db`).

### Architecture

- **Traversal**: Breadth-first or depth-first search up to a specified `max_depth`.
- **Normalization**: URLs are normalized to avoid duplicate crawling.
- **Persistence**: Pages are saved to a SQL table with full-text search triggers.
- **Dynamic Content**: Integration with Playwright via the `--dynamic` flag.
- **Safety & Metrics**: Uses `QualityLogger` to track successes and rejections, and enforces "polite" crawling with delays.
- **Auto-Blacklisting**: Automatically blacklists domains if a certain number of rejections occur consecutively.

## Public API / Interfaces

### `SimpleCrawler` Class

#### Methods:

- `__init__(base_url, max_depth=2, db_file="index.db", use_dynamic=False)`: Initialize the crawler.
- `crawl(url, depth=0)`: Recursively crawl the given URL.
- `is_valid_url(url)`: Checks if a URL should be crawled based on domain, extension, and visited status.
- `save_page(url, title, content, html, quality_score, quality_tier)`: Persists page data to the DB.
- `blacklist_domain(domain)`: Adds a domain to the blacklist.

### CLI Commands:

```bash
python crawler.py <url_or_file> [max_depth] [--dynamic]
```

- `<url_or_file>`: A single URL or a path to a text file containing seed URLs.
- `[max_depth]`: Integer depth limit (default 1).
- `--dynamic`: Enable Playwright for JS execution.

## Dependencies

- `requests`: HTTP client.
- `BeautifulSoup`: HTML parsing.
- `sqlite3`: Data storage.
- `playwright`: (Optional) Dynamic rendering.
- `quality_filter`: Content assessment.
- `quality_logger`: Stats tracking.
- `quality_config`: Global rules and thresholds.

## Examples

Crawl a specific blog:

```bash
python crawler.py https://example.com/blog 2
```

Crawl from a list of seeds with dynamic rendering:

```bash
python crawler.py seeds.txt 1 --dynamic
```

## Related

- [quality_filter-py.md](quality_filter-py.md)
- [quality_config-py.md](quality_config-py.md)
- [indexer-py.md](indexer-py.md)
