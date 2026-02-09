import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import textstat
from quality_config import (
    THRESHOLDS,
    CTA_PHRASES,
    MARKETING_TOOLS,
    AD_NETWORKS,
    PERSONAL_DOMAIN_KEYWORDS,
    EXCLUDED_TITLE_PATTERNS,
)


def calculate_text_ratio(html_content: str) -> float:
    """
    Calculates the ratio of visible text to content-bearing HTML.
    Focuses on the <body> and excludes non-textual structural tags.
    """
    if not html_content:
        return 0.0

    soup = BeautifulSoup(html_content, "lxml")
    body = soup.body if soup.body else soup

    # Create a copy or work on a fragment to avoid modifying the original soup if needed,
    # but here we can just decompose since this is a local analysis.

    # Remove definitely non-content tags from the denominator
    # Also strip framing elements like nav, header, footer to focus on core content density
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
    ]
    for element in body(tags_to_strip):
        element.decompose()

    text = body.get_text(separator=" ", strip=True)
    text_size = len(text)

    # We compare text size to the size of the remaining HTML structure (tags + text)
    content_html_size = len(str(body))

    if content_html_size == 0:
        return 0.0

    return text_size / content_html_size


def check_content_length(text: str) -> tuple[bool, int]:
    """Counts words in cleaned text and checks against thresholds."""
    words = text.split()
    word_count = len(words)
    is_acceptable = THRESHOLDS["min_words"] <= word_count <= THRESHOLDS["max_words"]
    return is_acceptable, word_count


def detect_advertising_tech(html: str) -> int:
    """Scans HTML for common ad/tracking scripts and services."""
    count = 0
    html_lower = html.lower()
    for ad_tech in AD_NETWORKS:
        if ad_tech in html_lower:
            count += 1

    # Also check for common patterns like pixel tracking
    pixel_patterns = [
        r"fbq\(\'track\'",
        r"gtag\(\'event\'",
        r"pixel\.gif",
        r"tracking",
        r"/ads/",
    ]
    for pattern in pixel_patterns:
        if re.search(pattern, html_lower):
            count += 1

    return count


def calculate_corporate_score(url: str, html: str, text: str) -> int:
    """Implements corporate scoring system (0-20 scale)."""
    score = 0
    url_lower = url.lower()
    html_lower = html.lower()
    text_lower = text.lower()

    # URL Analysis (0-5 points)
    if any(p in url_lower for p in ["/blog/", "/resources/", "/insights/"]):
        score += 2
    if any(
        p in url_lower
        for p in [
            "/pricing",
            "/demo",
            "/product",
            "/solutions",
            "/features",
            "/enterprise",
        ]
    ):
        score += 3

    # CTA Detection (0-6 points)
    cta_found = 0
    for cta in CTA_PHRASES:
        if cta in text_lower:
            cta_found += 1
    score += min(cta_found, 6)

    # Marketing Technology (0-6 points)
    mkt_tech_found = 0
    for tool in MARKETING_TOOLS:
        if tool in html_lower:
            mkt_tech_found += 2
    score += min(mkt_tech_found, 6)

    # Product Promotion (0-3 points)
    # Extract capitalized multi-word phrases (likely product names)
    # Simple heuristic: capitalized words not at the start of sentences
    # For speed, we'll look for specific recurring capitalized phrases
    words = text.split()
    if len(words) > 0:
        phrases = {}
        for i in range(len(words) - 1):
            if words[i][0].isupper() and words[i + 1][0].isupper():
                phrase = f"{words[i]} {words[i+1]}"
                phrases[phrase] = phrases.get(phrase, 0) + 1

        word_count = len(words)
        freq_threshold = (word_count / 1000) * 3
        if any(count > freq_threshold for count in phrases.values()):
            score += 3

    return score


