#!/usr/bin/env python3
"""
Utility script to list RSS feed URLs and sitemap URLs from the database.

RSS feeds are now stored in a dedicated rss_feeds table.
New RSS feeds discovered from page scans are automatically added to this table.

Usage:
    uv run python scripts/list_feeds_and_sitemaps.py           # List all feeds from rss_feeds table
    uv run python scripts/list_feeds_and_sitemaps.py --scan   # Scan pages and add new feeds to table
    uv run python scripts/list_feeds_and_sitemaps.py --format json
"""

import sqlite3
import sys
import argparse
import json
import warnings
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from bs4 import BeautifulSoup
from bs4 import XMLParsedAsHTMLWarning
from provoke.config import config

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


def get_feeds_from_table(db_path: str, active_only: bool = True) -> list:
    """Get RSS feeds from the rss_feeds table."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if table exists
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='rss_feeds'"
    )
    if not cursor.fetchone():
        conn.close()
        return []

    if active_only:
        cursor.execute(
            """
            SELECT url, title, feed_type, source_domain, date_added
            FROM rss_feeds WHERE is_active = 1
            ORDER BY source_domain, url
            """
        )
    else:
        cursor.execute(
            """
            SELECT url, title, feed_type, source_domain, date_added
            FROM rss_feeds
            ORDER BY source_domain, url
            """
        )

    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "url": row[0],
            "title": row[1] or "",
            "type": row[2] or "unknown",
            "domain": row[3],
            "added": row[4],
        }
        for row in rows
    ]


def extract_feeds_from_html(html: str, base_url: str) -> list:
    """Extract RSS/Atom feed URLs from HTML content.

    Only includes feeds with type 'application/rss+xml' or URLs ending with .xml
    """
    if not html:
        return []

    feeds = []
    try:
        soup = BeautifulSoup(html, "lxml")
        domain = urlparse(base_url).netloc

        for link in soup.find_all("link", rel="alternate"):
            link_type = link.get("type", "").lower()
            href = link.get("href", "")

            if not href:
                continue

            full_url = urljoin(base_url, href)

            # Only include if type is application/rss+xml or URL ends with .xml
            is_rss_type = link_type == "application/rss+xml"
            ends_with_xml = full_url.lower().endswith(".xml")

            if is_rss_type or ends_with_xml:
                feeds.append({
                    "url": full_url,
                    "type": link.get("type", "unknown"),
                    "title": link.get("title", ""),
                    "source_domain": domain,
                    "discovered_from": base_url,
                })

    except Exception:
        pass

    return feeds


def add_feeds_to_table(db_path: str, feeds: list) -> int:
    """Add discovered feeds to the rss_feeds table."""
    if not feeds:
        return 0

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Ensure table exists
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS rss_feeds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE NOT NULL,
            discovered_from TEXT,
            title TEXT,
            feed_type TEXT,
            source_domain TEXT,
            date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_checked TIMESTAMP,
            entry_count INTEGER,
            is_active BOOLEAN DEFAULT 1,
            error_count INTEGER DEFAULT 0
        )
        """
    )

    added_count = 0
    for feed in feeds:
        try:
            cursor.execute(
                """
                INSERT OR IGNORE INTO rss_feeds
                (url, discovered_from, title, feed_type, source_domain, date_added)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    feed["url"],
                    feed.get("discovered_from", ""),
                    feed.get("title", ""),
                    feed.get("type", "unknown"),
                    feed.get("source_domain", ""),
                    datetime.now().isoformat(),
                ),
            )
            if cursor.rowcount > 0:
                added_count += 1
        except sqlite3.Error:
            pass

    conn.commit()
    conn.close()
    return added_count


def scan_pages_for_feeds(db_path: str) -> tuple:
    """Scan all pages for RSS feeds and return (feeds_found, feeds_added)."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT url, html FROM pages WHERE html IS NOT NULL")
    rows = cursor.fetchall()
    conn.close()

    all_feeds = []
    for url, html in rows:
        if html:
            feeds = extract_feeds_from_html(html, url)
            all_feeds.extend(feeds)

    # Remove duplicates by URL
    seen = set()
    unique_feeds = []
    for feed in all_feeds:
        if feed["url"] not in seen:
            seen.add(feed["url"])
            unique_feeds.append(feed)

    added = add_feeds_to_table(db_path, unique_feeds)
    return len(unique_feeds), added


