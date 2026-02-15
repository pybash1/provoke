"""
Centralized configuration for the Provoke Search Engine.

All application settings are consolidated here. Individual modules should
import from this file instead of defining their own constants or paths.

Supports environment-based overrides via the PROVOKE_ENV environment variable:
  - "development" (default): debug mode, verbose logging
  - "production": optimized settings, no debug

Usage:
    from provoke.config import config
    db_path = config.DATABASE_PATH
"""

import os
import re
from urllib.parse import urlparse
import warnings
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
import textstat

# Suppress the XMLParsedAsHTMLWarning which triggers when BeautifulSoup
# encounters RSS feeds or XML-like content while using the lxml HTML parser.
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _env(key: str, default: str = "") -> str:
    """Read an environment variable with a fallback default."""
    return os.environ.get(key, default)


def _env_bool(key: str, default: bool = False) -> bool:
    """Read a boolean environment variable (truthy: 1, true, yes)."""
    val = os.environ.get(key, "")
    if not val:
        return default
    return val.strip().lower() in ("1", "true", "yes")


def _env_int(key: str, default: int = 0) -> int:
    """Read an integer environment variable with a fallback."""
    val = os.environ.get(key, "")
    if not val:
        return default
    try:
        return int(val)
    except ValueError:
        return default


def _env_float(key: str, default: float = 0.0) -> float:
    """Read a float environment variable with a fallback."""
    val = os.environ.get(key, "")
    if not val:
        return default
    try:
        return float(val)
    except ValueError:
        return default


# ---------------------------------------------------------------------------
# Base Configuration
# ---------------------------------------------------------------------------


