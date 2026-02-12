# Backward compatibility shim - moved to provoke.utils.landing_page
from provoke.utils.landing_page import (
    count_buttons_with_text,
    detect_spam_services,
    extract_internal_links,
    is_ecommerce_page,
    is_homepage_not_article,
    is_service_landing_page,
)

__all__ = [
    "count_buttons_with_text",
    "detect_spam_services",
    "extract_internal_links",
    "is_ecommerce_page",
    "is_homepage_not_article",
    "is_service_landing_page",
]
