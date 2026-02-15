#!/usr/bin/env python3
"""
Remove duplicate content from the database.

This script identifies pages with identical content hashes and removes duplicates,
keeping only the first occurrence (by ID).
"""

import sqlite3
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from provoke.config import config


def remove_duplicate_content(db_path: str, dry_run: bool = True):
    """Remove duplicate pages based on content hash."""

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Find all duplicate content hashes
    cursor.execute(
        """
        SELECT content_hash, COUNT(*) as count
        FROM pages
        WHERE content_hash IS NOT NULL
        GROUP BY content_hash
        HAVING count > 1
        ORDER BY count DESC
    """
    )

    duplicates = cursor.fetchall()

    if not duplicates:
        print("✓ No duplicate content found!")
        conn.close()
        return

    print(f"Found {len(duplicates)} unique pieces of content with duplicates")

    total_to_remove = 0
    for content_hash, count in duplicates:
        total_to_remove += count - 1  # Keep one, remove the rest

    print(f"Total duplicate pages to remove: {total_to_remove}")

    if dry_run:
        print("\n[DRY RUN] Showing what would be removed:\n")
    else:
        print("\n[REMOVING DUPLICATES]\n")

    removed_count = 0

    for content_hash, count in duplicates:
        # Get all URLs with this hash
        cursor.execute(
            "SELECT id, url FROM pages WHERE content_hash = ? ORDER BY id",
            (content_hash,),
        )
        pages = cursor.fetchall()

        # Keep the first one, mark others for removal
        keep_id, keep_url = pages[0]
        duplicates_to_remove = pages[1:]

        print(f"Content hash: {content_hash[:16]}... ({count} copies)")
        print(f"  ✓ KEEPING: {keep_url}")

        for dup_id, dup_url in duplicates_to_remove:
            print(f"  ✗ REMOVE:  {dup_url}")

            if not dry_run:
                cursor.execute("DELETE FROM pages WHERE id = ?", (dup_id,))
                removed_count += 1

        print()

    if not dry_run:
        conn.commit()
        print(f"✓ Removed {removed_count} duplicate pages")
    else:
        print(f"\n💡 To actually remove duplicates, run:")
        print(f"   python scripts/remove_duplicate_content.py --confirm")

    conn.close()


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Remove duplicate content from the database"
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Actually remove duplicates (default is dry-run)",
    )

    args = parser.parse_args()

    db_path = config.DATABASE_PATH

    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        sys.exit(1)

    print(f"Database: {db_path}")
    remove_duplicate_content(db_path, dry_run=not args.confirm)


if __name__ == "__main__":
    main()
