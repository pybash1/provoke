#!/usr/bin/env python3
"""
Backward-compatible shim for provoke.crawler

The SimpleCrawler class has moved to the provoke package.
This file is maintained for backward compatibility.
"""

from provoke.crawler import SimpleCrawler

__all__ = ["SimpleCrawler"]

if __name__ == "__main__":
    # Delegate to the main function in provoke.crawler
    import sys
    import os

    if len(sys.argv) < 2:
        print("Usage: uv run python crawler.py <url_or_file> [max_depth] [--dynamic]")
        sys.exit(1)

    input_arg = sys.argv[1]
    depth = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 1
    use_dynamic = "--dynamic" in sys.argv

    urls_to_crawl = []
    if os.path.isfile(input_arg):
        with open(input_arg, "r") as f:
            for line in f:
                url = line.strip()
                if url and not url.startswith("#"):
                    urls_to_crawl.append(url)
    else:
        urls_to_crawl = [input_arg]

    if not urls_to_crawl:
        print("No URLs found to crawl.")
        sys.exit(0)

    # Import config here to avoid circular imports
    from config import config

    # Use the first URL to initialize the crawler base domain if needed
    crawler = SimpleCrawler(urls_to_crawl[0], max_depth=depth, use_dynamic=use_dynamic)
    try:
        for url in urls_to_crawl:
            print(f"\n>>> Starting crawl from input URL: {url}")
            # Reset stop markers for each new seed URL
            crawler.stop_requested = False
            crawler.consecutive_rejections = 0
            crawler.crawl(url)
    finally:
        crawler.close_browser()
        crawler.quality_logger.print_summary()
    print("[CRAWL COMPLETE]")
