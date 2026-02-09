import csv
import os
import requests
from bs4 import BeautifulSoup


# Import from ml_data_prep if needed, or just redefine
def fetch_basic_info(url):
    """Fetch basic title and snippet for a URL."""
    try:
        response = requests.get(
            url,
            timeout=5,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            },
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
        pass
    return "", ""


def main():
    stats_file = "quality_stats.csv"
    output_file = "data/to_label.csv"
    limit = 100

    if not os.path.exists(stats_file):
        print(f"{stats_file} not found.")
        return

    # Load existing URLs to avoid duplicates
    existing_urls = set()
    if os.path.exists(output_file):
        with open(output_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing_urls.add(row["url"])

    landing_urls = []
    with open(stats_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = row["url"].strip('"')
            reasons = row["rejection_reasons"]

            is_landing = "landing" in url.lower() or "Corporate Page" in reasons

            if is_landing and url not in existing_urls:
                landing_urls.append(url)
                if len(landing_urls) >= limit:
                    break

    print(f"Found {len(landing_urls)} potential landing pages. Processing...")

    new_entries = []
    for i, url in enumerate(landing_urls):
        print(f"[{i+1}/{len(landing_urls)}] Fetching: {url}")
        title, snippet = fetch_basic_info(url)
        if not title and not snippet:
            title = "LANDING PAGE"
            snippet = "Rejected as landing/corporate page."

        new_entries.append(
            {
                "url": url,
                "title": title[:100],
                "snippet": snippet[:300],
                "quality": "bad",
            }
        )

    if not new_entries:
        print("No new landing pages to add.")
        return

    # Append to CSV
    file_exists = os.path.exists(output_file)
    with open(output_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["url", "title", "snippet", "quality"])
        if not file_exists:
            writer.writeheader()
        for entry in new_entries:
            writer.writerow(entry)

    print(f"Successfully added {len(new_entries)} landing pages to {output_file}")


if __name__ == "__main__":
    main()