class _BaseConfig:
    """
    All settings live as class attributes for easy dot-access.
    Subclasses override per-environment values.
    """

    # ── Environment ───────────────────────────────────────────────────────
    ENV: str = _env("PROVOKE_ENV", "development")

    # ── Server ────────────────────────────────────────────────────────────
    SERVER_HOST: str = _env("PROVOKE_HOST", "127.0.0.1")
    SERVER_PORT: int = _env_int("PROVOKE_PORT", 4000)
    SERVER_DEBUG: bool = True

    # ── File Paths ────────────────────────────────────────────────────────
    _PROJECT_ROOT: str = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    DATABASE_PATH: str = _env(
        "PROVOKE_DB_PATH", os.path.join(_PROJECT_ROOT, "index.db")
    )
    QUALITY_STATS_CSV: str = os.path.join(_PROJECT_ROOT, "quality_stats.csv")
    REJECTED_URLS_LOG: str = os.path.join(_PROJECT_ROOT, "rejected_urls.log")
    LABEL_CSV: str = os.path.join(_PROJECT_ROOT, "data/to_label.csv")
    LABEL_DONE_CSV: str = os.path.join(_PROJECT_ROOT, "data/to_label_done.csv")
    TRAINING_DATA_FILE: str = os.path.join(_PROJECT_ROOT, "data/training_data.txt")
    TRAIN_SPLIT_FILE: str = os.path.join(_PROJECT_ROOT, "data/train.txt")
    TEST_SPLIT_FILE: str = os.path.join(_PROJECT_ROOT, "data/test.txt")
    DATA_DIR: str = os.path.join(_PROJECT_ROOT, "data")
    MODELS_DIR: str = os.path.join(_PROJECT_ROOT, "models")
    ADLIST_PATH: str = os.path.join(DATA_DIR, "adlist.txt")

    # ── HTTP / User-Agent ─────────────────────────────────────────────────
    USER_AGENT: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/91.0.4472.124 Safari/537.36"
    )
    USER_AGENT_SHORT: str = "Mozilla/5.0"
    HTTP_TIMEOUT: int = 10  # Default timeout for HTTP requests (seconds)
    CRAWLER_TIMEOUT: int = 5  # Timeout for crawler fetch requests (seconds)
    DYNAMIC_PAGE_TIMEOUT: int = 30000  # Playwright page.goto timeout (ms)
    DYNAMIC_RENDER_WAIT: float = 1.0  # Extra wait for SPA rendering (seconds)

    # ── Crawler ───────────────────────────────────────────────────────────
    CRAWLER_DEFAULT_MAX_DEPTH: int = 2
    CRAWLER_POLITE_DELAY: float = 0.1  # Delay between crawled URLs (seconds)

    # ── Quality Thresholds ────────────────────────────────────────────────
    THRESHOLDS: dict = {
        "min_text_ratio": 0.1,
        "min_words": 100,
        "max_words": 8000,
        "corporate_score_threshold": 10,
        "min_personal_signals_if_corporate": 3,
        "ideal_readability_min": 60,
        "ideal_readability_max": 80,
        "min_readability": 0,
        "max_readability": 120,
        "domain_rejection_threshold": 30,
        "consecutive_rejection_threshold": 25,
        "unified_score_threshold": 40,
        "high_quality_threshold": 80,
        # Smart tree skipping: abandon unproductive URL branches
        "branch_depth_threshold": 2,  # Min depth before considering skip
        "branch_rejection_ratio": 0.85,  # Rejection ratio to trigger skip (0.0-1.0)
        "branch_min_samples": 3,  # Min pages crawled before evaluating branch
        "branch_acceptance_bonus": 2,  # Bonus accepted pages to give new branches a chance
        # Page size limits: abandon pages that are too large (in bytes)
        "max_page_size_mb": 2,  # Maximum page size in MB (2MB = ~2 million characters)
        # RSS/JSON feed auto-blacklisting
        "feed_only_domain_threshold": 5,  # Number of feeds before auto-blacklisting domain
    }

    # ── ML Settings ───────────────────────────────────────────────────────
    ML_CONFIG: dict = {
        "enabled": True,
        "model_path": "models/content_classifier.bin",
        "high_confidence_threshold": 0.7,
        "low_confidence_threshold": 0.3,
    }

    # ML Training Hyper-parameters
    ML_LEARNING_RATE: float = 0.7
    ML_EPOCHS: int = 25
    ML_WORD_NGRAMS: int = 2
    ML_EMBEDDING_DIM: int = 100
    ML_VERBOSE: int = 2
    ML_TEST_RATIO: float = 0.25
    ML_CONFIDENCE_THRESHOLD: float = 0.8  # For check_model_stats analysis

    # ML Training Data Export
    ML_EXPORT_LIMIT: int = 500
    ML_EXPORT_DB_RATIO: float = 0.4  # 40% from DB, rest from rejected

    # ── Excluded Title Patterns ───────────────────────────────────────────
    EXCLUDED_TITLE_PATTERNS: list = [
        r"privacy\s+policy",
        r"terms\s+of\s+use",
        r"terms\s+of\s+service",
        r"legal\s+notice",
        r"legal",
        r"cookie\s+policy",
        r"cookies",
        r"^home\s*[-\|]",
        r"\blogin\b",
        r"\bsign\s+up\b",
        r"\bsign\s+in\b",
        r"\bregister\b",
        r"auth",
        r"about us",
        r"release notes",
        r"forum",
        r"changelog",
    ]

    # ── Excluded URL Patterns ─────────────────────────────────────────────
    EXCLUDED_URL_PATTERNS: list = [
        r"/tag/",
        r"/category/",
        r"/categories/",
        r"/search/",
        r"/archive/",
        r"/archives/",
        r"/feed/",
        r"/user/",
        r"/users/",
        r"/xmlrpc\.php",
        r"/wp-json/",
        r"\?p=\d+",
        r"\?s=",
        r"\?cat=",
        r"\?tag=",
        # Documentation & Technical Reference
        r"^https?://docs\.",
        r"^https?://api\.",
        r"^https?://developer\.",
        r"^https?://support\.",
        r"^https?://help\.",
        r"/docs/",
        r"/documentation/",
        r"/docs-",
        r"/api-docs/",
        r"/reference/",
        r"/manual/",
        r"/guide/",
        r"/wiki/",
        r"/installation",
        r"/setup",
        r"/getting-started",
        # Explicit user-requested or obvious non-article domains
        r"macports\.org",
        r"brew\.sh",
        r"npmbuilds\.com",
        r"crates\.io",
        r"pypi\.org",
    ]

    # ── CTA / Marketing ───────────────────────────────────────────────────
    CTA_PHRASES: list = [
        "free trial",
        "book a demo",
        "contact sales",
        "get started",
        "request demo",
        "schedule a call",
        "talk to sales",
        "release notes",
    ]

    MARKETING_TOOLS: list = [
        "hubspot",
        "marketo",
        "pardot",
        "clearbit",
        "intercom",
        "drift",
        "calendly",
        "6sense",
    ]

    # ── Ad Networks ───────────────────────────────────────────────────────
    AD_NETWORKS: list = [
        "doubleclick",
        "adsense",
        "taboola",
        "outbrain",
        "advertising.com",
        "ad-server",
        "googletagservices",
        "googletagmanager",
        "amazon-adsystem",
        "adnxs",
        "criteo",
        "openx",
        "rubiconproject",
        "pubmatic",
        "casalemedia",
        "yieldmo",
        "triplelift",
        "indexww",
        "adform",
        "smartadserver",
        "revcontent",
        "mgid",
        "buysellads",
        "carbonads",
        "media.net",
        "adroll",
    ]

    # ── Tracking Scripts ──────────────────────────────────────────────────
    TRACKING_SCRIPTS: list = [
        r"fbq\(",
        r"gtag\(",
        r"pixel\.gif",
        r"tracking",
        r"quantserve",
        r"scorecardresearch",
        r"fullstory",
        r"hotjar",
        r"crazyegg",
        r"mixpanel",
        r"segment\.io",
        r"amplitude",
        r"pendo",
        r"intercom-track",
        r"drift-track",
        r"luckyorange",
    ]

    # ── Ad Element Patterns ───────────────────────────────────────────────
    AD_ELEMENT_PATTERNS: list = [
        r"ad-slot",
        r"ad-container",
        r"ad-wrapper",
        r"banner-ads",
        r"sponsored-content",
        r"promoted-item",
        r"adsbygoogle",
        r"gpt-ad",
        r"dfp-ad",
        r"native-ad",
        r"sidebar-ad",
        r"bottom-ad",
    ]

    # ── Ad Script Blacklist (Hard Rejection) ──────────────────────────────
    # Domains that, if found in <script src="..."> or <link href="...">,
    # trigger immediate rejection.
    BLACKLISTED_AD_SCRIPTS: list = [
        "doubleclick.net",
        "googleadservices.com",
        "googlesyndication.com",
        "adnxs.com",
        "taboola.com",
        "outbrain.com",
        "amazon-adsystem.com",
        "adform.net",
        "adroll.com",
        "criteo.com",
        "rubiconproject.com",
        "pubmatic.com",
        "openx.net",
        "yieldmo.com",
        "triplelift.com",
        "indexww.com",
        "smartadserver.com",
        "revcontent.com",
        "mgid.com",
        "buysellads.com",
        "carbonads.net",
        "ad-server.org",
        "mads.microsoft.com",
        "quantserve.com",
        "scorecardresearch.com",
    ]

    # ── Personal Blog Signals ─────────────────────────────────────────────
    PERSONAL_DOMAIN_KEYWORDS: list = [
        "blog",
        "personal",
        "me",
        "notes",
        "thoughts",
        "journal",
    ]

    # ── Binary Extensions (skip during crawl) ─────────────────────────────
    BINARY_EXTENSIONS: set = {
        # Images
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".bmp",
        ".webp",
        ".svg",
        ".ico",
        ".tiff",
        # Video
        ".mp4",
        ".m4v",
        ".mov",
        ".avi",
        ".wmv",
        ".flv",
        ".mkv",
        ".webm",
        ".mpg",
        ".mpeg",
        # Audio
        ".mp3",
        ".wav",
        ".m4a",
        ".ogg",
        ".flac",
        ".aac",
        ".wma",
        # Archives
        ".zip",
        ".rar",
        ".7z",
        ".tar",
        ".gz",
        ".bz2",
        ".xz",
        # Documents (excluding PDF)
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        ".rtf",
        # System
        ".exe",
        ".dll",
        ".so",
        ".dmg",
        ".iso",
        ".bin",
        ".msi",
    }


