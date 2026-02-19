import asyncio
import aiohttp
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
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
import redis.asyncio as aredis
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


class AsyncCrawler:
    def __init__(self, base_url, max_depth=None, db_file=None, use_dynamic=False):
        self.base_url = base_url
        self.max_depth = (
            max_depth if max_depth is not None else config.CRAWLER_DEFAULT_MAX_DEPTH
        )
        self.db_file = db_file or config.DATABASE_PATH
        self.use_dynamic = use_dynamic
        self.init_db()
        self.visited = set()
        self.playwright = None
        self.browser = None
        self.session = None  # aiohttp session
        self.quality_logger = QualityLogger()
        self.blacklist = self.get_blacklisted_domains()
        self.whitelist = self.get_whitelisted_domains()
        self.domain_rejections = {}
        self.consecutive_rejections = 0
        self.stop_requested = False
        self.branch_stats = {}
        self.robots_parser = RobotsParser(user_agent=config.USER_AGENT)
        self.feed_only_domains = {}
        self.queue = asyncio.Queue()
        self.active_workers = 0
        self.redis = None

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def _handle_signal(self, signum, frame):
        """Signal handler to trigger graceful shutdown."""
        sig_name = "SIGINT" if signum == signal.SIGINT else "SIGTERM"
        print(f"\n[SIGNL] Received {sig_name}. Requesting graceful shutdown...")
        self.stop_requested = True

    def _get_db_connection(self):
        conn = sqlite3.connect(self.db_file)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def init_db(self):
        conn = self._get_db_connection()
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
            conn = self._get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT domain FROM blacklisted_domains")
            domains = {row[0] for row in cursor.fetchall()}
            conn.close()
            return domains
        except sqlite3.Error:
            return set()

    def get_whitelisted_domains(self):
        try:
            conn = self._get_db_connection()
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
            conn = self._get_db_connection()
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
            conn = self._get_db_connection()
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

    async def start_session(self):
        """Initialize async resources."""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=config.CRAWLER_TIMEOUT)
            self.session = aiohttp.ClientSession(
                headers={"User-Agent": config.USER_AGENT}, timeout=timeout
            )

        if self.use_dynamic and not self.browser:
            print("Starting headless browser for dynamic content (Async)...")
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=True)

        if not self.redis:
            self.redis = aredis.Redis(
                host=config.REDIS_HOST, port=config.REDIS_PORT, decode_responses=True
            )

    async def close_session(self):
        """Clean up async resources."""
        if self.session:
            await self.session.close()
            self.session = None
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.redis:
            await self.redis.close()
            self.redis = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None

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

    def is_likely_dynamic(self, url: str, html: str | None = None) -> bool:
        """Check if URL requires dynamic rendering via heuristics."""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # 1. Domain-level check
        if any(d in domain for d in config.DYNAMIC_DOMAINS):
            return True

        # 2. Content check (if available)
        if html:
            # Check for known SPA indicators
            if any(indicator in html for indicator in config.DYNAMIC_INDICATORS):
                return True

            # Threshold-based detection from auto-switch feature
            thresholds = config.THRESHOLDS
            html_lower = html.lower()

            # Logic 1: Size-based. If static content is unusually small, it's likely an SPA shell.
            if len(html) < thresholds.get("min_static_content_bytes", 1000):
                return True

            # Logic 2: Script-density. High script count often indicates a complex app.
            if html_lower.count("<script") > thresholds.get(
                "max_static_script_tags", 20
            ):
                return True

            # Logic 3: Explicit <noscript> tag is a strong indicator of JS requirement.
            if "<noscript" in html_lower:
                return True

        return False

    async def fetch_page(self, url: str) -> tuple[str | None, bool]:
        """
        Fetch page content using best strategy.
        Returns (html_content, used_dynamic).
        """
        html = None
        used_dynamic = False

        # Strategy 1: If domain is known dynamic, go straight to Playwright
        if self.use_dynamic and self.is_likely_dynamic(url):
            try:
                html = await self.fetch_dynamic(url)
                if html:
                    return html, True
            except Exception as e:
                print(f"  Dynamic fetch failed for {url}: {e}")
                # Fallback to static if dynamic fails? Or just fail.
                # Usually dynamic failure means timeout or error, unlikely static works better if it's SPA.

        # Strategy 2: Fast static fetch first
        try:
            if not self.session:
                await self.start_session()

            if self.session:
                async with self.session.get(url) as response:
                    if response.status != 200:
                        return None, False
                    html = await response.text()
            else:
                return None, False
        except Exception as e:
            # If static fails, maybe try dynamic as last resort if configured?
            # print(f"Static fetch failed: {e}")
            return None, False

        # Strategy 3: Check if static content signals need for dynamic render
        if self.use_dynamic and self.is_likely_dynamic(url, html):
            print(
                f"  Detected dynamic content signals for {url}, upgrading to Playwright..."
            )
            try:
                dynamic_html = await self.fetch_dynamic(url)
                if dynamic_html:
                    return dynamic_html, True
            except Exception as e:
                print(f"  Upgrade to dynamic failed: {e}, keeping static content.")

        return html, False

    async def fetch_dynamic(self, url):
        if not self.browser:
            await self.start_session()

        if not self.browser:
            return None

        page = await self.browser.new_page()
        try:
            await page.goto(
                url, wait_until="networkidle", timeout=config.DYNAMIC_PAGE_TIMEOUT
            )
            # Wait a bit more for rendering
            await asyncio.sleep(config.DYNAMIC_RENDER_WAIT)
            content = await page.content()
            return content
        finally:
            await page.close()

    async def process_url(self, url, depth, parent_branch=None):
        """Process a single URL."""
        normalized = self.normalize_url(url)

        # Re-check visited (in case another worker added it)
        if normalized in self.visited:
            return

        # Basic validity checks
        if not self.is_valid_url(url):
            return

        # Smart tree skipping check
        if self.should_skip_branch(url, depth):
            return

        # Branch stats setup
        branch_key = self.get_branch_key(url, depth)
        if branch_key not in self.branch_stats:
            self.branch_stats[branch_key] = BranchStats()
        branch_stats = self.branch_stats[branch_key]

        print(
            f"Crawling: {url} (Depth: {depth}, Branch: {branch_key.split('/')[-1] or 'root'})"
        )
        self.visited.add(normalized)

        try:
            html, used_dynamic = await self.fetch_page(url)

            if not html:
                branch_stats.record_result(depth, accepted=False)
                return

            # CPU-intensive parsing - run in thread executor to not block loop
            loop = asyncio.get_running_loop()
            max_size_bytes = config.THRESHOLDS.get("max_page_size_mb", 2) * 1024 * 1024
            if len(html.encode("utf-8")) > max_size_bytes:
                branch_stats.record_result(depth, accepted=False)
                return

            # Parse and Evaluate
            # We run the heavy lifting in a thread
            def analyze_content():
                soup = BeautifulSoup(html, "lxml")

                # RSS Check
                if self.is_rss_or_json_feed(html, url):
                    # ... handle feed logic ...
                    return "FEED", None

                title = soup.title.string if soup.title else url
                text = soup.get_text(separator=" ", strip=True)

                content_hash = self.compute_content_hash(text)
                is_dup, existing = self.is_duplicate_content(content_hash)

                if is_dup:
                    return "DUPLICATE", existing

                quality_result = evaluate_page_quality(
                    url, html, text, whitelist=self.whitelist
                )
                return "OK", (title, text, content_hash, quality_result)

            result_type, data = await loop.run_in_executor(None, analyze_content)

            if result_type == "FEED":
                # Handle feed (simplified logic for async)
                # We need to update feed_only_domains and potentially blacklist
                # This affects shared state (feed_only_domains), might need lock if strictly parallel,
                # but dict operations are atomic in GIL, so it's mostly fine.
                parsed = urlparse(url)
                domain = parsed.netloc.lower()
                self.feed_only_domains[domain] = (
                    self.feed_only_domains.get(domain, 0) + 1
                )
                if self.check_and_blacklist_feed_domain(domain):
                    pass
                branch_stats.record_result(depth, accepted=False)
                return

            elif result_type == "DUPLICATE":
                branch_stats.record_result(depth, accepted=False)
                return

            elif result_type == "OK" and isinstance(data, tuple):
                title, text, content_hash, quality_result = data

                if quality_result.get("is_acceptable"):
                    branch_stats.record_result(depth, accepted=True)
                    self.quality_logger.log_acceptance(
                        url, quality_result.get("quality_tier", "unknown")
                    )
                    print(
                        f"  ✓ Accepted {url} (Tier: {quality_result.get('quality_tier', 'unknown')})"
                    )

                    # Enqueue for indexing via Redis Stream (Decoupled)
                    await self.enqueue_indexing_task(
                        {
                            "url": url,
                            "title": str(title),
                            "content": text,
                            "html": html,
                            "quality_score": json.dumps(quality_result.get("scores")),
                            "quality_tier": quality_result.get("quality_tier"),
                            "content_hash": content_hash,
                            "timestamp": datetime.now().isoformat(),
                        }
                    )
                    self.consecutive_rejections = 0
                else:
                    branch_stats.record_result(depth, accepted=False)
                    self.quality_logger.log_rejection(
                        url,
                        quality_result.get("rejection_reasons", []),
                        quality_result.get("scores", {}),
                    )
                    reasons = quality_result.get(
                        "rejection_reasons", ["Low quality score"]
                    )
                    print(f"  ✗ Rejected {url}: {', '.join(reasons)}")

                    # Track rejections
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

                    self.consecutive_rejections += 1
                    if (
                        self.consecutive_rejections
                        >= config.THRESHOLDS["consecutive_rejection_threshold"]
                    ):
                        print(
                            "!!! GLOBAL consecutive rejection threshold hit. Stopping crawl. !!!"
                        )
                        self.stop_requested = True

                    if self.should_skip_branch(url, depth):
                        return

            # Enqueue links
            if depth < self.max_depth and not self.stop_requested:
                # Extract links (soup is needed)
                # We can re-parse or return soup from analyze_content.
                # For simplicity, let's just re-parse or extract in analyze_content.
                # Let's extract links in analyze_content to save CPU
                pass
                # Actually, extracting links is fast enough.
                # But we need soup.
                soup = BeautifulSoup(html, "lxml")
                for link in soup.find_all("a", href=True):
                    href = str(link["href"])
                    next_url = urljoin(url, href)
                    if self.is_valid_url(next_url):
                        next_branch = self.get_branch_key(next_url, depth + 1)
                        if (
                            next_branch in self.branch_stats
                            and self.branch_stats[next_branch].skipped
                        ):
                            continue
                        await self.queue.put((next_url, depth + 1))

        except Exception as e:
            print(f"Error processing {url}: {e}")
            branch_stats.record_result(depth, accepted=False)

    async def worker(self):
        while True:
            try:
                if self.stop_requested:
                    # Drain queue
                    try:
                        while True:
                            self.queue.get_nowait()
                            self.queue.task_done()
                    except asyncio.QueueEmpty:
                        pass
                    break

                # Get item from queue
                try:
                    url, depth = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    if self.active_workers == 0 and self.queue.empty():
                        # No more work
                        break
                    continue
                except asyncio.QueueEmpty:
                    continue

                self.active_workers += 1
                try:
                    if depth <= self.max_depth and not self.stop_requested:
                        await self.process_url(url, depth)
                finally:
                    self.queue.task_done()
                    self.active_workers -= 1

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Worker error: {e}")

    async def run(self, seed_urls: list[str]):
        """Run the async crawler."""
        await self.start_session()
        try:
            for url in seed_urls:
                if self.stop_requested:
                    break
                # Reset per-seed counters if needed, but we keep history
                self.consecutive_rejections = 0
                await self.queue.put((url, 0))

            # Start workers
            workers = [
                asyncio.create_task(self.worker())
                for _ in range(config.CRAWLER_CONCURRENCY)
            ]

            # Wait for queue to be fully processed
            await self.queue.join()

            # Cancel workers
            for w in workers:
                w.cancel()
            await asyncio.gather(*workers, return_exceptions=True)

        finally:
            await self.close_session()

    def crawl(self, url, depth=0, parent_branch=None):
        # shim for backward compatibility if needed, but we should use run()
        pass

    async def enqueue_indexing_task(self, data: dict):
        """Push crawl results to Redis Stream for the indexer worker."""
        if not self.redis:
            await self.start_session()

        if self.redis:
            try:
                # XADD inked:crawl_results * url ... title ...
                # Redis Stream entries are key-value pairs
                await self.redis.xadd(config.REDIS_STREAM, data)
            except Exception as e:
                print(f"  Error enqueuing indexing task: {e}")
        else:
            print("  Error: Redis not initialized.")

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
                conn = self._get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR IGNORE INTO blacklisted_domains (domain) VALUES (?)",
                    (domain,),
                )
                conn.commit()
                conn.close()
            except sqlite3.Error as e:
                print(f"Error blacklisting domain: {e}")


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
    crawler = AsyncCrawler(urls_to_crawl[0], max_depth=depth, use_dynamic=use_dynamic)
    try:
        print(f"\n>>> Starting ASYNC crawl using {config.CRAWLER_CONCURRENCY} workers")
        print(
            f"[CONFIG] Smart Tree: {'enabled' if args.no_smart_tree == False else 'disabled'}, "
            f"Min Samples: {config.THRESHOLDS.get('branch_min_samples', 3)}, "
            f"Rejection Threshold: {config.THRESHOLDS.get('branch_rejection_ratio', 0.85):.0%}, "
            f"Depth Threshold: {config.THRESHOLDS.get('branch_depth_threshold', 2)}"
        )

        asyncio.run(crawler.run(urls_to_crawl))

    except KeyboardInterrupt:
        print("\n[SHUTDOWN] KeyboardInterrupt received. Cleaning up...")
        crawler.stop_requested = True
    finally:
        crawler.quality_logger.print_summary()
        crawler.print_branch_summary()

    if crawler.stop_requested:
        print("[CRAWL INTERRUPTED - Graceful shutdown completed]")
    else:
        print("[CRAWL COMPLETE]")


if __name__ == "__main__":
    main()
