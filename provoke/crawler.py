import requests
from bs4 import BeautifulSoup
import sqlite3
import time
import os
import sys
from urllib.parse import urljoin, urlparse
import json
from provoke.config import config, evaluate_page_quality
from provoke.utils.logger import QualityLogger
import re
from datetime import datetime
from dataclasses import dataclass, field
import signal
import hashlib
from provoke.utils.robots import RobotsParser


@dataclass
class BranchStats:
    """Tracks crawling statistics for a URL branch (tree)."""

    total_crawled: int = 0
    accepted_count: int = 0
    max_depth_reached: int = 0
    skipped: bool = False
    # Track by depth level for fine-grained analysis
    by_depth: dict = field(
        default_factory=dict
    )  # depth -> {"total": int, "accepted": int}

    def record_result(self, depth: int, accepted: bool):
        """Record a crawl result at a given depth."""
        self.total_crawled += 1
        if accepted:
            self.accepted_count += 1
        if depth > self.max_depth_reached:
            self.max_depth_reached = depth

        # Track by depth
        if depth not in self.by_depth:
            self.by_depth[depth] = {"total": 0, "accepted": 0}
        self.by_depth[depth]["total"] += 1
        if accepted:
            self.by_depth[depth]["accepted"] += 1

    @property
    def rejection_ratio(self) -> float:
        """Returns the ratio of rejected pages (0.0-1.0)."""
        if self.total_crawled == 0:
            return 0.0
        return 1.0 - (self.accepted_count / self.total_crawled)

    def should_skip(self, current_depth: int) -> bool:
        """
        Determine if this branch should be skipped based on quality metrics.
        Returns True if the branch is unproductive and should be abandoned.
        """
        if self.skipped:
            return True

        thresholds = config.THRESHOLDS
        min_samples = thresholds.get("branch_min_samples", 3)
        depth_threshold = thresholds.get("branch_depth_threshold", 2)
        rejection_threshold = thresholds.get("branch_rejection_ratio", 0.85)
        acceptance_bonus = thresholds.get("branch_acceptance_bonus", 2)

        # Don't skip until we've crawled enough to make a decision
        if self.total_crawled < min_samples:
            return False

        # Don't skip until we're at sufficient depth (give shallow pages a chance)
        if current_depth < depth_threshold:
            return False

        # Check if we've had ANY accepted pages (with bonus for new branches)
        effective_accepted = self.accepted_count + acceptance_bonus
        effective_total = self.total_crawled + acceptance_bonus
        effective_ratio = 1.0 - (effective_accepted / effective_total)

        # Skip if rejection ratio is too high
        if effective_ratio >= rejection_threshold:
            self.skipped = True
            return True

        return False

    def __str__(self):
        ratio = self.rejection_ratio
        status = "SKIPPED" if self.skipped else "active"
        return f"[{status}] {self.accepted_count}/{self.total_crawled} accepted ({ratio:.0%} rejection), depth {self.max_depth_reached}"


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
        self.branch_stats = (
            {}
        )  # URL branch -> BranchStats mapping for smart tree skipping
        self.robots_parser = RobotsParser(user_agent=config.USER_AGENT)
        self.feed_only_domains = (
            {}
        )  # Track domains that only serve feeds: domain -> feed_count

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def _handle_signal(self, signum, frame):
        """Signal handler to trigger graceful shutdown."""
        sig_name = "SIGINT" if signum == signal.SIGINT else "SIGTERM"
        print(f"\n[SIGNL] Received {sig_name}. Requesting graceful shutdown...")
        self.stop_requested = True

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
        if "unified_score" not in columns:
            cursor.execute("ALTER TABLE pages ADD COLUMN unified_score INTEGER")
        if "content_hash" not in columns:
            cursor.execute("ALTER TABLE pages ADD COLUMN content_hash TEXT")
            # Create index for fast duplicate lookups
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_content_hash ON pages(content_hash)"
            )

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

    def add_to_blacklist(self, domain: str):
        """Add a domain to the blacklist in the database and in-memory cache."""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO blacklisted_domains (domain) VALUES (?)",
                (domain,),
            )
            conn.commit()
            conn.close()
            # Update in-memory cache
            self.blacklist.add(domain)
        except sqlite3.Error as e:
            print(f"  Warning: Could not add {domain} to blacklist: {e}")

    def compute_content_hash(self, text: str) -> str:
        """Compute a hash of the first 512 bytes of text content for deduplication."""
        # Use first 512 bytes to create a fingerprint
        # This is enough to catch duplicates while being fast
        sample = text[:512].encode("utf-8", errors="ignore")
        return hashlib.sha256(sample).hexdigest()

    def is_duplicate_content(self, content_hash: str) -> tuple[bool, str | None]:
        """Check if content with this hash already exists in the database.
        Returns (is_duplicate, existing_url)
        """
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT url FROM pages WHERE content_hash = ? LIMIT 1", (content_hash,)
            )
            result = cursor.fetchone()
            conn.close()

            if result:
                return True, result[0]
            return False, None
        except sqlite3.Error:
            return False, None

    def is_rss_or_json_feed(self, html: str, url: str) -> bool:
        """Detect if the content is an RSS/Atom feed or JSON feed."""
        if not html:
            return False

        # Check for common feed patterns in first 1000 chars
        sample = html[:1000].strip().lower()

        # RSS/Atom feed detection
        rss_patterns = [
            "<rss",
            "<feed",
            "<?xml",
            "<atom:",
            'xmlns="http://www.w3.org/2005/atom"',
            'xmlns="http://purl.org/rss/',
        ]

        for pattern in rss_patterns:
            if pattern in sample:
                return True

        # JSON feed detection
        if sample.startswith("{") or sample.startswith("["):
            try:
                import json

                data = json.loads(html[:5000])  # Parse first 5KB
                # Check for common JSON feed structures
                if isinstance(data, dict):
                    # JSON Feed format
                    if "version" in data and "items" in data:
                        return True
                    # Common API/feed patterns
                    if any(
                        key in data
                        for key in ["feed", "entries", "posts", "articles", "items"]
                    ):
                        return True
            except (json.JSONDecodeError, ValueError):
                pass

        return False

    def check_and_blacklist_feed_domain(self, domain: str) -> bool:
        """Check if a domain should be auto-blacklisted for serving only feeds.
        Returns True if domain was blacklisted.
        """
        if domain not in self.feed_only_domains:
            return False

        feed_count = self.feed_only_domains[domain]
        threshold = config.THRESHOLDS.get("feed_only_domain_threshold", 2)

        # If we've seen multiple feeds from this domain, blacklist it
        if feed_count >= threshold:
            print(
                f"  ↳ [AUTO-BLACKLIST] Domain {domain} only serves feeds ({feed_count} detected)"
            )
            self.add_to_blacklist(domain)
            return True

        return False

    def start_browser(self):
        if not self.browser:
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

    def fetch_dynamic(self, url):
        """Fetch a URL using Playwright (headless browser)."""
        self.start_browser()
        if not self.browser:
            return None

        try:
            page = self.browser.new_page()
            # Set viewport to a standard desktop size to ensure content loads correctly
            page.set_viewport_size({"width": 1280, "height": 800})

            page.goto(
                url, wait_until="networkidle", timeout=config.DYNAMIC_PAGE_TIMEOUT
            )
            # Wait a bit more for React/Vue to finish rendering if needed
            time.sleep(config.DYNAMIC_RENDER_WAIT)
            html = page.content()
            page.close()
            return html
        except Exception as e:
            print(f"  ↳ Warning: Dynamic fetch failed for {url}: {e}")
            return None

    def normalize_url(self, url):
        # Strip fragment and query parameters for canonical URL
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")

    def get_branch_key(self, url, depth=0):
        """
        Get the branch identifier for a URL.
        At depth 0, this is the seed URL (base domain/path).
        At deeper depths, we group URLs by their parent path structure.
        """
        parsed = urlparse(url)
        path_parts = parsed.path.strip("/").split("/")

        if depth == 0:
            # At root, the branch is the base URL (scheme + netloc + first path segment if any)
            base_path = path_parts[0] if path_parts and path_parts[0] else ""
            return f"{parsed.scheme}://{parsed.netloc}/{base_path}".rstrip("/")

        # For deeper levels, group by parent path to track "subtrees"
        # Take path up to current depth level to identify the branch
        relevant_depth = min(depth, len(path_parts))
        branch_path = (
            "/".join(path_parts[:relevant_depth]) if relevant_depth > 0 else ""
        )
        return f"{parsed.scheme}://{parsed.netloc}/{branch_path}".rstrip("/")

    def should_skip_branch(self, url, depth):
        """
        Check if the current URL branch should be skipped due to low quality.
        Returns True if the branch is abandoned, False otherwise.
        """
        branch_key = self.get_branch_key(url, depth)
        stats = self.branch_stats.get(branch_key)

        if stats is None:
            return False

        if stats.should_skip(depth):
            if not hasattr(stats, "_logged_skip"):
                print(f"  ↳ [SMART SKIP] Abandoning branch '{branch_key}': {stats}")
                stats._logged_skip = True
            return True

        return False

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

        # robots.txt compliance
        if not self.robots_parser.can_fetch(url):
            print(f"  ↳ [ROBOTS] Disallowed: {url}")
            return False

        return bool(parsed.netloc) and normalized not in self.visited

    def crawl(self, url, depth=0, parent_branch=None):
        if self.stop_requested:
            return

        normalized = self.normalize_url(url)
        if depth > self.max_depth or normalized in self.visited:
            return

        # For seed URLs (depth 0), we need to check validity here
        # (Subsequent calls are checked before the recursive call)
        if depth == 0 and not self.is_valid_url(url):
            return

        # Smart tree skipping: check if this branch should be abandoned
        if self.should_skip_branch(url, depth):
            return

        # Get or create branch stats for tracking
        branch_key = self.get_branch_key(url, depth)
        if branch_key not in self.branch_stats:
            self.branch_stats[branch_key] = BranchStats()
        branch_stats = self.branch_stats[branch_key]

        print(
            f"Crawling: {url} (Depth: {depth}, Branch: {branch_key.split('/')[-1] or 'root'})"
        )
        self.visited.add(normalized)

        try:
            html = None

            if self.use_dynamic:
                html = self.fetch_dynamic(url)
                if not html:
                    # Record rejection for failed fetches
                    branch_stats.record_result(depth, accepted=False)
                    return
            else:
                headers = {"User-Agent": config.USER_AGENT}
                response = requests.get(
                    url, timeout=config.CRAWLER_TIMEOUT, headers=headers
                )
                if response.status_code != 200:
                    # Record rejection for failed fetches too
                    branch_stats.record_result(depth, accepted=False)
                    return
                html = response.text

                # Check for indicators that dynamic rendering is needed
                thresholds = config.THRESHOLDS
                needs_dynamic = False
                reason = ""
                html_lower = html.lower()

                if len(html) < thresholds.get("min_static_content_bytes", 1000):
                    reason = f"content too small ({len(html)} bytes < {thresholds.get('min_static_content_bytes', 1000)})"
                    needs_dynamic = True
                elif html_lower.count("<script") > thresholds.get(
                    "max_static_script_tags", 20
                ):
                    reason = f"too many scripts ({html_lower.count('<script')} > {thresholds.get('max_static_script_tags', 20)})"
                    needs_dynamic = True
                elif "<noscript" in html_lower:
                    # If we see <noscript>, the site almost certainly expects JS
                    reason = "found <noscript> tag"
                    needs_dynamic = True

                if needs_dynamic:
                    print(f"  ↳ [AUTO-SWITCH] Switching to dynamic fetch: {reason}")
                    # Try fetch with headless browser
                    dynamic_html = self.fetch_dynamic(url)
                    if dynamic_html:
                        html = dynamic_html
                        print(
                            f"  ✓ [AUTO-SWITCH] Successfully fetched dynamic content ({len(html)} bytes)"
                        )
                    else:
                        print(
                            f"  ✗ [AUTO-SWITCH] Dynamic fetch failed, falling back to static content."
                        )

            # Check page size limit - abandon pages that are too large
            max_size_bytes = config.THRESHOLDS.get("max_page_size_mb", 2) * 1024 * 1024
            page_size = len(html.encode("utf-8"))
            if page_size > max_size_bytes:
                size_mb = page_size / (1024 * 1024)
                max_mb = max_size_bytes / (1024 * 1024)
                print(
                    f"  ↳ [SIZE SKIP] Abandoning {url}: {size_mb:.1f}MB exceeds {max_mb}MB limit"
                )
                branch_stats.record_result(depth, accepted=False)
                self.quality_logger.log_rejection(
                    url,
                    [f"Page too large ({size_mb:.1f}MB)"],
                    {"page_size_mb": round(size_mb, 2)},
                )
                return

            soup = BeautifulSoup(html, "lxml")

            # Check if this is an RSS/JSON feed
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.lower()

            if self.is_rss_or_json_feed(html, url):
                # Track feed-only domains
                if domain not in self.feed_only_domains:
                    self.feed_only_domains[domain] = 0
                self.feed_only_domains[domain] += 1

                # Check if we should auto-blacklist this domain
                if self.check_and_blacklist_feed_domain(domain):
                    branch_stats.record_result(depth, accepted=False)
                    return

                # Reject this specific feed page
                branch_stats.record_result(depth, accepted=False)
                print(f"  ↳ [FEED] Skipping RSS/JSON feed: {url}")
                self.quality_logger.log_rejection(
                    url,
                    ["RSS/JSON feed detected"],
                    {
                        "feed_type": "rss_or_json",
                        "domain_feed_count": self.feed_only_domains[domain],
                    },
                )
                return

            # Extract text and title
            title = soup.title.string if soup.title else url
            text = soup.get_text(separator=" ", strip=True)

            # Check for duplicate content before quality filtering
            content_hash = self.compute_content_hash(text)
            is_duplicate, existing_url = self.is_duplicate_content(content_hash)

            if is_duplicate:
                branch_stats.record_result(depth, accepted=False)
                print(f"  ↳ [DUPLICATE] Skipping {url} (identical to {existing_url})")
                self.quality_logger.log_rejection(
                    url,
                    [f"Duplicate content (same as {existing_url})"],
                    {"content_hash": content_hash, "original_url": existing_url},
                )
                return

            # Quality Filtering
            quality_result = evaluate_page_quality(
                url, html, text, whitelist=self.whitelist
            )

            if quality_result["is_acceptable"]:
                # Record acceptance in branch stats
                branch_stats.record_result(depth, accepted=True)

                self.quality_logger.log_acceptance(url, quality_result["quality_tier"])
                print(f"  ✓ Accepted {url} (Tier: {quality_result['quality_tier']})")
                self.save_page(
                    url,
                    str(title),
                    text,
                    html,
                    quality_result["scores"],
                    quality_result["quality_tier"],
                    content_hash,
                )
                # Reset consecutive rejections on acceptance
                self.consecutive_rejections = 0  # Reset global counter
            else:
                # Record rejection in branch stats
                branch_stats.record_result(depth, accepted=False)

                self.quality_logger.log_rejection(
                    url, quality_result["rejection_reasons"], quality_result["scores"]
                )
                print(
                    f"  ✗ Rejected {url}: {', '.join(quality_result['rejection_reasons'])}"
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

                # Check if branch should be abandoned after this rejection
                if self.should_skip_branch(url, depth):
                    return

            # Find and crawl links
            if depth < self.max_depth:
                for link in soup.find_all("a", href=True):
                    href = str(link["href"])
                    next_url = urljoin(url, href)
                    if self.is_valid_url(next_url):
                        # Use a more responsive loop for stopping
                        if self.stop_requested:
                            break

                        # Check if the new URL would be in an abandoned branch
                        next_branch = self.get_branch_key(next_url, depth + 1)
                        if (
                            next_branch in self.branch_stats
                            and self.branch_stats[next_branch].skipped
                        ):
                            continue  # Skip links to abandoned branches

                        self.crawl(next_url, depth + 1, parent_branch=branch_key)

                        # Responsive delay: check for stop several times during delay
                        for _ in range(int(config.CRAWLER_POLITE_DELAY * 10)):
                            if self.stop_requested:
                                break
                            time.sleep(0.1)
                        if self.stop_requested:
                            break
        except Exception as e:
            print(f"Error crawling {url}: {e}")
            # Record as rejection on error
            if branch_key in self.branch_stats:
                self.branch_stats[branch_key].record_result(depth, accepted=False)

    def save_page(
        self,
        url,
        title,
        content,
        html,
        quality_score=None,
        quality_tier=None,
        content_hash=None,
    ):
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            # Extract unified_score from quality_score dict
            unified_score = None
            if isinstance(quality_score, dict):
                unified_score = quality_score.get("unified_score")
                quality_score_json = json.dumps(quality_score)
            elif isinstance(quality_score, (int, float)):
                unified_score = int(quality_score)
                quality_score_json = str(quality_score)
            else:
                quality_score_json = quality_score

            cursor.execute(
                """INSERT OR REPLACE INTO pages
                    (url, title, content, html, quality_score, quality_tier, unified_score, content_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    url,
                    title,
                    content,
                    html,
                    quality_score_json,
                    quality_tier,
                    unified_score,
                    content_hash,
                ),
            )
            conn.commit()
            conn.close()

            # Also extract and save RSS feeds from this page
            self.extract_and_save_rss_feeds(url, html)

        except sqlite3.Error as e:
            print(f"Error saving to database: {e}")

    def print_branch_summary(self):
        """Print summary of all branches and their outcomes."""
        if not self.branch_stats:
            return

        print("\n" + "=" * 60)
        print("BRANCH CRAWL SUMMARY")
        print("=" * 60)

        # Sort by total crawled (descending) then by acceptance ratio
        sorted_branches = sorted(
            self.branch_stats.items(),
            key=lambda x: (x[1].total_crawled, -x[1].rejection_ratio),
            reverse=True,
        )

        skipped_count = sum(1 for _, stats in sorted_branches if stats.skipped)
        total_pages = sum(stats.total_crawled for _, stats in sorted_branches)
        total_accepted = sum(stats.accepted_count for _, stats in sorted_branches)

        print(f"Total branches tracked: {len(self.branch_stats)}")
        print(f"Branches abandoned (skipped): {skipped_count}")
        print(f"Total pages crawled: {total_pages}")
        print(
            f"Total pages accepted: {total_accepted} ({total_accepted/total_pages:.0%})"
            if total_pages > 0
            else ""
        )
        print("-" * 60)

        # Show top branches by volume
        print("\nTop branches by activity:")
        for branch_key, stats in sorted_branches[:10]:
            status = "[SKIPPED]" if stats.skipped else "[active] "
            acceptance_pct = (
                (stats.accepted_count / stats.total_crawled * 100)
                if stats.total_crawled > 0
                else 0
            )
            # Truncate long branch keys for display
            display_key = (
                branch_key[:50] + "..." if len(branch_key) > 50 else branch_key
            )
            print(f"  {status} {display_key}")
            print(
                f"          {stats.accepted_count}/{stats.total_crawled} accepted ({acceptance_pct:.0f}%), max depth {stats.max_depth_reached}"
            )

        if len(sorted_branches) > 10:
            print(f"  ... and {len(sorted_branches) - 10} more branches")

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

    def extract_and_save_rss_feeds(self, url, html):
        """Extract RSS feeds from HTML and save them to the rss_feeds table."""
        if not html:
            return

        try:
            from datetime import datetime

            soup = BeautifulSoup(html, "lxml")
            domain = urlparse(url).netloc
            feeds_to_add = []

            # Look for RSS/Atom feed links
            for link in soup.find_all("link", rel="alternate"):
                # Ensure we have a string for type and href
                link_type = link.get("type", "")
                if isinstance(link_type, list):
                    link_type = " ".join(link_type)
                link_type = (link_type or "").lower()

                href = link.get("href", "")
                if isinstance(href, list):
                    href = href[0]

                if not href:
                    continue

                full_url = urljoin(url, href)

                # Only include if type is application/rss+xml or URL ends with .xml
                is_rss_type = link_type == "application/rss+xml"
                ends_with_xml = full_url.lower().endswith(".xml")

                if is_rss_type or ends_with_xml:
                    feeds_to_add.append(
                        {
                            "url": full_url,
                            "title": link.get("title", ""),
                            "type": link.get("type", "unknown"),
                            "domain": domain,
                        }
                    )

            if feeds_to_add:
                conn = sqlite3.connect(self.db_file)
                cursor = conn.cursor()

                # Ensure rss_feeds table exists
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

                for feed in feeds_to_add:
                    try:
                        cursor.execute(
                            """
                            INSERT OR IGNORE INTO rss_feeds
                            (url, discovered_from, title, feed_type, source_domain, date_added)
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (
                                feed["url"],
                                url,
                                feed["title"],
                                feed["type"],
                                feed["domain"],
                                datetime.now().isoformat(),
                            ),
                        )
                    except sqlite3.Error:
                        pass

                conn.commit()
                conn.close()

        except Exception:
            pass


def main():
    import argparse

    # Set up argument parser for better CLI experience
    parser = argparse.ArgumentParser(description="Smart Tree Web Crawler")
    parser.add_argument("input", help="URL or file containing URLs to crawl")
    parser.add_argument(
        "depth", type=int, nargs="?", default=1, help="Maximum crawl depth (default: 1)"
    )
    parser.add_argument(
        "--dynamic", action="store_true", help="Use Playwright for JavaScript rendering"
    )
    parser.add_argument(
        "--smart-tree",
        action="store_true",
        default=True,
        help="Enable smart tree branch skipping (default: enabled)",
    )
    parser.add_argument(
        "--no-smart-tree",
        action="store_true",
        help="Disable smart tree branch skipping",
    )
    parser.add_argument(
        "--min-samples",
        type=int,
        default=3,
        help="Minimum samples before branch skip decision (default: 3)",
    )
    parser.add_argument(
        "--rejection-threshold",
        type=float,
        default=0.85,
        help="Rejection ratio threshold for skipping (default: 0.85)",
    )
    parser.add_argument(
        "--depth-threshold",
        type=int,
        default=2,
        help="Minimum depth before checking branch skip (default: 2)",
    )
    parser.add_argument(
        "--max-page-size",
        type=float,
        default=2,
        help="Maximum page size in MB (default: 2)",
    )

    args = parser.parse_args()

    # Override config thresholds with CLI arguments if provided
    if args.min_samples != 3:
        config.THRESHOLDS["branch_min_samples"] = args.min_samples
    if args.rejection_threshold != 0.85:
        config.THRESHOLDS["branch_rejection_ratio"] = args.rejection_threshold
    if args.depth_threshold != 2:
        config.THRESHOLDS["branch_depth_threshold"] = args.depth_threshold
    if args.max_page_size != 2:
        config.THRESHOLDS["max_page_size_mb"] = args.max_page_size

    # Disable smart tree if requested
    if args.no_smart_tree:
        # Set rejection threshold to 1.0 (never skip)
        config.THRESHOLDS["branch_rejection_ratio"] = 1.0
        print("[INFO] Smart tree crawling disabled - will crawl all branches")

    input_arg = args.input
    depth = args.depth
    use_dynamic = args.dynamic

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
            if crawler.stop_requested:
                print(
                    "[SHUTDOWN] Skipping remaining seed URLs due to shutdown request."
                )
                break

            print(f"\n>>> Starting crawl from input URL: {url}")
            print(
                f"[CONFIG] Smart Tree: {'enabled' if args.no_smart_tree == False else 'disabled'}, "
                f"Min Samples: {config.THRESHOLDS.get('branch_min_samples', 3)}, "
                f"Rejection Threshold: {config.THRESHOLDS.get('branch_rejection_ratio', 0.85):.0%}, "
                f"Depth Threshold: {config.THRESHOLDS.get('branch_depth_threshold', 2)}"
            )
            # Reset stop markers for each new seed URL
            crawler.stop_requested = False
            crawler.consecutive_rejections = 0
            # Note: We keep branch_stats across seeds to learn from previous branches
            crawler.crawl(url)
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] KeyboardInterrupt received. Cleaning up...")
        crawler.stop_requested = True
    finally:
        crawler.close_browser()
        crawler.quality_logger.print_summary()
        crawler.print_branch_summary()

    if crawler.stop_requested:
        print("[CRAWL INTERRUPTED - Graceful shutdown completed]")
    else:
        print("[CRAWL COMPLETE]")


if __name__ == "__main__":
    main()