# ---------------------------------------------------------------------------
# Environment Overrides
# ---------------------------------------------------------------------------


class _DevelopmentConfig(_BaseConfig):
    """Development-specific overrides (default)."""

    ENV = "development"
    SERVER_DEBUG = True


class _ProductionConfig(_BaseConfig):
    """Production-specific overrides."""

    ENV = "production"
    SERVER_DEBUG = False
    ML_VERBOSE = 0


# ---------------------------------------------------------------------------
# Config Selector
# ---------------------------------------------------------------------------

_CONFIGS = {
    "development": _DevelopmentConfig,
    "production": _ProductionConfig,
}

_active_env = _env("PROVOKE_ENV", "development").lower()
config: _BaseConfig = _CONFIGS.get(_active_env, _DevelopmentConfig)()

# ---------------------------------------------------------------------------
# Convenience re-exports (backwards compatibility with quality_config.py)
# ---------------------------------------------------------------------------
# These allow existing `from config import THRESHOLDS` style imports to work.

THRESHOLDS = config.THRESHOLDS
ML_CONFIG = config.ML_CONFIG
EXCLUDED_TITLE_PATTERNS = config.EXCLUDED_TITLE_PATTERNS
EXCLUDED_URL_PATTERNS = config.EXCLUDED_URL_PATTERNS
CTA_PHRASES = config.CTA_PHRASES
MARKETING_TOOLS = config.MARKETING_TOOLS
AD_NETWORKS = config.AD_NETWORKS
TRACKING_SCRIPTS = config.TRACKING_SCRIPTS
AD_ELEMENT_PATTERNS = config.AD_ELEMENT_PATTERNS
PERSONAL_DOMAIN_KEYWORDS = config.PERSONAL_DOMAIN_KEYWORDS
BINARY_EXTENSIONS = config.BINARY_EXTENSIONS
BLACKLISTED_AD_SCRIPTS = config.BLACKLISTED_AD_SCRIPTS


