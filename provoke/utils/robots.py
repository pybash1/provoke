import urllib.robotparser
import requests
import logging
from urllib.parse import urlparse
from provoke.config import config

logger = logging.getLogger(__name__)


class RobotsParser:
    """
    Fetches and caches robots.txt per domain to ensure compliance.
    """

    def __init__(self, user_agent=None):
        self.user_agent = user_agent or config.USER_AGENT
        self.cache = {}  # domain -> RobotFileParser

    def get_parser(self, url):
        """Get the RobotFileParser for the given URL's domain."""
        parsed = urlparse(url)
        if not parsed.netloc:
            return None

        domain = f"{parsed.scheme}://{parsed.netloc}"
        if domain in self.cache:
            return self.cache[domain]

        parser = urllib.robotparser.RobotFileParser()
        robots_url = f"{domain}/robots.txt"

        try:
            headers = {"User-Agent": self.user_agent}
            # Use requests for consistency with the rest of the app
            response = requests.get(
                robots_url, headers=headers, timeout=config.CRAWLER_TIMEOUT
            )

            if response.status_code == 200:
                parser.parse(response.text.splitlines())
            elif response.status_code == 404:
                # 404 means everything is allowed
                parser.parse(["User-agent: *", "Disallow:"])
            elif response.status_code == 401 or response.status_code == 403:
                # 401/403 means everything is disallowed according to some specs
                # but many crawlers are lenient. We'll be strict.
                parser.parse(["User-agent: *", "Disallow: /"])
            else:
                # For other errors (5xx), we could wait or assume allowed.
                # We'll assume allowed but log it.
                parser.parse(["User-agent: *", "Disallow:"])
        except Exception as e:
            # Network errors - safer to assume allowed but log the failure
            parser.parse(["User-agent: *", "Disallow:"])

        self.cache[domain] = parser
        return parser

    def can_fetch(self, url):
        """Check if the given URL can be fetched according to robots.txt."""
        parser = self.get_parser(url)
        if not parser:
            return True

        # We check both the full user agent and the short one (if provided)
        # to be as compliant as possible.
        allowed = parser.can_fetch(self.user_agent, url)

        # If config has a short user agent, check that too
        if allowed and hasattr(config, "USER_AGENT_SHORT"):
            allowed = parser.can_fetch(config.USER_AGENT_SHORT, url)

        return allowed
