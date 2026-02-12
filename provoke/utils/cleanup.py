import sqlite3
import os
import requests
from urllib.parse import urlparse
from config import config, evaluate_page_quality


def is_domain_blacklisted(domain, blacklist):
    """Checks if a domain or any of its parent domains are in the blacklist."""
    parts = domain.split(".")
    for i in range(len(parts)):
        parent_domain = ".".join(parts[i:])
        if parent_domain in blacklist:
            return True
    return False


def cleanup_index():
    db_file = config.DATABASE_PATH
    if not os.path.exists(db_file):
        print(f"Error: {db_file} not found.")
        return

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # 1. Initialize DB schema (ensure html column exists)
    cursor.execute("PRAGMA table_info(pages)")
    columns = [column[1] for column in cursor.fetchall()]
    if "html" not in columns:
        print("Adding 'html' column to database...")
        cursor.execute("ALTER TABLE pages ADD COLUMN html TEXT")
        conn.commit()

    # 2. Fetch Blacklist and Whitelist domains
    try:
        cursor.execute("SELECT domain FROM blacklisted_domains")
        blacklist = {row[0].lower() for row in cursor.fetchall()}

        cursor.execute("SELECT domain FROM whitelisted_domains")
        whitelist = {row[0].lower() for row in cursor.fetchall()}
    except sqlite3.OperationalError:
        print("Error: Required management tables not found.")
        conn.close()
        return

    # 3. Fetch all indexed pages
    cursor.execute("SELECT id, url, content, html FROM pages")
    pages = cursor.fetchall()

    to_delete = []
    to_update_html = []
    reasons = {}

    print(f"Re-evaluating {len(pages)} pages against ALL filters...")

    for page_id, url, text, html in pages:
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
            print(f"  Fetching missing HTML for: {url}")
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
        # Note: whitelist is passed to evaluate_page_quality for Phase 1 bypass
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
    if to_update_html:
        print(f"Updating {len(to_update_html)} pages with fetched HTML...")
        cursor.executemany("UPDATE pages SET html = ? WHERE id = ?", to_update_html)
        conn.commit()

    if to_delete:
        print(f"\nFound {len(to_delete)} pages to remove:")
        reason_summary = {}
        for pid in to_delete:
            r = reasons[pid].split("(")[0]
            reason_summary[r] = reason_summary.get(r, 0) + 1

        for r, count in sorted(
            reason_summary.items(), key=lambda x: x[1], reverse=True
        ):
            print(f"  - {r}: {count}")

        cursor.executemany(
            "DELETE FROM pages WHERE id = ?", [(pid,) for pid in to_delete]
        )
        conn.commit()
        print("\nCleanup complete.")
    else:
        print("\nAll pages passed existing filters.")

    conn.close()


def main():
    cleanup_index()


if __name__ == "__main__":
    main()