# ---------------------------------------------------------------------------
# Quality Filter Logic (Moved from quality_filter.py)
# ---------------------------------------------------------------------------

# Common English stopwords to help identify natural language content
STOPWORDS = {
    "the",
    "and",
    "a",
    "of",
    "to",
    "is",
    "in",
    "it",
    "i",
    "that",
    "you",
    "it",
    "for",
    "on",
    "was",
    "with",
    "as",
    "are",
    "by",
    "be",
    "this",
    "had",
    "from",
    "at",
    "which",
    "or",
    "have",
    "an",
    "they",
    "which",
    "one",
    "you",
    "were",
    "her",
    "all",
    "she",
    "there",
    "would",
    "their",
    "we",
    "him",
    "been",
    "has",
    "when",
    "who",
    "will",
    "no",
    "if",
    "out",
    "so",
    "up",
    "can",
    "their",
    "about",
    "more",
    "some",
    "my",
    "into",
    "their",
    "only",
    "other",
    "them",
    "then",
    "now",
}


def calculate_text_ratio(html_content: str) -> float:
    """
    Calculates an adjusted ratio of meaningful text to HTML weight.
    Incorporates link density penalties and language signals (stopwords).
    """
    if not html_content:
        return 0.0

    soup = BeautifulSoup(html_content, "lxml")
    body = soup.body if soup.body else soup

    # 1. Strip definitely non-content tags from both numerator and denominator
    tags_to_strip = [
        "script",
        "style",
        "svg",
        "path",
        "canvas",
        "video",
        "audio",
        "iframe",
        "comment",
        "nav",
        "header",
        "footer",
        "noscript",
        "meta",
        "link",
        "aside",
        "form",
        "dialog",
        "button",
        "select",
        "input",
        "textarea",
        "label",
        "img",
        "picture",
        "head",
    ]
    for element in body(tags_to_strip):
        element.decompose()

    # 2. Extract texts
    all_text = body.get_text(separator=" ", strip=True)
    if not all_text:
        return 0.0

    # Calculate link text length to determine Link Density
    links = body.find_all("a")
    link_text = " ".join([a.get_text(strip=True) for a in links])

    total_len = len(all_text)
    link_len = len(link_text)

    # Link density (ratio of text that is links)
    # High link density is a strong signal for menus/directories
    link_density = link_len / total_len if total_len > 0 else 0

    # 3. Calculate HTML size (denominator)
    # We use the cleaned structure weight
    content_html = str(body)
    content_html_size = len(content_html)

    if content_html_size == 0:
        return 0.0

    # Raw ratio: visible characters / total markup+text characters
    raw_ratio = total_len / content_html_size

    # 4. Stopword Density (Language quality signal)
    # Natural language has a predictable density of common small words.
    words = all_text.lower().split()
    word_count = len(words)
    stopword_count = sum(1 for w in words if w in STOPWORDS)
    stopword_density = stopword_count / word_count if word_count > 0 else 0

    # 5. Perfect the ratio with adjustments

    # Link Penalty: Penalize pages where text is mostly clickable navigation.
    # Linear penalty: if link_density is 0.5, we cut the ratio in half.
    link_penalty = 1.0 - link_density

    # Stopword Factor: Confirm this is natural language and not a data dump.
    # Standard English articles are usually ~25-30% stopwords.
    # If density is low (< 0.15), it's likely a list of nouns or code.
    # We use a factor that caps at 1.1 and drops to 0.2 for low density.
    stopword_factor = min(1.1, max(0.2, stopword_density * 4))

    # Length Scaling: Moderate penalty for tiny snippets that look "dense" but lack substance.
    min_words = config.THRESHOLDS.get("min_words", 100)
    length_factor = min(1.0, max(0.1, word_count / (min_words * 0.8)))

    # Final adjusted ratio
    adjusted_ratio = raw_ratio * link_penalty * stopword_factor * length_factor

    return min(1.0, float(adjusted_ratio))


