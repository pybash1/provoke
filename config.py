"""
Backward-compatible shim for provoke.config

All configuration and quality assessment logic has moved to the provoke package.
This file is maintained for backward compatibility.
"""

from provoke.config import (
    config,
    evaluate_page_quality,
    calculate_text_ratio,
    calculate_ad_score,
    calculate_corporate_score,
    calculate_readability,
    calculate_unified_score,
    check_page_title,
    THRESHOLDS,
    ML_CONFIG,
    EXCLUDED_TITLE_PATTERNS,
    EXCLUDED_URL_PATTERNS,
    CTA_PHRASES,
    MARKETING_TOOLS,
    AD_NETWORKS,
    TRACKING_SCRIPTS,
    AD_ELEMENT_PATTERNS,
    PERSONAL_DOMAIN_KEYWORDS,
    BINARY_EXTENSIONS,
    STOPWORDS,
)

__all__ = [
    "config",
    "evaluate_page_quality",
    "calculate_text_ratio",
    "calculate_ad_score",
    "calculate_corporate_score",
    "calculate_readability",
    "calculate_unified_score",
    "check_page_title",
    "THRESHOLDS",
    "ML_CONFIG",
    "EXCLUDED_TITLE_PATTERNS",
    "EXCLUDED_URL_PATTERNS",
    "CTA_PHRASES",
    "MARKETING_TOOLS",
    "AD_NETWORKS",
    "TRACKING_SCRIPTS",
    "AD_ELEMENT_PATTERNS",
    "PERSONAL_DOMAIN_KEYWORDS",
    "BINARY_EXTENSIONS",
    "STOPWORDS",
]