def check_personal_blog_signals(url: str, html: str) -> int:
    """Positive signals scoring (0-10 scale)."""
    score = 0
    soup = BeautifulSoup(html, "lxml")
    url_lower = url.lower()

    # RSS/Atom feed (+3)
    if soup.find("link", type=["application/rss+xml", "application/atom+xml"]):
        score += 3

    # Single author metadata (+2)
    if soup.find("meta", attrs={"name": "author"}) or soup.find(
        class_=re.compile(r"author|byline", re.I)
    ):
        score += 2

    # Personal "About" page exists (+2)
    # check links for "About" or "Me"
    about_pattern = re.compile(r"About|Who am I|Me", re.I)
    if soup.find("a", string=about_pattern):
        score += 2

    # Domain structure suggests personal site (+2)
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    if any(keyword in domain for keyword in PERSONAL_DOMAIN_KEYWORDS):
        score += 2

    # Comments section (+1)
    if any(
        x in html
        for x in ["disqus_thread", "comment-respond", "comments-area", "utterances"]
    ):
        score += 1

    return score


def calculate_readability(text: str) -> float:
    """Calculates Flesch Reading Ease score."""
    try:
        return textstat.flesch_reading_ease(text)
    except:
        return 0.0


def detect_schema_type(html: str) -> str:
    """Parses HTML for schema.org metadata."""
    if "schema.org" not in html:
        return "none"

    # Look for Article, BlogPosting, etc. in JSON-LD
    json_ld = re.findall(
        r'<script type="application/ld\+json">(.*?)</script>', html, re.S
    )
    for ld in json_ld:
        if "BlogPosting" in ld:
            return "BlogPosting"
        if "Article" in ld:
            return "Article"
        if "TechArticle" in ld:
            return "TechArticle"
        if "Person" in ld:
            return "Person"
        if "Product" in ld:
            return "Product"
        if "Organization" in ld:
            return "Organization"

    # Also check Microdata
    if 'itemtype="http://schema.org/BlogPosting"' in html:
        return "BlogPosting"
    if 'itemtype="http://schema.org/Article"' in html:
        return "Article"

    return "none"


def detect_date_indicators(html: str, text: str) -> bool:
    """Look for date-related patterns that indicate blog/article content."""
    indicators = 0

    # HTML Metadata
    soup = BeautifulSoup(html, "lxml")
    if soup.find("meta", property=["article:published_time", "article:modified_time"]):
        indicators += 1
    if soup.find("time", datetime=True):
        indicators += 1
    if "datePublished" in html or "dateModified" in html:
        indicators += 1

    # Text patterns
    # Look in first 500 chars
    prefix = text[:500]
    date_patterns = [
        r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b",
        r"\b\d{4}-\d{2}-\d{2}\b",
        r"\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}\b",
    ]
    for pattern in date_patterns:
        if re.search(pattern, prefix, re.I):
            indicators += 1
            break

    if re.search(r"Posted on|Published|Last updated", prefix, re.I):
        indicators += 1

    return indicators >= 2


def calculate_unified_score(scores: dict) -> int:
    """
    Combines individual heuristic scores into a single 0-100 quality score.
    """
    base_points = 0

    # 1. Content Density (Max 15)
    ratio = scores.get("text_ratio", 0)
    base_points += min(15, (ratio / 0.3) * 15)

    # 2. Content Length (Max 30)
    words = scores.get("word_count", 0)
    if 300 <= words <= 2000:
        base_points += 30
    elif 100 <= words < 300:
        base_points += 5
    elif 2000 < words <= 5000:
        base_points += 25
    elif words > 5000:
        base_points += 20

    # 3. Readability (Max 25)
    readability = scores.get("readability", 0)
    if 40 < readability <= 100:
        base_points += 25
    elif 20 <= readability <= 40:
        base_points += 15
    elif 0 <= readability < 20:
        base_points += 5

    # 4. Identity Signals (Personal vs Corporate, Max 15)
    personal = scores.get("personal_signals", 0)
    base_points += min(15, (personal / 10) * 15)

    corporate = scores.get("corporate_score", 0)
    # Corporate score is a penalty (max penalty -30)
    base_points -= min(20, (corporate / 20) * 20)

    # 5. Metadata (Schema + Date, Max 15)
    if scores.get("has_blog_schema"):
        base_points += 10
    if scores.get("has_date_indicators"):
        base_points += 5

    # 6. Trust Penalties
    if scores.get("ad_tech_count", 0) > 5:
        base_points -= 3

    return int(max(0, min(100, base_points)))