def calculate_ad_score(html: str) -> tuple[int, int]:
    """
    Calculates an 'ad score' (0-100) based on detected ad/tracking tech.
    Higher score means more ad-heavy.
    """
    if not html:
        return 0, 0

    points = 0
    html_lower = html.lower()
    soup = BeautifulSoup(html, "lxml")

    from provoke.utils.adblock import get_ad_blocker

    ad_blocker = get_ad_blocker()

    # 1. Check for specific domains/networks in src/href (Precision)
    networks_found = set()

    # Check scripts
    for script in soup.find_all("script", src=True):
        src = str(script["src"]).lower()
        if ad_blocker.is_ad_url(src):
            networks_found.add("blacklisted_ad_script")
            points += 25  # High weight for blocked scripts

        for network in config.AD_NETWORKS:
            if network in src:
                networks_found.add(network)
                points += 15  # Higher weight for actual script tags

    # Check links/iframes
    for tag in soup.find_all(["link", "iframe", "a"], href=True):
        href = str(tag.get("href", "")).lower()
        if ad_blocker.is_ad_url(href):
            networks_found.add("blacklisted_ad_link")
            points += 10

        for network in config.AD_NETWORKS:
            if network in href:
                networks_found.add(network)
                points += 5

    # 2. Check for tracking patterns in whole HTML (Breadth)
    trackers_found = 0
    for pattern in config.TRACKING_SCRIPTS:
        if re.search(pattern, html_lower):
            trackers_found += 1
            points += 5

    # 3. Check for specific ad elements in HTML structure
    for pattern in config.AD_ELEMENT_PATTERNS:
        matches = re.findall(pattern, html_lower)
        points += min(10, len(matches)) * 3

    # 4. Detect multiple iframes (often used for ads)
    iframe_count = len(soup.find_all("iframe"))
    if iframe_count > 3:
        points += min(15, (iframe_count - 3) * 5)

    ad_score = min(100, points)
    return ad_score, len(networks_found) + trackers_found


