#!/usr/bin/env python3
"""
Index pages from RSS feeds using only the ML classifier (skips all other filters).

This script:
1. Reads RSS feed URLs from the rss_feeds table in the database
2. Parses each feed to extract article URLs
3. Fetches each article page
4. Runs only the ML model quality check
5. Indexes the page if the ML model passes it

Usage:
    uv run python scripts/index_from_rss.py
    uv run python scripts/index_from_rss.py --model models/content_classifier.bin
    uv run python scripts/index_from_rss.py --max-workers 10
    uv run python scripts/index_from_rss.py --limit 100
"""

import argparse
import sqlite3
import sys
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
from bs4 import BeautifulSoup

from provoke.config import config
from provoke.ml.classifier import get_classifier

warnings.filterwarnings("ignore")


def get_rss_feeds_from_db(db_path: str, active_only: bool = True) -> list:
    """Get RSS feed URLs from the rss_feeds table."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if table exists
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='rss_feeds'"
    )
    if not cursor.fetchone():
        print("No rss_feeds table found. Run migrate_rss_feeds.py first.", file=sys.stderr)
        conn.close()
        return []

    if active_only:
        cursor.execute(
            """
            SELECT url, title, source_domain
            FROM rss_feeds WHERE is_active = 1
            """
        )
    else:
        cursor.execute(
            """
            SELECT url, title, source_domain
            FROM rss_feeds
            """
        )

    rows = cursor.fetchall()
    conn.close()

    return [
        {"url": row[0], "title": row[1] or "", "domain": row[2]}
        for row in rows
    ]


def parse_rss_feed(feed_url: str) -> list:
    """Parse an RSS/Atom feed and return a list of entry URLs with metadata."""
    entries = []
    try:
        response = requests.get(
            feed_url,
            timeout=config.HTTP_TIMEOUT,
            headers={"User-Agent": config.USER_AGENT},
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "xml")

        # Try RSS 2.0 format
        items = soup.find_all("item")
        if items:
            for item in items:
                link = item.find("link")
                title = item.find("title")
                if link and link.text:
                    entries.append({
                        "url": link.text.strip(),
                        "title": title.text.strip() if title else "",
                        "source_feed": feed_url,
                    })

        # Try Atom format
        if not items:
            entries_tags = soup.find_all("entry")
            for entry in entries_tags:
                link = entry.find("link")
                title = entry.find("title")
                if link:
                    href = link.get("href", "")
                    if href:
                        entries.append({
                            "url": href.strip(),
                            "title": title.text.strip() if title else "",
                            "source_feed": feed_url,
                        })

    except Exception as e:
        print(f"Error parsing feed {feed_url}: {e}", file=sys.stderr)

    return entries


def fetch_page(url: str) -> dict | None:
    """Fetch a page and return its content."""
    try:
        response = requests.get(
            url,
            timeout=config.HTTP_TIMEOUT,
            headers={"User-Agent": config.USER_AGENT},
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")
        title = soup.title.string if soup.title else url
        text = soup.get_text(separator=" ", strip=True)

        return {
            "url": url,
            "title": str(title),
            "text": text,
            "html": response.text,
        }
    except Exception as e:
        print(f"Error fetching {url}: {e}", file=sys.stderr)
        return None


def ml_only_filter(page_data: dict, classifier) -> tuple[bool, str, float]:
    """Run only the ML classifier, skip all other quality filters."""
    is_acceptable, reason, confidence = classifier.is_acceptable(
        text=page_data["text"],
        url=page_data["url"],
        title=page_data["title"],
    )
    return is_acceptable, reason, confidence


def save_page_to_db(db_path: str, page_data: dict, ml_reason: str, ml_confidence: float):
    """Save a page to the database with ML classification info."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Ensure table exists
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE,
            title TEXT,
            content TEXT,
            html TEXT,
            quality_score TEXT,
            quality_tier TEXT
        )
        """
    )

    quality_score = {
        "ml_reason": ml_reason,
        "ml_confidence": ml_confidence,
        "filter_type": "ml_only",
    }

    import json

    cursor.execute(
        """
        INSERT OR REPLACE INTO pages (url, title, content, html, quality_score, quality_tier)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            page_data["url"],
            page_data["title"],
            page_data["text"],
            page_data["html"],
            json.dumps(quality_score),
            "ml_accepted",
        ),
    )
    conn.commit()
    conn.close()


