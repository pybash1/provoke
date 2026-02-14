#!/usr/bin/env python3
"""
Migration script to create rss_feeds table and populate it from existing data.

This script:
1. Creates a new rss_feeds table
2. Scans all pages in the database for RSS feed links
3. Adds discovered RSS feeds to the new table
4. Provides utilities to manage RSS feeds going forward

Usage:
    uv run python scripts/migrate_rss_feeds.py
    uv run python scripts/migrate_rss_feeds.py --migrate
    uv run python scripts/migrate_rss_feeds.py --scan
    uv run python scripts/migrate_rss_feeds.py --list
"""

import argparse
import sqlite3
import sys
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


def init_rss_feeds_table(db_path: str):
    """Create the rss_feeds table if it doesn't exist."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

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

    # Create index for faster lookups
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_rss_feeds_domain ON rss_feeds(source_domain)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_rss_feeds_active ON rss_feeds(is_active)"
    )

    conn.commit()
    conn.close()
    print(f"Created/verified rss_feeds table in {db_path}")


def extract_feeds_from_html(html: str, base_url: str) -> list:
    """Extract RSS/Atom feed URLs from HTML content."""
    if not html:
        return []

    feeds = []
    try:
        soup = BeautifulSoup(html, "lxml")
        domain = urlparse(base_url).netloc

        # Look for link elements with feed types
        for link in soup.find_all("link", rel="alternate"):
            link_type = link.get("type", "").lower()
            href = link.get("href", "")

            if not href:
                continue

            # Only include if type is application/rss+xml or URL ends with .xml
            is_rss_type = link_type == "application/rss+xml"
            ends_with_xml = href.lower().endswith(".xml")

            if is_rss_type or ends_with_xml:
                full_url = urljoin(base_url, href)
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


def scan_and_migrate_feeds(db_path: str) -> int:
    """Scan all pages for RSS feeds and add them to the rss_feeds table."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all pages with HTML content
    cursor.execute("SELECT url, html FROM pages WHERE html IS NOT NULL")
    rows = cursor.fetchall()

    all_feeds = []
    for url, html in rows:
        if html:
            feeds = extract_feeds_from_html(html, url)
            all_feeds.extend(feeds)

    print(f"Discovered {len(all_feeds)} potential RSS feeds from {len(rows)} pages")

    # Insert unique feeds into rss_feeds table
    added_count = 0
    for feed in all_feeds:
        try:
            cursor.execute(
                """
                INSERT OR IGNORE INTO rss_feeds
                (url, discovered_from, title, feed_type, source_domain, date_added)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    feed["url"],
                    feed["discovered_from"],
                    feed["title"],
                    feed["type"],
                    feed["source_domain"],
                    datetime.now().isoformat(),
                ),
            )
            if cursor.rowcount > 0:
                added_count += 1
        except sqlite3.Error as e:
            print(f"Error inserting feed {feed['url']}: {e}", file=sys.stderr)

    conn.commit()
    conn.close()

    return added_count


def add_rss_feed(db_path: str, feed_url: str, source: str = "manual") -> bool:
    """Add a single RSS feed URL to the table."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    domain = urlparse(feed_url).netloc

    try:
        cursor.execute(
            """
            INSERT OR IGNORE INTO rss_feeds
            (url, discovered_from, source_domain, date_added)
            VALUES (?, ?, ?, ?)
            """,
            (feed_url, source, domain, datetime.now().isoformat()),
        )
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success
    except sqlite3.Error as e:
        print(f"Error adding feed {feed_url}: {e}", file=sys.stderr)
        conn.close()
        return False


def get_all_rss_feeds(db_path: str, active_only: bool = True) -> list:
    """Get all RSS feed URLs from the table."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    if active_only:
        cursor.execute(
            "SELECT url, title, feed_type, source_domain, date_added FROM rss_feeds WHERE is_active = 1"
        )
    else:
        cursor.execute(
            "SELECT url, title, feed_type, source_domain, date_added FROM rss_feeds"
        )

    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "url": row[0],
            "title": row[1] or "",
            "type": row[2] or "",
            "domain": row[3],
            "added": row[4],
        }
        for row in rows
    ]


def mark_feed_inactive(db_path: str, feed_url: str):
    """Mark a feed as inactive (e.g., if it's no longer accessible)."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE rss_feeds SET is_active = 0 WHERE url = ?",
        (feed_url,),
    )
    conn.commit()
    conn.close()


def list_feeds(db_path: str):
    """Print all RSS feeds in a formatted way."""
    feeds = get_all_rss_feeds(db_path, active_only=False)

    if not feeds:
        print("No RSS feeds found in database.")
        return

    print(f"\n{'='*80}")
    print(f"RSS FEEDS IN DATABASE ({len(feeds)} total)")
    print(f"{'='*80}\n")

    for feed in feeds:
        print(f"URL:     {feed['url']}")
        if feed['title']:
            print(f"Title:   {feed['title']}")
        print(f"Domain:  {feed['domain']}")
        print(f"Added:   {feed['added']}")
        print(f"-" * 80)


def main():
    parser = argparse.ArgumentParser(
        description="Manage RSS feeds table in the database"
    )
    parser.add_argument(
        "--db",
        type=str,
        default=config.DATABASE_PATH,
        help=f"Path to SQLite database (default: {config.DATABASE_PATH})",
    )
    parser.add_argument(
        "--init",
        action="store_true",
        help="Create rss_feeds table without migrating data",
    )
    parser.add_argument(
        "--migrate",
        action="store_true",
        help="Scan pages and migrate discovered RSS feeds to the new table",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all RSS feeds in the database",
    )
    parser.add_argument(
        "--add",
        type=str,
        metavar="FEED_URL",
        help="Add a single RSS feed URL manually",
    )

    args = parser.parse_args()

    # Always initialize the table first
    init_rss_feeds_table(args.db)

    if args.migrate:
        print("Scanning pages for RSS feeds...")
        added = scan_and_migrate_feeds(args.db)
        print(f"Migration complete. Added {added} new RSS feeds to the table.")

    elif args.add:
        if add_rss_feed(args.db, args.add, source="manual"):
            print(f"Added: {args.add}")
        else:
            print(f"Already exists or error: {args.add}")

    elif args.list or not any([args.init, args.migrate, args.add]):
        # Default action: list feeds
        list_feeds(args.db)

    print("\nDone.")


if __name__ == "__main__":
    main()
