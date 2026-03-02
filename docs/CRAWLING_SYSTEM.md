# Crawling System (`provoke/crawler.py`)

## Summary

The core crawling engine that traverses the web, extracts content, and saves high-quality pages to the search index. The system includes built-in protections against low-quality domains and infinite crawling loops.

## Description

`crawler.py` implements the `SimpleCrawler` class, which handles the recursive traversal of URLs. It uses `requests` for static content and can optionally use Playwright for dynamic JavaScript-rendered pages. Every page found is evaluated for quality using `config.evaluate_page_quality` before being saved to the SQLite database (`index.db`).

### Key Features

- **Asynchronous Crawling**: Utilizes `asyncio`, `aiohttp`, and asynchronous Playwright for high-concurrency crawling.
- **Smart Tree Skipping**: Automatically abandons unproductive URL branches based on real-time rejection ratios.
- **Distributed Bloom Filter**: Uses a persistent Redis-backed Bloom Filter to track visited URLs across sessions and multiple crawler instances.
- **Normalization**: URLs are normalized (stripping params/fragments) to avoid duplicate crawling.
- **Persistence**: Pages are saved to a SQL table with full-text search (FTS5) triggers and content deduplication via SHA256 hashing.
- **Dynamic Content**: Auto-upgrades to Playwright rendering when SPA indicators or script-heavy patterns are detected.
- **Safety**: Complies with `robots.txt` and enforces domain/consecutive rejection limits.

## Public API / Interfaces

### `AsyncCrawler` Class

#### Methods:

- **`__init__(base_url, max_depth=None, db_file=None, use_dynamic=False)`**: Initialize the async crawler and connect to Redis for the Bloom Filter.
- **`run(seed_urls)`**: Entry point for starting the asynchronous crawl loop.
- **`process_url(url, depth)`**: Asynchronously fetches, evaluates, and processes a single URL.
- **`is_valid_url(url)`**: Checks if a URL should be crawled based on the Bloom Filter, domain blacklist, and `robots.txt`.
- **`fetch_page(url)`**: Strategy-based fetch that uses `aiohttp` for static or Playwright for dynamic content.
- **`save_page(...)`**: Persists page data and updates RSS feed discovery.

### CLI Commands:

```bash
uv run python scripts/crawler.py <url_or_file> [max_depth] [--dynamic]
# or
uv run provoke-crawler <url_or_file> [max_depth] [--dynamic]
```

- **`<url_or_file>`**: A single URL or a path to a text file containing seed URLs.
- **`[max_depth]`**: Integer depth limit (default 1).
- **`--dynamic`**: Enable Playwright for JS execution (crawls SPA sites).

## Dependencies

- `aiohttp`: Async HTTP client.
- `BeautifulSoup`: HTML parsing.
- `sqlite3`: Data storage.
- `redis`: Distributed Bloom Filter signaling/persistence.
- `playwright`: (Optional) Dynamic rendering.
- `provoke.config`: Central configuration.
- `provoke.utils.bloom`: RedisBloom abstraction.

## Examples

Crawl a specific blog:

```bash
uv run python scripts/crawler.py https://example.com/blog 2
```

Crawl from a list of seeds with dynamic rendering:

```bash
uv run python scripts/crawler.py seeds.txt 1 --dynamic
```

## Related

- [CONFIG.md](CONFIG.md)
- [SEARCH_ENGINE.md](SEARCH_ENGINE.md)
