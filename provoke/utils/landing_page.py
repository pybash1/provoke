import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup


def count_buttons_with_text(html: str, keywords: list[str]) -> int:
    """Count buttons/links containing specific keywords."""
    soup = BeautifulSoup(html, "lxml")

    # Find all buttons and links
    elements = soup.find_all(["button", "a"])

    count = 0
    seen_keywords = set()

    for elem in elements:
        text = elem.get_text(strip=True).lower()
        for keyword in keywords:
            if keyword.lower() in text and keyword not in seen_keywords:
                count += 1
                seen_keywords.add(keyword)
                break

    return count


def extract_internal_links(html: str) -> list[str]:
    """Extract all internal link paths from HTML."""
    soup = BeautifulSoup(html, "lxml")
    links = []

    for a in soup.find_all("a", href=True):
        href = a["href"]
        # Handle potential list return (though rare for href)
        if isinstance(href, list):
            href = href[0]

        # Filter for internal links (relative or same domain)
        if href.startswith("/") or not href.startswith("http"):
            links.append(href)

    return links


def is_service_landing_page(html: str, text: str, url_path: str) -> tuple[bool, int]:
    """
    Detect pages that are selling a service or product.
    Returns (True, score) if score > 8.
    """
    score = 0
    text_lower = text.lower()

    # CTA Button Detection (0-10 points)
    cta_keywords = [
        "buy",
        "purchase",
        "order now",
        "get started",
        "sign up",
        "try free",
        "free trial",
        "download",
        "subscribe",
        "add to cart",
        "shop now",
        "buy now",
    ]
    # We use the helper function but we need to count unique types found
    # The helper function 'count_buttons_with_text' already counts unique keywords found (based on the set logic).
    # Wait, the prompt says "Award 2 points per unique CTA type found".
    # My helper function implementation:
    # checks if keyword in text, adds to seen_keywords, increments count.
    # So it returns number of unique keywords found.

    cta_count = count_buttons_with_text(html, cta_keywords)
    score += min(cta_count * 2, 10)

    # Pricing Indicators (0-3 points)
    pricing_indicators = 0
    currency_symbols = ["$", "€", "£", "¥"]
    pricing_phrases = [
        "price:",
        "pricing",
        "from $",
        "starting at $",
        "/month",
        "/year",
    ]

    for symbol in currency_symbols:
        if symbol in text:
            pricing_indicators += 1

    for phrase in pricing_phrases:
        if phrase in text_lower:
            pricing_indicators += 1

    if pricing_indicators >= 2:
        score += 3

    # Service Description Language (0-6 points)
    service_phrases = [
        "we offer",
        "our service",
        "we provide",
        "we help you",
        "buy followers",
        "buy likes",
        "increase your",
        "humanize text",
        "get more",
        "boost your",
    ]

    unique_service_phrases = 0
    for phrase in service_phrases:
        if phrase in text_lower:
            unique_service_phrases += 1

    score += min(unique_service_phrases * 2, 6)

    # Root Domain Check (0-2 points)
    normalized_path = url_path.strip().lower()
    if (
        normalized_path in ["/", "/index", "/index.html", "/home", ""]
        or normalized_path == "/"
    ):
        score += 2

    return score > 8, score


def is_ecommerce_page(html: str) -> bool:
    """Detect online shopping and product pages."""
    html_lower = html.lower()

    # Shopping Cart Indicators
    cart_phrases = [
        "add to cart",
        "shopping cart",
        "shopping bag",
        "proceed to checkout",
        "out of stock",
        "low stock",
        "add to bag",
        "add to wishlist",
    ]

    for phrase in cart_phrases:
        if phrase in html_lower:
            return True

    # Product Schema
    if (
        "schema.org/product" in html_lower
        or '"@type":"product"' in html_lower
        or '"@type": "product"' in html_lower
    ):
        return True

    # Payment Method Visibility
    payment_methods = [
        "paypal",
        "visa",
        "mastercard",
        "amex",
        "discover",
        "apple pay",
        "google pay",
    ]

    payment_count = 0
    for method in payment_methods:
        if method in html_lower:
            payment_count += 1

    if payment_count >= 2:
        return True

    return False


def is_homepage_not_article(url: str, html: str) -> bool:
    """Detect homepages that don't lead to blog content."""

    # 1. Parse URL path
    path = urlparse(url).path.strip("/")

    # 2. Check if root domain
    root_paths = ["", "index", "index.html", "home", "index.php"]
    if path not in root_paths:
        return False  # Not a homepage

    # 3. If it IS a homepage, check for blog section
    internal_links = extract_internal_links(html)

    blog_link_patterns = [
        "/blog/",
        "/post/",
        "/posts/",
        "/article/",
        "/articles/",
        "/news/",
        "/writing/",
        "/essays/",
        "/20",  # year pattern
    ]

    blog_link_count = 0
    for link in internal_links:
        for pattern in blog_link_patterns:
            if pattern in link:
                blog_link_count += 1
                break

    # 4. Decision
    if blog_link_count >= 3:
        return False  # Acceptable homepage with blog
    else:
        return True  # Homepage without blog content


def detect_spam_services(url: str, text: str) -> bool:
    """Detect spam/manipulation services and low-value tools."""

    social_spam = [
        "buy followers",
        "buy likes",
        "buy subscribers",
        "buy views",
        "cheap followers",
        "real followers",
        "instagram followers",
        "tiktok followers",
        "youtube subscribers",
        "boost your engagement",
        "increase followers",
        "grow your audience fast",
    ]

    seo_tools = [
        "paraphrase",
        "paraphrasing tool",
        "rewrite text",
        "article rewriter",
        "spin text",
        "humanize text",
        "humanize ai",
        "undetectable ai",
        "bypass ai detector",
        "plagiarism checker",
        "seo tool",
    ]

    all_keywords = social_spam + seo_tools

    # 1. Check URL
    url_lower = url.lower()
    for keyword in all_keywords:
        # Remove spaces for URL check
        keyword_no_space = keyword.replace(" ", "")
        if keyword_no_space in url_lower:
            return True

    # 2. Check Text Content
    text_lower = text.lower()
    unique_keywords_found = 0

    for keyword in all_keywords:
        if keyword in text_lower:
            unique_keywords_found += 1

    if unique_keywords_found >= 3:
        return True

    return False