def calculate_corporate_score(url: str, html: str, text: str) -> int:
    """
    Comprehensive commercial/corporate/content-mill detection (0-100).
    Captures:
    1. Direct B2B/B2C Corporate Pages
    2. E-commerce & Landing Pages
    3. Content Mills & News Aggregators (Low original value)
    4. Lead-Gen & Squeeze Pages
    """
    from provoke.utils.landing_page import (
        is_service_landing_page,
        is_ecommerce_page,
        is_homepage_not_article,
        detect_spam_services,
        count_buttons_with_text,
    )
    from urllib.parse import urlparse

    score = 0
    url_lower = url.lower()
    html_lower = html.lower()
    text_lower = text.lower()
    parsed_url = urlparse(url)

    # 1. Content Protection (Negative points to help high-quality articles)
    # We only apply this if it's a deep path, not a generic one
    if len(parsed_url.path.split("/")) > 2:
        content_paths = [
            "/blog/",
            "/resources/",
            "/insights/",
            "/articles/",
            "/posts/",
            "/essays/",
        ]
        if any(p in url_lower for p in content_paths):
            score -= 20

    # 2. Hard Commercial Signals
    commercial_paths = [
        "/pricing",
        "/demo",
        "/product",
        "/solutions",
        "/features",
        "/enterprise",
        "/services",
        "/company",
        "/platform",
        "/checkout",
        "/cart",
        "/bylaws",
        "/annual-reports",
        "/sponsors",
        "/documentation",
        "/docs",
        "/api-reference",
        "/pricing",
    ]
    if any(p in url_lower for p in commercial_paths):
        # Docs are high corporate signal but not necessarily "commercial" in sales sense,
        # but they are definitely organizational.
        if "/docs" in url_lower or "/documentation" in url_lower:
            score += 45
        else:
            score += 25

    # E-commerce detection
    if is_ecommerce_page(html):
        score += 65

    # Spam/Lead-gen services
    if detect_spam_services(url, text):
        score += 75

    # Corporate / Service Schema
    org_schemas = [
        "organisation",
        "organization",
        "service",
        "product",
        "corporation",
        "localbusiness",
    ]
    if any(s in html_lower for s in org_schemas) and '"@type"' in html_lower:
        # Check for root specifically to avoid penalizing blog posts on subpaths
        if parsed_url.path.strip("/") in ["", "index.html", "index.php"]:
            score += 40

    # 3. Commercial Metadata (High signal for business sites)
    # Social meta tags usually indicate professional marketing
    meta_signals = [
        "og:site_name",
        "twitter:site",
        "fb:app_id",
        "og:type",
        "twitter:creator",
    ]
    meta_hits = sum(5 for m in meta_signals if m in html_lower)
    score += meta_hits  # Up to 25 points

    # 4. Content Mill & Aggregator Signals
    # Generic "Business" / "Media" footer links
    footer_keywords = [
        "privacy policy",
        "terms of use",
        "contact us",
        "about us",
        "cookie policy",
        "legal",
        "advertise",
        "press",
        "careers",
        "newsletter",
    ]
    footer_hits = sum(3 for kw in footer_keywords if kw in html_lower)
    score += min(footer_hits, 30)

    # Aggregator phrases
    aggregator_phrases = [
        "originally appeared on",
        "read more at",
        "source:",
        "via:",
        "credit:",
        "hat tip",
        "reporting by",
        "quotes are taken from",
    ]
    if any(phrase in text_lower for phrase in aggregator_phrases):
        score += 30

    # Content Mill Clutter phrases
    mill_phrases = [
        "latest stories",
        "trending now",
        "must read",
        "you may also like",
        "viral",
        "top stories",
        "stay tuned",
        "subscribe to our push-notifications",
    ]
    mill_hits = sum(5 for phrase in mill_phrases if phrase in text_lower)
    score += min(mill_hits, 25)

    # Affiliate / Ad-Revenue Signals
    affiliate_signals = [
        "affiliate link",
        "earn a commission",
        "sponsored",
        "disclosure:",
        "advertisement",
    ]
    if any(sig in text_lower for sig in affiliate_signals):
        score += 35

    # 5. Engagement Intensity (CTAs)
    # Broadened to catch media sites' "conversion" goals
    cta_keywords = [
        "buy",
        "purchase",
        "demo",
        "pricing",
        "sign up",
        "free trial",
        "get started",
        "subscribe",
        "newsletter",
        "follow us",
        "join us",
        "register",
        "create account",
    ]
    # CTA score should be less significant for long-form content
    cta_count = count_buttons_with_text(html, cta_keywords)
    word_count = len(text.split())
    if word_count > 600:
        score += min(cta_count * 4, 20)
    else:
        score += min(cta_count * 8, 40)

    # 5.5. Personal Blog Signals (Negative score = better)
    personal_keywords = config.PERSONAL_DOMAIN_KEYWORDS
    # Use word boundary to avoid matching substring (e.g., 'me' in 'merch')
    personal_hits = 0
    for kw in personal_keywords:
        pattern = rf"\b{re.escape(kw)}\b"
        if re.search(pattern, url_lower) or re.search(
            pattern, text_lower[:800], re.IGNORECASE
        ):
            personal_hits += 1

    score -= min(personal_hits * 10, 30)

    # 6. Service Description Language (Sales Copy)
    sales_copy = [
        "our customers",
        "trusted by",
        "case studies",
        "solution for",
        "maximize your",
        "unleash",
        "streamline your",
        "next-generation",
        "community platform",
        "collaboration",
        "foundation",
        "non-profit",
        "installation guide",
        "quickstart",
        "getting started",
        "api reference",
        "developer guide",
        "system requirements",
    ]
    if any(phrase in text_lower for phrase in sales_copy):
        score += 25

    # 7. Normalization and Tuning
    # If the page is essentially an empty container for a feed
    if is_homepage_not_article(url, html):
        score += 30

    final_score = max(0, min(100, score))
    return final_score


