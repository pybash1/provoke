import requests
from bs4 import BeautifulSoup
import sqlite3
import time
import os
from urllib.parse import urljoin, urlparse
import json
from config import config, evaluate_page_quality
from quality_logger import QualityLogger
import re


class SimpleCrawler:
    def __init__(self, base_url, max_depth=None, db_file=None, use_dynamic=False):
        self.base_url = base_url
        self.max_depth = (
            max_depth if max_depth is not None else config.CRAWLER_DEFAULT_MAX_DEPTH
        )
        self.db_file = db_file or config.DATABASE_PATH
        self.use_dynamic = use_dynamic
        self.init_db()
        # visited tracks URLs in the CURRENT session to avoid infinite loops.
        # Historical URLs in the database will be updated via 'INSERT OR REPLACE'.
        self.visited = set()
        self.playwright = None
        self.browser = None
        self.quality_logger = QualityLogger()
        self.blacklist = self.get_blacklisted_domains()
        self.whitelist = self.get_whitelisted_domains()
        self.domain_rejections = {}  # Tracks rejections per domain in current session
        self.consecutive_rejections = 0  # GLOBAL consecutive rejections
        self.stop_requested = False  # Flag to stop the entire crawl

    def init_db(self):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE,
            title TEXT,
            content TEXT,
            html TEXT,
            quality_score TEXT,
            quality_tier TEXT
        )
        """
        )

        # Ensure quality columns exist if table was created older versions
        cursor.execute("PRAGMA table_info(pages)")
        columns = [column[1] for column in cursor.fetchall()]
        if "quality_score" not in columns:
            cursor.execute("ALTER TABLE pages ADD COLUMN quality_score TEXT")
        if "quality_tier" not in columns:
            cursor.execute("ALTER TABLE pages ADD COLUMN quality_tier TEXT")
        if "html" not in columns:
            cursor.execute("ALTER TABLE pages ADD COLUMN html TEXT")

        # Create blacklisted_domains table
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS blacklisted_domains (domain TEXT PRIMARY KEY)"
        )

        # Create whitelisted_domains table
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS whitelisted_domains (domain TEXT PRIMARY KEY)"
        )

        # Migrate whitelisted_patterns if it exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='whitelisted_patterns'"
        )
        if cursor.fetchone():
            cursor.execute(
                "INSERT OR IGNORE INTO whitelisted_domains (domain) SELECT pattern FROM whitelisted_patterns"
            )
            cursor.execute("DROP TABLE whitelisted_patterns")

        # Check if Trigram FTS table exists (for fuzzy search)
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='pages_trigram'"
        )
        if not cursor.fetchone():
            print("Creating trigram index for fuzzy search...")
            cursor.execute(
                """
            CREATE VIRTUAL TABLE pages_trigram USING fts5(
                title,
                content,
                tokenize="trigram",
                content='pages',
                content_rowid='id'
            )
            """
            )
            # Triggers for keeping trigram index in sync
            cursor.execute(
                """
            CREATE TRIGGER pages_trigram_ai AFTER INSERT ON pages BEGIN
              INSERT INTO pages_trigram(rowid, title, content) VALUES (new.id, new.title, new.content);
            END;
            """
            )
            cursor.execute(
                """
            CREATE TRIGGER pages_trigram_ad AFTER DELETE ON pages BEGIN
              INSERT INTO pages_trigram(pages_trigram, rowid, title, content) VALUES('delete', old.id, old.title, old.content);
            END;
            """
            )
            cursor.execute(
                """
            CREATE TRIGGER pages_trigram_au AFTER UPDATE ON pages BEGIN
              INSERT INTO pages_trigram(pages_trigram, rowid, title, content) VALUES('delete', old.id, old.title, old.content);
              INSERT INTO pages_trigram(rowid, title, content) VALUES (new.id, new.title, new.content);
            END;
            """
            )
            # Backfill existing data
            cursor.execute(
                "INSERT INTO pages_trigram(rowid, title, content) SELECT id, title, content FROM pages"
            )

        conn.commit()
        conn.close()

    def get_blacklisted_domains(self):
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute("SELECT domain FROM blacklisted_domains")
            domains = {row[0] for row in cursor.fetchall()}
            conn.close()
            return domains
        except sqlite3.Error:
            return set()

    def get_whitelisted_domains(self):
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute("SELECT domain FROM whitelisted_domains")
            domains = {row[0] for row in cursor.fetchall()}
            conn.close()
            return domains
        except sqlite3.Error:
            return set()

    def start_browser(self):
        if self.use_dynamic and not self.browser:
            from playwright.sync_api import sync_playwright

            print("Starting headless browser for dynamic content...")
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=True)

    def close_browser(self):
        if self.browser:
            self.browser.close()
            self.browser = None
        if self.playwright:
            self.playwright.stop()
            self.playwright = None

    def normalize_url(self, url):
        # Strip fragment and query parameters for canonical URL
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")

    def is_valid_url(self, url):
        normalized = self.normalize_url(url)
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        path = parsed.path.lower()
        # Allow other domains, but still require a netloc and ensure not already visited/blacklisted
        # Also reject binary extensions listed in config (except PDF)
        if any(path.endswith(ext) for ext in config.BINARY_EXTENSIONS):
            return False

        # Reject based on URL patterns (tags, categories, etc.)
        for pattern in config.EXCLUDED_URL_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                return False

        # Check if domain or any of its parent domains are blacklisted
        parts = domain.split(".")
        for i in range(len(parts)):
            parent_domain = ".".join(parts[i:])
            if parent_domain in self.blacklist:
                return False

        return bool(parsed.netloc) and normalized not in self.visited

    def crawl(self, url, depth=0):
        if self.stop_requested:
            return

        normalized = self.normalize_url(url)
        if depth > self.max_depth or normalized in self.visited:
            return

        print(f"Crawling: {url} (Normalized: {normalized}, Depth: {depth})")
        self.visited.add(normalized)

        try:
            if self.use_dynamic:
                self.start_browser()
                if not self.browser:
                    print(f"Failed to start browser for {url}")
                    return
                page = self.browser.new_page()
                page.goto(
                    url, wait_until="networkidle", timeout=config.DYNAMIC_PAGE_TIMEOUT
                )
                # Wait a bit more for React/Vue to finish rendering if needed
                time.sleep(config.DYNAMIC_RENDER_WAIT)
                html = page.content()
                page.close()
            else:
                response = requests.get(url, timeout=config.CRAWLER_TIMEOUT)
                if response.status_code != 200:
                    return
                html = response.text

            soup = BeautifulSoup(html, "html.parser")

            # Extract text and title
            title = soup.title.string if soup.title else url
            text = soup.get_text(separator=" ", strip=True)

            # Quality Filtering
            quality_result = evaluate_page_quality(
                url, html, text, whitelist=self.whitelist
            )

            if quality_result["is_acceptable"]:
                self.quality_logger.log_acceptance(url, quality_result["quality_tier"])
                print(f"Accepted {url} (Tier: {quality_result['quality_tier']})")
                self.save_page(
                    url,
                    str(title),
                    text,
                    html,
                    quality_result["scores"],
                    quality_result["quality_tier"],
                )
                # Reset consecutive rejections on acceptance
                self.consecutive_rejections = 0  # Reset global counter
            else:
                self.quality_logger.log_rejection(
                    url, quality_result["rejection_reasons"], quality_result["scores"]
                )
                print(
                    f"Rejected {url}: {', '.join(quality_result['rejection_reasons'])}"
                )

                # Track domain rejections (total in session)
                parsed = urlparse(url)
                domain = parsed.netloc.lower()
                self.domain_rejections[domain] = (
                    self.domain_rejections.get(domain, 0) + 1
                )
                if (
                    self.domain_rejections[domain]
                    >= config.THRESHOLDS["domain_rejection_threshold"]
                ):
                    self.blacklist_domain(domain)

                # Track global consecutive rejections
                self.consecutive_rejections += 1

                if (
                    self.consecutive_rejections
                    >= config.THRESHOLDS["consecutive_rejection_threshold"]
                ):
                    print(
                        f"!!! GLOBAL consecutive rejection threshold hit ({self.consecutive_rejections}). Stopping crawl. !!!"
                    )
                    self.stop_requested = True

                # Continue to find and crawl links even if this page was rejected

            # Find and crawl links
            if depth < self.max_depth:
                for link in soup.find_all("a", href=True):
                    href = str(link["href"])
                    next_url = urljoin(url, href)
                    if self.is_valid_url(next_url):
                        self.crawl(next_url, depth + 1)
                        time.sleep(config.CRAWLER_POLITE_DELAY)  # Polite crawling
        except Exception as e:
            print(f"Error crawling {url}: {e}")

    def save_page(
        self, url, title, content, html, quality_score=None, quality_tier=None
    ):
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            # Serialize quality_score if it's a dict
            if isinstance(quality_score, dict):
                quality_score = json.dumps(quality_score)

            cursor.execute(
                "INSERT OR REPLACE INTO pages (url, title, content, html, quality_score, quality_tier) VALUES (?, ?, ?, ?, ?, ?)",
                (url, title, content, html, quality_score, quality_tier),
            )
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            print(f"Error saving to database: {e}")

    def blacklist_domain(self, domain):
        if domain not in self.blacklist:
            print(f"!!! BLACKLISTING DOMAIN: {domain} due to excessive rejections !!!")
            self.blacklist.add(domain)
            try:
                conn = sqlite3.connect(self.db_file)
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR IGNORE INTO blacklisted_domains (domain) VALUES (?)",
                    (domain,),
                )
                conn.commit()
                conn.close()
            except sqlite3.Error as e:
                print(f"Error blacklisting domain: {e}")


if __name__ == "__main__":
    import sys
    import os

    if len(sys.argv) < 2:
        print("Usage: python crawler.py <url_or_file> [max_depth] [--dynamic]")
        sys.exit(1)

    input_arg = sys.argv[1]
    depth = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 1
    use_dynamic = "--dynamic" in sys.argv

    urls_to_crawl = []
    if os.path.isfile(input_arg):
        with open(input_arg, "r") as f:
            for line in f:
                url = line.strip()
                if url and not url.startswith("#"):
                    urls_to_crawl.append(url)
    else:
        urls_to_crawl = [input_arg]

    if not urls_to_crawl:
        print("No URLs found to crawl.")
        sys.exit(0)

    # Use the first URL to initialize the crawler base domain if needed
    crawler = SimpleCrawler(urls_to_crawl[0], max_depth=depth, use_dynamic=use_dynamic)
    try:
        for url in urls_to_crawl:
            print(f"\n>>> Starting crawl from input URL: {url}")
            # Reset stop markers for each new seed URL
            crawler.stop_requested = False
            crawler.consecutive_rejections = 0
            crawler.crawl(url)
    finally:
        crawler.close_browser()
        crawler.quality_logger.print_summary()
    print("[CRAWL COMPLETE]")
