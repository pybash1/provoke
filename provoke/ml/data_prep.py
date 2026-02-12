import sqlite3
import csv
import random
import os
import requests
from bs4 import BeautifulSoup
from provoke.config import config

DB_PATH = config.DATABASE_PATH


def export_indexed_pages(output_file: str, limit: int = 500):
    """Export indexed URLs to CSV for manual labeling."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Sample pages (prioritize diverse domains)
    # We use a subquery to get diverse domains if possible, or just random
    cursor.execute(
        """
        SELECT url, title, content
        FROM pages
        ORDER BY RANDOM()
        LIMIT ?
    """,
        (limit,),
    )

    pages = cursor.fetchall()
    conn.close()

    # Export to CSV
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    # Use 'a' if file exists to allow multiple exports/augmentations
    file_exists = os.path.exists(output_file)
    with open(
        output_file, "a" if file_exists else "w", newline="", encoding="utf-8"
    ) as f:
        writer = csv.DictWriter(f, fieldnames=["url", "title", "snippet", "quality"])
        if not file_exists:
            writer.writeheader()

        for url, title, content in pages:
            writer.writerow(
                {
                    "url": url,
                    "title": (title or "")[:100],
                    "snippet": (content or "")[:300],
                    "quality": "",  # To be filled manually
                }
            )

    print(f"Exported {len(pages)} pages to {output_file}")


def fetch_basic_info(url):
    """Fetch basic title and snippet for a URL."""
    try:
        response = requests.get(
            url,
            timeout=config.CRAWLER_TIMEOUT,
            headers={"User-Agent": config.USER_AGENT_SHORT},
        )
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "lxml")
            title = soup.title.string if soup.title else ""
            # Get first 300 chars of body text as snippet
            if soup.body:
                # Remove script and style
                for script in soup.body(["script", "style"]):
                    script.decompose()
                text = soup.body.get_text(separator=" ", strip=True)
                snippet = text[:300]
            else:
                snippet = ""
            return title.strip() if title else "", snippet.strip()
    except Exception as e:
        print(f"Failed to fetch {url}: {e}")
    return "", ""


def augment_from_rejected_urls(
    output_file: str,
    limit: int = 100,
    stats_file: str | None = None,
    done_file: str | None = None,
):
    """Augment the labeling dataset with URLs that were rejected by the crawler."""
    if stats_file is None:
        stats_file = config.QUALITY_STATS_CSV
    if done_file is None:
        done_file = config.LABEL_DONE_CSV
    if not os.path.exists(stats_file):
        print(f"Stats file {stats_file} not found.")
        return

    existing_urls = set()

    # Load already labeled URLs if they exist
    for fpath in [done_file, output_file]:
        if os.path.exists(fpath):
            with open(fpath, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    existing_urls.add(row["url"])

    new_entries = []

    # Read stats and process newest first
    with open(stats_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
        if not lines:
            return
        reader = csv.DictReader(lines)
        rows = list(reader)
        rows.reverse()

        for row in rows:
            if len(new_entries) >= limit:
                break

            url = row["url"].strip('"')
            if url not in existing_urls:
                print(
                    f"Processing new rejected URL ({len(new_entries)+1}/{limit}): {url}"
                )
                title, snippet = fetch_basic_info(url)

                if not title and not snippet:
                    title = "REJECTED PAGE"
                    snippet = f"Reasons: {row['rejection_reasons']}"

                new_entries.append(
                    {
                        "url": url,
                        "title": title,
                        "snippet": snippet,
                        "quality": "bad",  # Pre-fill as bad
                    }
                )
                existing_urls.add(url)

    if not new_entries:
        print("No new rejected URLs to add.")
        return

    # Append to output_file
    file_exists = os.path.exists(output_file)
    mode = "a" if file_exists else "w"

    with open(output_file, mode, newline="", encoding="utf-8") as f:
        fieldnames = ["url", "title", "snippet", "quality"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        for entry in new_entries:
            writer.writerow(entry)

    print(f"Added {len(new_entries)} rejected URLs to {output_file}")
    print("Label the 'quality' column with: good, bad, or unsure")


def fetch_page_content(url: str) -> str:
    """Fetch or retrieve stored content for URL."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT content FROM pages WHERE url = ?", (url,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return row[0] or ""
    return ""


def create_fasttext_training_file(labeled_csv: str, output_file: str):
    """Convert labeled CSV to FastText training format."""
    import csv

    if not os.path.exists(labeled_csv):
        print(f"Error: {labeled_csv} not found.")
        return

    with open(labeled_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        with open(output_file, "w", encoding="utf-8") as out:
            count = 0
            for row in reader:
                quality = row["quality"].strip().lower()

                # Skip unlabeled or unsure
                if quality not in ["good", "bad"]:
                    continue

                # Fetch full content for this URL
                content = fetch_page_content(row["url"])

                if not content:
                    # Fallback to snippet if full content not found
                    content = row.get("snippet", "")

                # Clean text (remove newlines, extra spaces)
                clean_content = " ".join(content.split())

                # Get URL and title from the row
                url = row.get("url", "").strip()
                title = row.get("title", "").strip()

                # Clean title (remove newlines, extra spaces)
                clean_title = " ".join(title.split())

                # Write in FastText format with URL and title
                # Format: __label__<quality> url=<url> title=<title> <content>
                out.write(
                    f"__label__{quality} url={url} title={clean_title} {clean_content}\n"
                )
                count += 1

    print(f"Created FastText training file: {output_file} with {count} samples")


def split_training_data(
    input_file: str, train_file: str, test_file: str, test_ratio: float = 0.25
):
    """Split FastText data into train/test sets."""
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    with open(input_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    if not lines:
        print("Error: No data in training file.")
        return

    # Shuffle
    random.shuffle(lines)

    # Split
    split_idx = int(len(lines) * (1 - test_ratio))
    train_lines = lines[:split_idx]
    test_lines = lines[split_idx:]

    # Write splits
    with open(train_file, "w", encoding="utf-8") as f:
        f.writelines(train_lines)

    with open(test_file, "w", encoding="utf-8") as f:
        f.writelines(test_lines)

    print(f"Training samples: {len(train_lines)}")
    print(f"Test samples: {len(test_lines)}")
