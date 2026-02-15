import sqlite3
import os
import requests
import json
import argparse
from urllib.parse import urlparse
from datetime import datetime
from provoke.config import config, evaluate_page_quality

# File to track which URLs were checked in the last cleanup run
CHECKED_URLS_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "data", "cleanup_checked_urls.json")


def load_checked_urls():
    """Load the set of URLs that were checked in the last cleanup run."""
    if os.path.exists(CHECKED_URLS_FILE):
        try:
            with open(CHECKED_URLS_FILE, 'r') as f:
                data = json.load(f)
                return set(data.get('urls', [])), data.get('last_run')
        except (json.JSONDecodeError, IOError):
            return set(), None
    return set(), None


def save_checked_urls(urls):
    """Save the set of URLs that were checked in this cleanup run."""
    os.makedirs(os.path.dirname(CHECKED_URLS_FILE), exist_ok=True)
    data = {
        'urls': list(urls),
        'last_run': datetime.now().isoformat()
    }
    try:
        with open(CHECKED_URLS_FILE, 'w') as f:
            json.dump(data, f)
    except IOError as e:
        print(f"Warning: Could not save checked URLs tracking file: {e}")


def is_domain_blacklisted(domain, blacklist):
    """Checks if a domain or any of its parent domains are in the blacklist."""
    parts = domain.split(".")
    for i in range(len(parts)):
        parent_domain = ".".join(parts[i:])
        if parent_domain in blacklist:
            return True
    return False