def calculate_readability(text: str) -> float:
    """Calculates Flesch Reading Ease score."""
    try:
        return textstat.flesch_reading_ease(text)
    except:
        return 0.0


def calculate_unified_score(scores: dict) -> int:
    """
    Combines individual heuristic scores into a single 0-100 quality score.
    """
    base_points = 0

    # 1. Content Density (Max 50)
    ratio = scores.get("text_ratio", 0)
    base_points += min(50, (ratio / 0.3) * 50)

    # 3. Readability (Max 50)
    readability = scores.get("readability", 0)
    if readability > 40:
        base_points += 50
    elif 15 <= readability <= 40:
        base_points += 30
    else:
        # Very complex academic/dense text
        base_points += 15

    # 4. Identity Signals (Corporate Penalty)
    corporate = scores.get("corporate_score", 0)
    # Aggressive penalty for high commercial intensity.
    # Score 40 (Aggregator level) -> -20 penalty
    # Score 80+ (Hard corporate) -> -50 penalty
    penalty = (corporate / 100) * 50
    base_points -= penalty

    # 6. Ad & Tracking Penalties
    ad_score = scores.get("ad_score", 0)
    if ad_score > 20:
        # Scaled penalty up to 25 points off
        penalty = min(25, ((ad_score - 20) / 80) * 25)
        base_points -= penalty

    return int(max(0, min(100, base_points)))


def check_page_title(html: str) -> str | None:
    """
    DEPRECATED: Use as part of corporate page checks.
    Checks if the page title contains excluded keywords.
    """
    soup = BeautifulSoup(html, "lxml")
    if not soup.title or not soup.title.string:
        return None

    title = soup.title.string
    # No need to lowercase for regex as we can use re.IGNORECASE flag if needed,
    # but let's stick to standard practice. Pattern is likely case-insensitive intent.
    # Actually, user wants robust matching. I'll use re.IGNORECASE.

    for pattern in config.EXCLUDED_TITLE_PATTERNS:
        if re.search(pattern, title, re.IGNORECASE):
            return "Title matched common phrase"
    return None