def check_page_title(html: str) -> str | None:
    """Checks if the page title contains excluded keywords."""
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
    url: str, html: str, text: str, whitelist: set | list | None = None
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

    if not is_whitelisted:
        # PHASE 1: HARD REJECTIONS (before quality scoring)

        # Check 1: Service landing page
        is_service, service_score = is_service_landing_page(
            html, text, urlparse(url).path
        )
        if is_service:
            return {
                "is_acceptable": False,
                "rejection_reasons": ["Corporate Page"],
                "scores": {"service_score": service_score},
                "quality_tier": "rejected",
            }

        # Check 2: E-commerce
        if is_ecommerce_page(html):
            return {
                "is_acceptable": False,
                "rejection_reasons": ["Corporate Page"],
                "scores": {},
                "quality_tier": "rejected",
            }

        # Check 3: Spam services
        if detect_spam_services(url, text):
            return {
                "is_acceptable": False,
                "rejection_reasons": ["Corporate Page"],
                "scores": {},
                "quality_tier": "rejected",
            }

        # Check 4: Homepage without blog
        if is_homepage_not_article(url, html):
            return {
                "is_acceptable": False,
                "rejection_reasons": ["Corporate Page"],
                "scores": {},
                "quality_tier": "rejected",
            }

    # PHASE 2: Continue with existing quality checks

    text_ratio = calculate_text_ratio(html)
    is_length_ok, word_count = check_content_length(text)
    ad_tech_count = detect_advertising_tech(html)
    corp_score = calculate_corporate_score(url, html, text)
    personal_signals = check_personal_blog_signals(url, html)
    readability = calculate_readability(text)
    schema_type = detect_schema_type(html)
    has_date = detect_date_indicators(html, text)

    scores = {
        "text_ratio": text_ratio,
        "word_count": word_count,
        "corporate_score": corp_score,
        "personal_signals": personal_signals,
        "readability": readability,
        "ad_tech_count": ad_tech_count,
        "has_blog_schema": schema_type in ["BlogPosting", "Article", "TechArticle"],
        "has_date_indicators": has_date,
    }

    unified_score = calculate_unified_score(scores)
    scores["unified_score"] = unified_score

    rejection_reasons = []

    # Check title exclusion (Kept for whitelisted domains)
    title_rejection = check_page_title(html)
    if title_rejection:
        rejection_reasons.append(title_rejection)
        return {
            "is_acceptable": False,
            "scores": scores,
            "rejection_reasons": rejection_reasons,
            "quality_tier": "low",
        }

    # Final decision: Unified score (Bypassed if whitelisted)
    if is_whitelisted:
        is_acceptable = True
    else:
        is_acceptable = unified_score >= THRESHOLDS["unified_score_threshold"]

    # PHASE 3: ML Classification refinement (Kept for whitelisted domains)
    from quality_config import ML_CONFIG

    if ML_CONFIG.get("enabled", False):
        from ml_classifier import get_classifier

        # We use ML if it's acceptable by rules, or if it's borderline
        should_use_ml = True
        if ML_CONFIG.get("use_for_uncertain_only", True):
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
            if not is_length_ok:
                rejection_reasons.append(
                    f"Content length out of range ({word_count} words)"
                )
            if ad_tech_count > THRESHOLDS["max_ad_tech"]:
                rejection_reasons.append(
                    f"Too many ad/tracking technologies ({ad_tech_count})"
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
            if personal_signals < 2:
                rejection_reasons.append("Weak personal blog identity signals")

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
