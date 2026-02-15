#!/usr/bin/env python3
"""
Backfill content hashes for existing pages in the database.

This script computes content hashes for all pages that don't have one yet,
enabling duplicate detection for the entire corpus.
"""

import sqlite3
import hashlib
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from provoke.config import config


def compute_content_hash(text: str) -> str:
    """Compute a hash of the first 512 bytes of text content for deduplication."""
    sample = text[:512].encode("utf-8", errors="ignore")
    return hashlib.sha256(sample).hexdigest()


def backfill_content_hashes(db_path: str, batch_size: int = 100):
    """Backfill content hashes for all pages without one."""

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Count pages without content hash
    cursor.execute("SELECT COUNT(*) FROM pages WHERE content_hash IS NULL")
    total_count = cursor.fetchone()[0]

    if total_count == 0:
        print("✓ All pages already have content hashes!")
        conn.close()
        return

    print(f"Found {total_count} pages without content hashes. Starting backfill...")

    # Process in batches to avoid memory issues
    processed = 0
    updated = 0
    duplicates_found = 0

    while True:
        # Fetch a batch of pages without content hash
        cursor.execute(
            """SELECT id, url, content FROM pages 
               WHERE content_hash IS NULL 
               LIMIT ?""",
            (batch_size,),
        )

        batch = cursor.fetchall()
        if not batch:
            break

        for page_id, url, content in batch:
            if content:
                content_hash = compute_content_hash(content)

                # Check if this hash already exists (potential duplicate)
                cursor.execute(
                    "SELECT url FROM pages WHERE content_hash = ? AND id != ?",
                    (content_hash, page_id),
                )
                existing = cursor.fetchone()

                if existing:
                    duplicates_found += 1
                    print(f"  [DUPLICATE] {url} → identical to {existing[0]}")

                # Update the content hash
                cursor.execute(
                    "UPDATE pages SET content_hash = ? WHERE id = ?",
                    (content_hash, page_id),
                )
                updated += 1

            processed += 1

            # Progress indicator
            if processed % 100 == 0:
                print(
                    f"  Progress: {processed}/{total_count} ({processed/total_count*100:.1f}%)"
                )

        # Commit after each batch
        conn.commit()

    conn.close()

    print(f"\n✓ Backfill complete!")
    print(f"  Total processed: {processed}")
    print(f"  Hashes computed: {updated}")
    print(f"  Duplicates found: {duplicates_found}")

    if duplicates_found > 0:
        print(f"\n💡 Tip: You can remove duplicate pages with:")
        print(f"   python scripts/remove_duplicate_content.py")


def main():
    db_path = config.DATABASE_PATH

    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        sys.exit(1)

    print(f"Database: {db_path}")
    backfill_content_hashes(db_path)


if __name__ == "__main__":
    main()
