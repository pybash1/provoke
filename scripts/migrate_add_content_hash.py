#!/usr/bin/env python3
"""
Add content_hash column to the pages table.

This migration adds the content_hash column and index to support
duplicate content detection.
"""

import sqlite3
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from provoke.config import config


def migrate_add_content_hash(db_path: str):
    """Add content_hash column and index to pages table."""

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if column already exists
        cursor.execute("PRAGMA table_info(pages)")
        columns = [column[1] for column in cursor.fetchall()]

        if "content_hash" in columns:
            print("✓ content_hash column already exists!")
            conn.close()
            return True

        print("Adding content_hash column to pages table...")

        # Add the column
        cursor.execute("ALTER TABLE pages ADD COLUMN content_hash TEXT")

        # Create index for fast duplicate lookups
        print("Creating index on content_hash...")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_content_hash ON pages(content_hash)"
        )

        conn.commit()
        conn.close()

        print("✓ Migration complete!")
        print("  - Added content_hash column")
        print("  - Created idx_content_hash index")

        return True

    except sqlite3.Error as e:
        print(f"Error: Database migration failed")
        print(f"SQLite error: {e}")
        return False


def main():
    db_path = config.DATABASE_PATH

    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        sys.exit(1)

    print(f"Database: {db_path}")

    if migrate_add_content_hash(db_path):
        print("\n✓ Ready to backfill content hashes!")
        print("  Run: python scripts/backfill_content_hashes.py")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