def extract_sitemaps_from_html(html: str, base_url: str) -> list:
    """Extract sitemap references from HTML content. Only includes URLs ending with .xml."""
    if not html:
        return []

    sitemaps = []
    try:
        soup = BeautifulSoup(html, "lxml")

        for a in soup.find_all("a", href=True):
            href = a.get("href", "").lower()
            if href.endswith(".xml") and "sitemap" in href:
                full_url = urljoin(base_url, href)
                sitemaps.append({
                    "url": full_url,
                    "source": "html_link",
                    "context": a.get_text(strip=True) or ""
                })

    except Exception:
        pass

    return sitemaps


def get_sitemaps_from_pages(db_path: str) -> list:
    """Scan pages for sitemap references."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT url, html FROM pages WHERE html IS NOT NULL")
    rows = cursor.fetchall()
    conn.close()

    all_sitemaps = []
    seen = set()

    for url, html in rows:
        if not html:
            continue
        sitemaps = extract_sitemaps_from_html(html, url)
        for sitemap in sitemaps:
            if sitemap["url"] not in seen:
                seen.add(sitemap["url"])
                all_sitemaps.append(sitemap)

    return all_sitemaps


def get_stats(db_path: str) -> dict:
    """Get statistics about feeds and sitemaps."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if rss_feeds table exists
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='rss_feeds'"
    )
    has_table = cursor.fetchone() is not None

    feed_count = 0
    domain_count = 0
    if has_table:
        cursor.execute("SELECT COUNT(*) FROM rss_feeds WHERE is_active = 1")
        feed_count = cursor.fetchone()[0]
        cursor.execute(
            "SELECT COUNT(DISTINCT source_domain) FROM rss_feeds WHERE is_active = 1"
        )
        domain_count = cursor.fetchone()[0]

    # Count total pages
    cursor.execute("SELECT COUNT(*) FROM pages")
    page_count = cursor.fetchone()[0]

    conn.close()

    return {
        "total_pages": page_count,
        "rss_feeds": feed_count,
        "domains_with_feeds": domain_count,
    }


def print_text_output(feeds: list, sitemaps: list, stats: dict, scan_info: dict = None):
    """Print results in human-readable text format."""
    print("=" * 60)
    print("RSS/FEED AND SITEMAP DISCOVERY REPORT")
    print("=" * 60)
    print()
    print(f"Total pages in database: {stats['total_pages']}")
    print(f"RSS feeds in table:      {stats['rss_feeds']}")
    print(f"Domains with feeds:      {stats['domains_with_feeds']}")
    print(f"Sitemaps found:          {len(sitemaps)}")
    if scan_info:
        print(f"Feeds discovered:        {scan_info['found']}")
        print(f"New feeds added:         {scan_info['added']}")
    print()

    if feeds:
        print("-" * 60)
        print("RSS/ATOM FEEDS")
        print("-" * 60)
        current_domain = None
        for feed in feeds:
            if feed["domain"] != current_domain:
                current_domain = feed["domain"]
                print(f"\n[{current_domain}]")
            print(f"  {feed['url']}")
        print()

    if sitemaps:
        print("-" * 60)
        print("SITEMAPS")
        print("-" * 60)
        for sitemap in sitemaps:
            print(f"\nURL: {sitemap['url']}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="List RSS feeds and sitemaps from the database"
    )
    parser.add_argument(
        "--db",
        type=str,
        default=config.DATABASE_PATH,
        help=f"Path to SQLite database (default: {config.DATABASE_PATH})",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--scan",
        action="store_true",
        help="Scan pages for new RSS feeds and add them to the table",
    )
    parser.add_argument(
        "--feeds-only",
        action="store_true",
        help="Only show RSS/Atom feeds",
    )
    parser.add_argument(
        "--sitemaps-only",
        action="store_true",
        help="Only show sitemaps",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Include inactive feeds",
    )

    args = parser.parse_args()

    scan_info = None
    if args.scan:
        print("Scanning pages for RSS feeds...", file=sys.stderr)
        found, added = scan_pages_for_feeds(args.db)
        scan_info = {"found": found, "added": added}
        print(f"Found {found} feeds, added {added} new ones to table.", file=sys.stderr)

    feeds = get_feeds_from_table(args.db, active_only=not args.all)
    sitemaps = get_sitemaps_from_pages(args.db) if not args.feeds_only else []
    stats = get_stats(args.db)

    if args.sitemaps_only:
        feeds = []

    if args.format == "json":
        data = {
            "feeds": feeds,
            "sitemaps": sitemaps,
            "stats": {**stats, "sitemaps_found": len(sitemaps)},
        }
        if scan_info:
            data["scan"] = scan_info
        print(json.dumps(data, indent=2))
    else:
        print_text_output(feeds, sitemaps, stats, scan_info)


if __name__ == "__main__":
    main()
