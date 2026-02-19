import asyncio
import json
import sqlite3
import redis
import redis.asyncio as aredis
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from provoke.config import config


class IndexerWorker:
    def __init__(self, db_file=None):
        self.db_file = db_file or config.DATABASE_PATH
        self.redis = None
        self.stop_requested = False

    def _get_db_connection(self):
        conn = sqlite3.connect(self.db_file)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    async def run(self):
        """Main loop for the indexer worker."""
        print(f">>> Indexer Worker starting. Listening on {config.REDIS_STREAM}...")

        self.redis = aredis.Redis(
            host=config.REDIS_HOST, port=config.REDIS_PORT, decode_responses=True
        )

        # Ensure consumer group exists
        try:
            await self.redis.xgroup_create(
                config.REDIS_STREAM, config.REDIS_GROUP, id="0", mkstream=True
            )
        except Exception as e:
            if "BUSYGROUP" not in str(e):
                print(f"Error creating consumer group: {e}")
                # We can continue if it already exists

        while not self.stop_requested:
            try:
                # Read from stream
                # COUNT 1: Process one at a time for safety
                # BLOCK 2000: Wait up to 2 seconds if stream is empty
                streams = await self.redis.xreadgroup(
                    config.REDIS_GROUP,
                    config.REDIS_CONSUMER,
                    {config.REDIS_STREAM: ">"},
                    count=1,
                    block=2000,
                )

                if not streams:
                    continue

                for _, messages in streams:
                    for msg_id, data in messages:
                        await self.process_task(msg_id, data)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in indexer worker loop: {e}")
                await asyncio.sleep(1)

        if self.redis:
            await self.redis.close()
        print("Indexer Worker stopped.")

    async def process_task(self, msg_id, data):
        """Process a single indexing task."""
        url = data.get("url")
        print(f"Indexing: {url}")

        try:
            # We run the DB save in a thread to not block the async loop
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: self.save_page(
                    url=url,
                    title=data.get("title"),
                    content=data.get("content"),
                    html=data.get("html"),
                    quality_score=data.get("quality_score"),
                    quality_tier=data.get("quality_tier"),
                    content_hash=data.get("content_hash"),
                ),
            )

            # Ack the message
            if self.redis:
                await self.redis.xack(config.REDIS_STREAM, config.REDIS_GROUP, msg_id)
                # Optional: Delete the message if we don't need history in Redis
                await self.redis.xdel(config.REDIS_STREAM, msg_id)

        except Exception as e:
            print(f"  Error processing task for {url}: {e}")

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
            conn = self._get_db_connection()
            cursor = conn.cursor()

            # quality_score comes as a JSON string from the crawler
            # We want to extract unified_score for the dedicated column
            unified_score = None
            if quality_score:
                try:
                    qs_dict = json.loads(quality_score)
                    if isinstance(qs_dict, dict):
                        unified_score = qs_dict.get("unified_score")
                except (json.JSONDecodeError, TypeError):
                    pass

            cursor.execute(
                """INSERT OR REPLACE INTO pages
                    (url, title, content, html, quality_score, quality_tier, unified_score, content_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    url,
                    title,
                    content,
                    html,
                    quality_score,
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

    def extract_and_save_rss_feeds(self, url, html):
        """Extract RSS feeds from HTML and save them to the rss_feeds table."""
        if not html:
            return

        try:
            soup = BeautifulSoup(html, "lxml")
            domain = urlparse(url).netloc
            feeds_to_add = []

            for link in soup.find_all("link", rel="alternate"):
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
                conn = self._get_db_connection()
                cursor = conn.cursor()
                # Ensure table exists (redundant but safe)
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

        except Exception as e:
            print(f"Error extracting RSS: {e}")


def main():
    worker = IndexerWorker()
    try:
        asyncio.run(worker.run())
    except KeyboardInterrupt:
        worker.stop_requested = True


if __name__ == "__main__":
    main()
