import fasttext
import os
import numpy as np
from urllib.parse import urlparse

# NumPy 2.0 Compatibility Patch for FastText
_original_array = np.array


def _patched_array(obj, *args, **kwargs):
    if kwargs.get("copy") is False:
        return np.asarray(obj, dtype=kwargs.get("dtype"))
    return _original_array(obj, *args, **kwargs)


np.array = _patched_array


# Helper functions for rule-based quality checks
def is_likely_homepage(url: str, title: str, content: str) -> bool:
    """
    Detect homepage/index pages that are often misclassified as good.
    These should be marked as bad (false positives).
    """
    # Short content is suspicious for homepages
    if len(content) < 800:
        title_lower = title.lower()

        # Generic homepage titles
        homepage_indicators = [
            "home",
            "welcome",
            "index",
            "main page",
            "skip to content",
            "skip to main",
            "menu",
            "navigation",
        ]

        if any(indicator in title_lower for indicator in homepage_indicators):
            return True

        # Root or near-root URLs
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.split("/") if p]

        # Root URL or very shallow
        if len(path_parts) <= 1:
            return True

    return False


def is_special_good_format(url: str, title: str) -> bool:
    """
    Detect special formats that should be marked as good despite minimal content.
    These prevent false negatives.
    """
    url_lower = url.lower()

    # RSS/Atom feeds from good sources
    if any(pattern in url_lower for pattern in [".xml", "/feed", "/rss", "/atom"]):
        return True

    # Contact/about pages from personal sites
    if any(pattern in url_lower for pattern in ["/hi/", "/about/", "/contact/"]):
        # Check if it's from a known good domain pattern (extensible list)
        if any(
            pattern in url_lower
            for pattern in [
                "benkuhn.net",
                "maggieappleton.com",
                "andymatuschak.org",
                "swyx.io",
                "linus.coffee",
                "thesephist.com",
            ]
        ):
            return True

    # Blog post URLs (even if content is short)
    if any(
        pattern in url_lower for pattern in ["/blog/", "/post/", "/article/", "/notes/"]
    ):
        return True

    return False


def is_commercial_or_low_quality(url: str, title: str) -> bool:
    """
    Detect commercial or low-quality pages that should be marked as bad.
    """
    url_lower = url.lower()
    title_lower = title.lower()

    # E-commerce indicators
    commerce_patterns = [
        "cart",
        "checkout",
        "shop",
        "store",
        "buy now",
        "add to cart",
        "shopping",
        "products",
        "pricing",
    ]

    if any(pattern in title_lower for pattern in commerce_patterns):
        return True

    # Commercial domains
    commercial_domains = [
        "amazon.",
        "ebay.",
        "shopify.",
        "store.",
        "shop.",
        "buy.",
        "cart.",
    ]

    if any(domain in url_lower for domain in commercial_domains):
        return True

    # Low-quality page types
    low_quality_patterns = [
        "privacy policy",
        "terms of use",
        "terms and conditions",
        "cookie policy",
        "legal",
        "disclaimer",
        "sign in",
        "log in",
        "login",
        "register",
        "signup",
        "sign up",
    ]

    if any(pattern in title_lower for pattern in low_quality_patterns):
        return True

    return False


