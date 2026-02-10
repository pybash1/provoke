THRESHOLDS = {
    "min_text_ratio": 0.1,
    "min_words": 100,
    "max_words": 8000,
    "corporate_score_threshold": 10,
    "min_personal_signals_if_corporate": 3,
    "ideal_readability_min": 60,
    "ideal_readability_max": 80,
    "min_readability": 20,
    "max_readability": 100,
    "domain_rejection_threshold": 30,
    "consecutive_rejection_threshold": 25,
    "unified_score_threshold": 40,
}

# ML Settings
ML_CONFIG = {
    "enabled": True,
    "model_path": "models/content_classifier.bin",
    "high_confidence_threshold": 0.7,  # Accept if >70% confident
    "low_confidence_threshold": 0.3,  # Uncertain if <30% confident
    "use_for_uncertain_only": True,  # Only use ML if rules uncertain
}

EXCLUDED_TITLE_PATTERNS = [
    r"privacy\s+policy",
    r"terms\s+of\s+use",
    r"terms\s+of\s+service",
    r"legal\s+notice",
    r"legal",
    r"cookie\s+policy",
    r"cookies",
    r"^home\s*[-\|]",  # Matches "Home -" or "Home |" at start
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

# Patterns in URLs that should be rejected immediately
EXCLUDED_URL_PATTERNS = [
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
]

CTA_PHRASES = [
    "free trial",
    "book a demo",
    "contact sales",
    "get started",
    "request demo",
    "schedule a call",
    "talk to sales",
    "release notes",
]

MARKETING_TOOLS = [
    "hubspot",
    "marketo",
    "pardot",
    "clearbit",
    "intercom",
    "drift",
    "calendly",
    "6sense",
]

AD_NETWORKS = [
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

TRACKING_SCRIPTS = [
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

AD_ELEMENT_PATTERNS = [
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

# Personal blog signals
PERSONAL_DOMAIN_KEYWORDS = ["blog", "personal", "me", "notes", "thoughts", "journal"]

# Extensions to reject (binary data, media, etc.)
# PDF is intentionally NOT in this list.
BINARY_EXTENSIONS = {
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
