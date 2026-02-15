#!/usr/bin/env python3
"""
Re-run quality filters on all database pages.
Updates scores, tiers, and removes rejected pages.
"""

import sqlite3
import json
import sys
from provoke.config import evaluate_page_quality, config
from bs4 import BeautifulSoup


def rerun_filters(db_path="index.db", dry_run=True):
    """Re-run quality filters on all pages."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Ensure unified_score column exists
    cursor.execute("PRAGMA table_info(pages)")
    columns = [column[1] for column in cursor.fetchall()]
    if "unified_score" not in columns:
        print("Adding unified_score column to pages table...")
        cursor.execute("ALTER TABLE pages ADD COLUMN unified_score INTEGER")
        conn.commit()

    # Get all pages
    cursor.execute(
        "SELECT id, url, title, content, html, quality_score, quality_tier, unified_score FROM pages"
    )
    rows = cursor.fetchall()

    print(f"Found {len(rows)} pages to re-evaluate")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE - WILL DELETE'}")
    print("-" * 60)

    to_delete = []
    to_update = []

    for i, row in enumerate(rows):
        if i % 100 == 0:
            print(f"Processing page {i}/{len(rows)}...")
        page_id, url, title, content, html, old_qs, old_tier, old_us = row

        if not html or not content:
            # Can't re-evaluate without HTML/content
            continue

        # Re-run quality evaluation
        result = evaluate_page_quality(url, html, content)

        is_acceptable = result["is_acceptable"]
        new_tier = result["quality_tier"]
        scores = result["scores"]
        new_unified = scores.get("unified_score", 0)
        rejection_reasons = result["rejection_reasons"]

        # Serialize scores for storage
        scores_json = json.dumps(scores)

        if not is_acceptable:
            to_delete.append(
                {
                    "id": page_id,
                    "url": url,
                    "old_tier": old_tier,
                    "new_tier": new_tier,
                    "old_score": old_us,
                    "new_score": new_unified,
                    "reasons": rejection_reasons,
                }
            )
        elif old_tier != new_tier or abs((old_us or 0) - new_unified) > 5:
            # Significant change in tier or score
            to_update.append(
                {
                    "id": page_id,
                    "url": url,
                    "old_tier": old_tier,
                    "new_tier": new_tier,
                    "old_score": old_us,
                    "new_score": new_unified,
                    "scores_json": scores_json,
                }
            )

    print(f"\nPages to DELETE (rejected): {len(to_delete)}")
    for p in to_delete[:20]:
        print(
            f"  [{p['old_tier']}\u2192{p['new_tier']}] {p['old_score']}\u2192{p['new_score']} - {p['url'][:60]}..."
        )
        print(f"    Reasons: {', '.join(p['reasons'][:3])}")

    if len(to_delete) > 20:
        print(f"  ... and {len(to_delete) - 20} more")

    print(f"\nPages to UPDATE (tier/score changed): {len(to_update)}")
    for p in to_update[:10]:
        print(
            f"  [{p['old_tier']}\u2192{p['new_tier']}] {p['old_score']}\u2192{p['new_score']} - {p['url'][:60]}..."
        )

    if len(to_update) > 10:
        print(f"  ... and {len(to_update) - 10} more")

    if not dry_run:
        print("\nApplying changes...")

        # Delete rejected pages
        for p in to_delete:
            cursor.execute("DELETE FROM pages WHERE id = ?", (p["id"],))

        # Update tier/score for accepted pages
        for p in to_update:
            cursor.execute(
                "UPDATE pages SET quality_tier = ?, quality_score = ?, unified_score = ? WHERE id = ?",
                (p["new_tier"], p["scores_json"], p["new_score"], p["id"]),
            )

        conn.commit()
        print(f"Deleted {len(to_delete)} rejected pages")
        print(f"Updated {len(to_update)} pages")

    conn.close()
    print("\nDone!")


if __name__ == "__main__":
    dry_run = "--live" not in sys.argv
    rerun_filters(dry_run=dry_run)
