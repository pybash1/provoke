import os
import re
import logging
from urllib.parse import urlparse
from provoke.config import config

logger = logging.getLogger(__name__)


class AdBlocker:
    """
    Loads and manages comprehensive ad-script blacklists from external files.
    Supports simple domains, wildcards, and regex patterns.
    """

    def __init__(self, ad_list_paths=None):
        self.domains = set()
        self.regexes = []

        if ad_list_paths:
            for path in ad_list_paths:
                self.load_ad_list(path)

        # Add the default small list from config for immediate baseline
        for domain in getattr(config, "BLACKLISTED_AD_SCRIPTS", []):
            self.domains.add(domain.lower())

    def load_ad_list(self, path):
        """Loads a text file where each line is a domain, wildcard, or regex."""
        if not os.path.exists(path):
            logger.warning(f"Ad list file not found: {path}")
            return

        added_count = 0
        try:
            with open(path, "r", encoding="utf-8") as f:
                # Skip the first line (header, e.g., [Adblock Plus])
                next(f, None)

                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments (starting with ! or #)
                    if not line or line.startswith("!") or line.startswith("#"):
                        continue

                    # Handle common formats

                    # 1. AdBlock Plus / DNS Filter Syntax (e.g., ||domain.com^)
                    if line.startswith("||") and line.endswith("^"):
                        domain = line[2:-1].lower()
                        self.domains.add(domain)
                        added_count += 1
                        continue

                    # 2. Regex (e.g., /.../)
                    if line.startswith("/") and line.endswith("/"):
                        try:
                            self.regexes.append(re.compile(line[1:-1], re.IGNORECASE))
                            added_count += 1
                        except re.error:
                            logger.error(f"Invalid regex in ad list: {line}")
                    # 3. Wildcards (e.g., *.doubleclick.net)
                    elif "*" in line:
                        pattern = re.escape(line).replace(r"\*", ".*")
                        self.regexes.append(re.compile(f"^{pattern}$", re.IGNORECASE))
                        added_count += 1
                    # 4. Plain domains
                    else:
                        self.domains.add(line.lower())
                        added_count += 1

            logger.info(f"Loaded {added_count} patterns from {path}")
        except Exception as e:
            logger.error(f"Error loading ad list {path}: {e}")

    def is_ad_url(self, url):
        """Checks if a URL (src/href) matches any ad pattern."""
        if not url:
            return False

        url_lower = url.lower()
        parsed = urlparse(url_lower)
        netloc = parsed.netloc

        # 1. Fast exact domain/subdomain check
        if netloc:
            parts = netloc.split(".")
            for i in range(len(parts) - 1):
                check_domain = ".".join(parts[i:])
                if check_domain in self.domains:
                    return True

        # 2. Regex checks (slower, but covers wildcards/paths)
        for regex in self.regexes:
            if regex.search(url_lower):
                return True

        return False


# Global instance for easy access
_ad_blocker = None


def get_ad_blocker():
    global _ad_blocker
    if _ad_blocker is None:
        # Look for default adlist file in data dir
        default_path = os.path.join(config.DATA_DIR, "adlist.txt")
        paths = []
        if os.path.exists(default_path):
            paths.append(default_path)

        _ad_blocker = AdBlocker(paths)
    return _ad_blocker