def _cleanup_generator(check_all=False):
    """
    Internal generator that yields progress messages.
    Yields: str messages
    Returns: dict with stats
    """
    db_file = config.DATABASE_PATH
    if not os.path.exists(db_file):
        yield f"Error: {db_file} not found."
        return {"error": f"{db_file} not found"}

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # 1. Initialize DB schema (ensure html column exists)
    cursor.execute("PRAGMA table_info(pages)")
    columns = [column[1] for column in cursor.fetchall()]
    if "html" not in columns:
        yield "Adding 'html' column to database..."
        cursor.execute("ALTER TABLE pages ADD COLUMN html TEXT")
        conn.commit()

    # 2. Fetch Blacklist and Whitelist domains
    try:
        cursor.execute("SELECT domain FROM blacklisted_domains")
        blacklist = {row[0].lower() for row in cursor.fetchall()}

        cursor.execute("SELECT domain FROM whitelisted_domains")
        whitelist = {row[0].lower() for row in cursor.fetchall()}
    except sqlite3.OperationalError:
        yield "Error: Required management tables not found."
        conn.close()
        return {"error": "Required management tables not found"}

    # 3. Load previously checked URLs and filter pages
    checked_urls, last_run = load_checked_urls()

    # Fetch all indexed pages
    cursor.execute("SELECT id, url, content, html FROM pages")
    all_pages = cursor.fetchall()

    # Filter pages based on check_all flag
    if check_all:
        pages = all_pages
        msg = f"Re-evaluating ALL {len(pages)} pages against ALL filters..."
    else:
        pages = [p for p in all_pages if p[1] not in checked_urls]
        skipped_count = len(all_pages) - len(pages)
        msg = f"Re-evaluating {len(pages)} new pages (skipped {skipped_count} already checked)..."
        if last_run:
            msg += f" Last run: {last_run[:10]}"

    # Handle case where there are no pages to check
    if not pages:
        msg = "No new pages to check."
        if not check_all and checked_urls:
            msg = f"No new pages to check. ({len(checked_urls)} URLs were checked in previous runs, use --all to re-check)"
        yield msg
        conn.close()
        save_checked_urls(checked_urls)
        return {"total_evaluated": 0, "updated_html": 0, "deleted": 0, "reasons": {}}

    yield msg

    to_delete = []
    to_update_html = []
    reasons = {}
    urls_checked = set()

    for page_id, url, text, html in pages:
        # Track this URL as checked
        urls_checked.add(url)

        # Check domain blacklist first (fastest)
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if is_domain_blacklisted(domain, blacklist):
            to_delete.append(page_id)
            reasons[page_id] = "domain_blacklisted"
            continue

        # If html is missing, we must re-fetch to run ALL filters
        current_html = html
        if not current_html:
            yield f"  Fetching missing HTML for: {url}"
            try:
                response = requests.get(url, timeout=config.HTTP_TIMEOUT)
                if response.status_code == 200:
                    current_html = response.text
                    to_update_html.append((current_html, page_id))
                else:
                    to_delete.append(page_id)
                    reasons[page_id] = f"fetch_failed(status={response.status_code})"
                    continue
            except Exception as e:
                to_delete.append(page_id)
                reasons[page_id] = f"fetch_error({type(e).__name__})"
                continue

        # Run FULL quality evaluation
        res = evaluate_page_quality(url, current_html, text, whitelist=whitelist)

        if not res["is_acceptable"]:
            to_delete.append(page_id)
            reason = (
                res["rejection_reasons"][0]
                if res["rejection_reasons"]
                else "failed_quality"
            )
            reasons[page_id] = reason

    # 4. Updates & Deletions
    stats = {
        "total_evaluated": len(pages),
        "updated_html": len(to_update_html),
        "deleted": len(to_delete),
        "reasons": {},
    }

    if to_update_html:
        yield f"Updating {len(to_update_html)} pages with fetched HTML..."
        cursor.executemany("UPDATE pages SET html = ? WHERE id = ?", to_update_html)
        conn.commit()

    if to_delete:
        reason_summary = {}
        for pid in to_delete:
            r = reasons[pid].split("(")[0]
            reason_summary[r] = reason_summary.get(r, 0) + 1

        stats["reasons"] = reason_summary

        yield f"\nFound {len(to_delete)} pages to remove:"
        for r, count in sorted(reason_summary.items(), key=lambda x: x[1], reverse=True):
            yield f"  - {r}: {count}"
        yield "\nDeleting..."

        cursor.executemany(
            "DELETE FROM pages WHERE id = ?", [(pid,) for pid in to_delete]
        )
        conn.commit()

        yield "\nCleanup complete."
        yield f"\n[CLEANUP_COMPLETE] {stats['deleted']} pages removed, {stats['updated_html']} updated"
    else:
        yield "\nAll pages passed existing filters."
        yield f"\n[CLEANUP_COMPLETE] {stats['deleted']} pages removed, {stats['updated_html']} updated"

    conn.close()

    # Save checked URLs (merge with previously checked)
    all_checked_urls = urls_checked.union(checked_urls) if not check_all else urls_checked
    save_checked_urls(all_checked_urls)

    return stats


def cleanup_index(yield_output=False, check_all=False):
    """
    Re-evaluate indexed pages against current filters and remove low-quality pages.

    By default, only checks URLs that were not checked in the previous run.
    Use check_all=True to re-evaluate all pages.

    Args:
        yield_output: If True, yields output lines as strings for streaming.
                     If False, prints directly to stdout.
        check_all: If True, check all pages. If False, only check new pages
                  since last cleanup run.

    Returns:
        Dict with cleanup statistics if yield_output is False.
        Generator if yield_output is True.
    """
    gen = _cleanup_generator(check_all=check_all)

    if yield_output:
        return gen
    else:
        # Consume the generator and print messages
        stats = None
        try:
            while True:
                msg = next(gen)
                print(msg)
        except StopIteration as e:
            # Generator returns stats via StopIteration.value
            stats = e.value
        return stats


def main():
    parser = argparse.ArgumentParser(
        description="Clean up low-quality pages from the index."
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Check all pages, not just new ones since last run",
    )
    args = parser.parse_args()

    stats = cleanup_index(check_all=args.all)
    if stats is None:
        print("Cleanup failed - check error messages above.")
        exit(1)


if __name__ == "__main__":
    main()