def process_entry(entry: dict, classifier, db_path: str, stats: dict):
    """Process a single RSS entry: fetch and classify with ML only."""
    url = entry["url"]

    # Check if already in database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM pages WHERE url = ?", (url,))
    if cursor.fetchone():
        conn.close()
        stats["skipped_already_indexed"] += 1
        return
    conn.close()

    # Fetch the page
    page_data = fetch_page(url)
    if not page_data:
        stats["fetch_errors"] += 1
        return

    # Run ML-only classification
    is_acceptable, reason, confidence = ml_only_filter(page_data, classifier)

    if is_acceptable:
        save_page_to_db(db_path, page_data, reason, confidence)
        stats["accepted"] += 1
        print(f"✓ ACCEPTED: {url} (confidence: {confidence:.2f})")
    else:
        stats["rejected"] += 1
        print(f"✗ REJECTED: {url} (reason: {reason}, confidence: {confidence:.2f})")


def update_feed_stats(db_path: str, feed_url: str, entry_count: int):
    """Update the feed's last_checked and entry_count in the database."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE rss_feeds
            SET last_checked = ?, entry_count = ?
            WHERE url = ?
            """,
            (datetime.now().isoformat(), entry_count, feed_url),
        )
        conn.commit()
        conn.close()
    except sqlite3.Error:
        pass


def main():
    parser = argparse.ArgumentParser(
        description="Index pages from RSS feeds using only ML classification"
    )
    parser.add_argument(
        "--db", type=str, default=config.DATABASE_PATH, help="Path to SQLite database"
    )
    parser.add_argument(
        "--model",
        type=str,
        default=config.ML_CONFIG["model_path"],
        help="Path to FastText model",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=5,
        help="Number of parallel workers (default: 5)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of entries to process per feed (for testing)",
    )
    parser.add_argument(
        "--include-inactive",
        action="store_true",
        help="Also process inactive feeds",
    )

    args = parser.parse_args()

    # Load ML classifier
    print(f"Loading ML model from {args.model}...", flush=True)
    classifier = get_classifier(args.model)
    if not classifier:
        print(f"Failed to load ML model from {args.model}", file=sys.stderr)
        sys.exit(1)
    print("ML model loaded successfully", flush=True)

    # Get RSS feed URLs from table
    feed_urls = get_rss_feeds_from_db(args.db, active_only=not args.include_inactive)
    if not feed_urls:
        print("No RSS feeds found in database.")
        sys.exit(0)

    print(f"Found {len(feed_urls)} RSS feeds to process", flush=True)

    # Collect all entries from all feeds
    all_entries = []
    for feed in feed_urls:
        feed_url = feed["url"]
        print(f"Parsing feed: {feed_url}", flush=True)
        entries = parse_rss_feed(feed_url)
        print(f"  → {len(entries)} entries found", flush=True)
        all_entries.extend(entries)
        update_feed_stats(args.db, feed_url, len(entries))

    # Remove duplicates by URL
    seen_urls = set()
    unique_entries = []
    for entry in all_entries:
        if entry["url"] not in seen_urls:
            seen_urls.add(entry["url"])
            unique_entries.append(entry)

    print(f"\nTotal unique entries to process: {len(unique_entries)}", flush=True)

    if args.limit:
        unique_entries = unique_entries[: args.limit]
        print(f"Limited to first {args.limit} entries", flush=True)

    # Stats tracking
    stats = {
        "accepted": 0,
        "rejected": 0,
        "fetch_errors": 0,
        "skipped_already_indexed": 0,
    }

    # Process entries with thread pool
    print(f"\nProcessing with {args.max_workers} parallel workers...", flush=True)
    print("=" * 60, flush=True)

    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        futures = {
            executor.submit(process_entry, entry, classifier, args.db, stats): entry
            for entry in unique_entries
        }

        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"Error processing entry: {e}", file=sys.stderr)

    print("=" * 60, flush=True)
    print("\nSUMMARY:", flush=True)
    print(f"  Accepted:              {stats['accepted']}", flush=True)
    print(f"  Rejected:              {stats['rejected']}", flush=True)
    print(f"  Fetch errors:          {stats['fetch_errors']}", flush=True)
    print(f"  Already indexed:       {stats['skipped_already_indexed']}", flush=True)
    print(f"  Total processed:       {sum(stats.values())}", flush=True)


if __name__ == "__main__":
    main()
