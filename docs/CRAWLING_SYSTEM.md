# Crawling System (`provoke/crawler.py`)

## Summary

The core crawling engine that traverses the web, extracts content, and enqueues high-quality pages for indexing. The system is designed for high concurrency and uses a message queue to decouple network-bound crawling from database-bound indexing.

## Description

The system implements the `AsyncCrawler` class, which handles asynchronous recursive traversal of URLs using `aiohttp` and `asyncio`.

### Decoupled Architecture

The crawling process is now decoupled into two main components:

1. **Crawler (`AsyncCrawler`)**: Responsible for fetching pages, evaluating their quality, and extracting links. If a page passes the quality threshold, it is pushed to a **Redis Stream** (`inked:crawl_results`).
2. **Indexer Worker (`IndexerWorker`)**: A dedicated background worker that consumes segments from the Redis Stream and performs the actual database persistence (SQLite). This prevents database lock contention from slowing down the high-speed crawler.

### Key Features

- **Asynchronous Traversal**: Utilizes `asyncio` and `aiohttp` for high-concurrency crawling.
- **Smart Tree Skipping**: Automatically abandons unproductive URL branches (subdirectories) if they consistently yield low-quality content.
- **Deduplication**: Uses first-512-byte SHA256 content hashing to avoid indexing duplicate content across different URLs.
- **Dynamic Content**: Auto-upgrades to Playwright (headless browser) if a page is detected as an SPA or requires JavaScript rendering.
- **Message Queueing**: Uses Redis Streams to reliably pass crawl results to the indexer.
- **Auto-Stopping**: Enforces global and per-domain rejection thresholds to prevent "bottom-less" crawls of low-quality networks.

## Public API / Interfaces

### `AsyncCrawler` Class

#### Methods:

- **`__init__(base_url, max_depth, use_dynamic=False)`**: Initialize the async crawler.
- **`run(seed_urls)`**: Start the asynchronous crawl process.
- **`enqueue_indexing_task(data)`**: Pushes accepted page metadata to Redis for the worker.

### `IndexerWorker` Class (`provoke/indexer_worker.py`)

#### Methods:

- **`run()`**: Listens to the Redis Stream and processes incoming indexing tasks.
- **`save_page(...)`**: Handles SQLite persistence and RSS feed extraction.

### CLI Commands:

```bash
# Start the Crawler
uv run provoke-crawler <url_or_file> [max_depth] [--dynamic]

# Start the Indexer Worker
uv run provoke-indexer-worker
```

## Infrastructure

The decoupled system requires **Redis** to be running. A `docker-compose.yml` is provided to easily spin up the required Redis instance:

```bash
docker-compose up -d redis
```

## Dependencies

- `aiohttp`: Async HTTP client.
- `redis`: Async Redis client.
- `BeautifulSoup`: HTML parsing.
- `sqlite3`: Data storage (via Indexer Worker).
- `playwright`: Dynamic rendering.

## Related

- [CONFIG.md](CONFIG.md)
- [DATA_STORAGE.md](DATA_STORAGE.md)
- [ML_CLASSIFICATION.md](ML_CLASSIFICATION.md)