class ContentClassifier:
    """Wrapper for FastText classifier."""

    def __init__(self, model_path: str):
        """Load FastText model."""
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")
        self.model = fasttext.load_model(model_path)
        print(f"Loaded FastText model from {model_path}")

    def predict(
        self, text: str, url: str = "", title: str = "", threshold: float = 0.7
    ) -> tuple[str, float]:
        """
        Predict quality of text content with optional URL and title features.

        Returns:
            (label, confidence) where label is 'good', 'bad', or 'uncertain'
        """
        # Prepare input text with features if available
        clean_text = " ".join(text.split())
        input_text = clean_text

        if url or title:
            # Match the training data format: url=<url> title=<title> <content>
            # Note: We don't force url/title if empty, just use what we have
            parts = []
            if url:
                parts.append(f"url={url}")
            if title:
                clean_title = " ".join(title.split())
                parts.append(f"title={clean_title}")
            parts.append(clean_text)
            input_text = " ".join(parts)

        if not input_text:
            return "bad", 1.0

        # Predict
        labels, confidences = self.model.predict(input_text)

        # Add checks for empty labels and confidences
        if not labels or len(labels) == 0 or not confidences or len(confidences) == 0:
            return "uncertain", 0.0

        label = labels[0].replace("__label__", "")
        confidence = confidences[0]

        # Handle uncertainty
        if confidence < threshold:
            return "uncertain", confidence

        return label, confidence

    def enhanced_check(
        self,
        url: str,
        title: str,
        content: str,
        ml_prediction: str,
        ml_confidence: float,
    ) -> tuple[str, float, str]:
        """
        Combine ML prediction with rule-based checks.

        Returns:
            (final_prediction, adjusted_confidence, reason)
        """
        reasons = []
        confidence_adjustment = 0.0

        # Rule 1: Homepage detection (reduce false positives)
        if is_likely_homepage(url, title, content):
            if ml_prediction == "good":
                confidence_adjustment -= 0.3
                reasons.append("Detected as homepage")

        # Rule 2: Special good formats (reduce false negatives)
        if is_special_good_format(url, title):
            if ml_prediction == "bad":
                confidence_adjustment += 0.2
                reasons.append("Special good format")

        # Rule 3: Commercial/low-quality (reduce false positives)
        if is_commercial_or_low_quality(url, title):
            if ml_prediction == "good":
                confidence_adjustment -= 0.25
                reasons.append("Commercial/low-quality indicators")

        # Calculate adjusted confidence
        adjusted_confidence = ml_confidence + confidence_adjustment

        # Determine final prediction with threshold (using a slightly looser threshold for final decision)
        threshold = 0.6
        final_prediction = "good" if adjusted_confidence >= threshold else "bad"

        # If no rules triggered, keep original prediction but return current confidence
        if not reasons:
            final_prediction = ml_prediction
            adjusted_confidence = ml_confidence
            reasons.append("ML prediction only")

        reason = "; ".join(reasons)

        return final_prediction, adjusted_confidence, reason

    def is_acceptable(
        self,
        text: str,
        url: str = "",
        title: str = "",
        high_threshold: float = 0.7,
        low_threshold: float = 0.3,
    ) -> tuple[bool, str, float]:
        """
        Determine if content should be accepted.

        Returns:
            (accept, decision_reason, confidence)
        """
        # 1. Get raw ML prediction (threshold=0 to get raw result)
        ml_label, ml_confidence = self.predict(text, url, title, threshold=0.0)

        # 2. Apply enhanced checks
        label, confidence, check_reason = self.enhanced_check(
            url, title, text, ml_label, ml_confidence
        )

        # 3. Final Decision Logic
        if label == "good" and confidence >= high_threshold:
            return True, f"ml_high_confidence_good ({check_reason})", confidence

        elif label == "bad" and confidence >= high_threshold:
            return False, f"ml_high_confidence_bad ({check_reason})", confidence

        else:
            # Uncertain - use conservative approach
            # Accept if labeled good OR if very uncertain (and not explicitly bad)
            # Note: The original logic accepted uncertain, but here we might want to be careful.
            # Use the 'label' which comes from our enhanced check (defaults to adjusted threshold)

            if label == "good":
                return True, f"ml_uncertain_accept ({check_reason})", confidence
            else:
                return False, f"ml_uncertain_reject ({check_reason})", confidence


# Global classifier instance
_classifier = None


def get_classifier(model_path: str = "models/content_classifier.bin"):
    """Get or create global classifier instance."""
    global _classifier
    if _classifier is None:
        try:
            _classifier = ContentClassifier(model_path)
        except Exception as e:
            # Optimization: don't log this every time if it's expected (e.g. before first training)
            # print(f"Classifier loading skipped: {e}")
            return None
    return _classifier