def evaluate_page_quality(
    url: str,
    html: str,
    text: str,
    whitelist: set | list | None = None,
    force_ml: bool = False,
) -> dict:
    """Combines all checks and return structured result."""
    from urllib.parse import urlparse
    from provoke.utils.landing_page import (
        is_service_landing_page,
        is_ecommerce_page,
        is_homepage_not_article,
        detect_spam_services,
    )

    # Check whitelist first (exact domain match, no subdomains)
    is_whitelisted = False
    parsed_url = urlparse(url)
    current_domain = parsed_url.netloc.lower()

    if whitelist:
        # User defined whitelist as domains. Check for exact match.
        if current_domain in [d.lower() for d in whitelist]:
            is_whitelisted = True

    # PHASE 0: URL Pattern Hard Rejection
    for pattern in config.EXCLUDED_URL_PATTERNS:
        if re.search(pattern, url, re.IGNORECASE):
            return {
                "is_acceptable": False,
                "rejection_reasons": ["URL matches excluded pattern"],
                "scores": {"excluded_pattern": True},
                "quality_tier": "rejected",
            }

    # PHASE 0.5: Root Landing Page check
    # Many homepages are just landing pages, not content.
    if not is_whitelisted:
        if is_homepage_not_article(url, html):
            return {
                "is_acceptable": False,
                "quality_tier": "rejected",
            }

    # PHASE 0.6: Ad Script Blacklist (Hard Rejection)
    if not is_whitelisted:
        from provoke.utils.adblock import get_ad_blocker

        ad_blocker = get_ad_blocker()
        soup = BeautifulSoup(html, "lxml")
        ad_scripts_found = []

        # Check src in scripts and link tags
        for tag in soup.find_all(["script", "link", "iframe"], src=True):
            src = str(tag.get("src", "")).lower()
            if ad_blocker.is_ad_url(src):
                ad_scripts_found.append(src)

        # Also check href in scripts/links
        for tag in soup.find_all(["script", "link"], href=True):
            href = str(tag.get("href", "")).lower()
            if ad_blocker.is_ad_url(href):
                ad_scripts_found.append(href)

        if len(set(ad_scripts_found)) >= 2:
            return {
                "is_acceptable": False,
                "rejection_reasons": ["High density of blacklisted ad scripts found"],
                "scores": {
                    "ad_script_blacklist": True,
                    "ad_count": len(set(ad_scripts_found)),
                },
                "quality_tier": "rejected",
            }

    # PHASE 1: COMPREHENSIVE SCORE PRE-FILTER
    # Calculate scores early to decide on hard rejection
    corp_score = calculate_corporate_score(url, html, text)

    if not is_whitelisted:
        # Only reject if overwhelmingly corporate (score > 90)
        # 80 was too low and caught many blogs with newsletters/products
        if corp_score > 90:
            return {
                "is_acceptable": False,
                "rejection_reasons": ["Corporate page"],
                "scores": {"corporate_score": corp_score},
                "quality_tier": "rejected",
            }

    # PHASE 2: Continue with existing quality checks

    text_ratio = calculate_text_ratio(html)
    word_count = len(text.split())
    readability = calculate_readability(text)

    ad_score, ad_tech_count = calculate_ad_score(html)
    scores = {
        "text_ratio": text_ratio,
        "word_count": word_count,
        "corporate_score": corp_score,
        "readability": readability,
        "ad_score": ad_score,
        "ad_tech_count": ad_tech_count,
    }

    unified_score = calculate_unified_score(scores)
    scores["unified_score"] = unified_score

    rejection_reasons = []

    # Final decision: Unified score (Bypassed if whitelisted)
    if is_whitelisted:
        is_acceptable = True
    else:
        is_acceptable = unified_score >= config.THRESHOLDS["unified_score_threshold"]

    # Initialize ml_accept to False (will be updated if ML is used)
    ml_accept = False

    # PHASE 3: ML Classification refinement (Kept for whitelisted domains)
    # Note: ML_CONFIG is now available as config.ML_CONFIG because we are in config.py
    # But for compatibility we can look it up from config object or global if defined.
    # config object is available globally in this file.

    if config.ML_CONFIG.get("enabled", False):
        from provoke.ml.classifier import get_classifier

        # We use ML if it's acceptable by rules, or if it's borderline, or if forced
        should_use_ml = True
        if should_use_ml:
            try:
                classifier = get_classifier(config.ML_CONFIG["model_path"])
                if classifier:
                    # Extract title for ML
                    soup = BeautifulSoup(html, "lxml")
                    page_title = soup.title.get_text(strip=True) if soup.title else ""

                    ml_accept, ml_reason, ml_confidence = classifier.is_acceptable(
                        text,
                        url=url,
                        title=page_title,
                        high_threshold=config.ML_CONFIG.get(
                            "high_confidence_threshold", 0.7
                        ),
                        low_threshold=config.ML_CONFIG.get(
                            "low_confidence_threshold", 0.3
                        ),
                    )

                    scores["ml_confidence"] = ml_confidence
                    scores["ml_decision"] = ml_reason

                    if ml_accept:
                        # Allow ML to rescue low-scoring pages if high confidence
                        if "high_confidence" in ml_reason:
                            is_acceptable = True
                    else:
                        is_acceptable = False
                        rejection_reasons.append("ML classified as low quality")
            except Exception:
                pass

    if not is_acceptable:
        # Only add score-based rejection reasons if not whitelisted
        if not is_whitelisted:
            if unified_score < config.THRESHOLDS["unified_score_threshold"]:
                rejection_reasons.append(
                    f"Unified quality score too low ({unified_score})"
                )

            if text_ratio < config.THRESHOLDS["min_text_ratio"]:
                rejection_reasons.append(
                    f"Text-to-HTML ratio too low ({text_ratio:.2f})"
                )
            if (
                readability < config.THRESHOLDS["min_readability"]
                or readability > config.THRESHOLDS["max_readability"]
            ):
                rejection_reasons.append(
                    f"Readability score out of range ({readability:.1f})"
                )
            if corp_score >= 40:
                rejection_reasons.append("Corporate page")

    # Unified Tier determination
    if not is_acceptable:
        tier = "rejected"
    elif unified_score >= config.THRESHOLDS["high_quality_threshold"]:
        tier = "high"
    elif unified_score >= config.THRESHOLDS["unified_score_threshold"]:
        tier = "medium"
    else:
        tier = "low"

    return {
        "is_acceptable": is_acceptable,
        "scores": scores,
        "rejection_reasons": rejection_reasons,
        "quality_tier": tier,
    }
