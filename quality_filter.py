import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import textstat
from quality_config import (
    THRESHOLDS,
    CTA_PHRASES,
    MARKETING_TOOLS,
    AD_NETWORKS,
    TRACKING_SCRIPTS,
    AD_ELEMENT_PATTERNS,
    EXCLUDED_TITLE_PATTERNS,
)

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
    min_words = THRESHOLDS.get("min_words", 100)
    length_factor = min(1.0, max(0.1, word_count / (min_words * 0.8)))

    # Final adjusted ratio
    adjusted_ratio = raw_ratio * link_penalty * stopword_factor * length_factor

    return min(1.0, float(adjusted_ratio))


def calculate_ad_score(html: str) -> int:
    """
    Calculates an 'ad score' (0-100) based on detected ad/tracking tech.
    Higher score means more ad-heavy.
    """
    if not html:
        return 0

    points = 0
    html_lower = html.lower()

    # 1. Check for specific domains/networks (Width of tech)
    networks_found = 0
    for network in AD_NETWORKS:
        if network in html_lower:
            networks_found += 1
            points += 10

    # 2. Check for tracking patterns
    trackers_found = 0
    for pattern in TRACKING_SCRIPTS:
        if re.search(pattern, html_lower):
            trackers_found += 1
            points += 5

    # 3. Check for specific ad elements in HTML structure (Density of ads)
    # We count occurrences to detect "ad-stuffed" pages
    for pattern in AD_ELEMENT_PATTERNS:
        # We cap the regex matches to prevent huge counts from becoming astronomical
        matches = re.findall(pattern, html_lower)
        points += min(10, len(matches)) * 3

    # 4. Detect multiple iframes (often used for ads)
    iframe_count = html_lower.count("<iframe")
    if iframe_count > 3:
        points += min(15, (iframe_count - 3) * 3)

    return min(100, points)


def calculate_corporate_score(url: str, html: str, text: str) -> int:
    """
    Comprehensive commercial/corporate/content-mill detection (0-100).
    Captures:
    1. Direct B2B/B2C Corporate Pages
    2. E-commerce & Landing Pages
    3. Content Mills & News Aggregators (Low original value)
    4. Lead-Gen & Squeeze Pages
    """
    from landing_page_filter import (
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
    ]
    if any(p in url_lower for p in commercial_paths):
        score += 45

    # E-commerce detection
    if is_ecommerce_page(html):
        score += 65

    # Spam/Lead-gen services
    if detect_spam_services(url, text):
        score += 75

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
    mill_hits = sum(10 for phrase in mill_phrases if phrase in text_lower)
    score += min(mill_hits, 40)

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
    cta_count = count_buttons_with_text(html, cta_keywords)
    score += min(cta_count * 15, 60)

    # 6. Service Description Language (Sales Copy)
    sales_copy = [
        "our customers",
        "trusted by",
        "case studies",
        "solution for",
        "maximize your",
        "unleash",
        "streamline your",
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
    if 40 < readability <= 100:
        base_points += 50
    elif 20 <= readability <= 40:
        base_points += 30
    elif 0 <= readability < 20:
        base_points += 10

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

    for pattern in EXCLUDED_TITLE_PATTERNS:
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
    from landing_page_filter import (
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

    # PHASE 1: COMPREHENSIVE SCORE PRE-FILTER
    # Calculate scores early to decide on hard rejection
    corp_score = calculate_corporate_score(url, html, text)

    if not is_whitelisted:
        # If the page is overwhelmingly corporate (score > 80), reject immediately
        if corp_score > 80:
            return {
                "is_acceptable": False,
                "rejection_reasons": ["Corporate Page"],
                "scores": {"corporate_score": corp_score},
                "quality_tier": "rejected",
            }

    # PHASE 2: Continue with existing quality checks

    text_ratio = calculate_text_ratio(html)
    word_count = len(text.split())
    readability = calculate_readability(text)

    scores = {
        "text_ratio": text_ratio,
        "word_count": word_count,
        "corporate_score": corp_score,
        "readability": readability,
        "ad_score": calculate_ad_score(html),
    }

    unified_score = calculate_unified_score(scores)
    scores["unified_score"] = unified_score

    rejection_reasons = []

    # Final decision: Unified score (Bypassed if whitelisted)
    if is_whitelisted:
        is_acceptable = True
    else:
        is_acceptable = unified_score >= THRESHOLDS["unified_score_threshold"]

    # PHASE 3: ML Classification refinement (Kept for whitelisted domains)
    from quality_config import ML_CONFIG

    if ML_CONFIG.get("enabled", False):
        from ml_classifier import get_classifier

        # We use ML if it's acceptable by rules, or if it's borderline, or if forced
        should_use_ml = True
        if not force_ml and ML_CONFIG.get("use_for_uncertain_only", True):
            should_use_ml = unified_score < 80

        if should_use_ml:
            try:
                classifier = get_classifier(
                    ML_CONFIG.get("model_path", "models/content_classifier.bin")
                )
                if classifier:
                    # Extract title for ML
                    soup = BeautifulSoup(html, "lxml")
                    page_title = soup.title.get_text(strip=True) if soup.title else ""

                    ml_accept, ml_reason, ml_confidence = classifier.is_acceptable(
                        text,
                        url=url,
                        title=page_title,
                        high_threshold=ML_CONFIG.get("high_confidence_threshold", 0.7),
                        low_threshold=ML_CONFIG.get("low_confidence_threshold", 0.3),
                    )

                    scores["ml_confidence"] = ml_confidence
                    scores["ml_decision"] = ml_reason

                    if ml_accept:
                        # Allow ML to rescue low-scoring pages if high confidence
                        if "high_confidence" in ml_reason:
                            is_acceptable = True
                    else:
                        is_acceptable = False
                        rejection_reasons.append(
                            f"ML classified as low quality ({ml_reason})"
                        )
            except Exception:
                pass

    if not is_acceptable:
        # Only add score-based rejection reasons if not whitelisted
        if not is_whitelisted:
            rejection_reasons.append(f"Unified quality score too low ({unified_score})")

            if text_ratio < THRESHOLDS["min_text_ratio"]:
                rejection_reasons.append(
                    f"Text-to-HTML ratio too low ({text_ratio:.2f})"
                )
            if (
                readability < THRESHOLDS["min_readability"]
                or readability > THRESHOLDS["max_readability"]
            ):
                rejection_reasons.append(
                    f"Readability score out of range ({readability:.1f})"
                )
            if corp_score >= 10:
                rejection_reasons.append("Likely corporate marketing")

    # Unified Tier determination
    if unified_score >= 80:
        tier = "high"
    elif unified_score >= THRESHOLDS["unified_score_threshold"] or is_whitelisted:
        tier = "medium"
    else:
        tier = "low"

    return {
        "is_acceptable": is_acceptable,
        "scores": scores,
        "rejection_reasons": rejection_reasons,
        "quality_tier": tier,
    }
