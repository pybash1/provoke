import sqlite3
import os

from provoke.ml.classifier import ContentClassifier
from provoke.config import config


def main():
    db_path = config.DATABASE_PATH
    model_path = config.ML_CONFIG["model_path"]

    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    if not os.path.exists(model_path):
        print(f"Model not found at {model_path}")
        return

    print(f"Loading model from {model_path}...")
    try:
        classifier = ContentClassifier(model_path)
    except Exception as e:
        print(f"Failed to load model: {e}")
        return

    print(f"Connecting to database {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT url, title, content FROM pages")
        rows = cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        conn.close()
        return

    total_items = len(rows)
    print(f"Found {total_items} items in the database. Running classification...")

    stats = {
        "good": 0,
        "bad": 0,
        "uncertain": 0,  # explicit category from classifier
        "high_confidence": 0,
        "low_confidence": 0,
        "high_conf_good": 0,
        "high_conf_bad": 0,
        "low_conf_good": 0,
        "low_conf_bad": 0,
    }

    bad_urls = []

    confidence_threshold = config.ML_CONFIDENCE_THRESHOLD

    for url, title, content in rows:
        # Use predict method effectively used by the classifier
        # Note: predict returns (label, confidence)
        # We handle None/empty content gracefully
        if not content:
            content = ""

        label, confidence = classifier.predict(content, url=url, title=title)

        # Update detailed stats
        if label == "good":
            stats["good"] += 1
            if confidence >= confidence_threshold:
                stats["high_conf_good"] += 1
            else:
                stats["low_conf_good"] += 1
        elif label == "bad":
            stats["bad"] += 1
            bad_urls.append((url, confidence))
            if confidence >= confidence_threshold:
                stats["high_conf_bad"] += 1
            else:
                stats["low_conf_bad"] += 1
        else:  # uncertain
            stats["uncertain"] += 1

        # Update general confidence stats
        if confidence >= confidence_threshold:
            stats["high_confidence"] += 1
        else:
            stats["low_confidence"] += 1

    conn.close()

    print("\n--- Classification Statistics ---")
    print(f"Total Items: {total_items}")
    print(f"Classified as GOOD: {stats['good']} ({stats['good']/total_items*100:.1f}%)")
    print(f"Classified as BAD: {stats['bad']} ({stats['bad']/total_items*100:.1f}%)")
    if stats["uncertain"] > 0:
        print(
            f"Classified as UNCERTAIN: {stats['uncertain']} ({stats['uncertain']/total_items*100:.1f}%)"
        )

    print(f"\n--- Confidence Stats (Threshold: {confidence_threshold}) ---")
    print(
        f"High Confidence: {stats['high_confidence']} ({stats['high_confidence']/total_items*100:.1f}%)"
    )
    print(
        f"Low Confidence: {stats['low_confidence']} ({stats['low_confidence']/total_items*100:.1f}%)"
    )

    print("\n--- Detailed Breakdown ---")
    print(f"High Confidence GOOD: {stats['high_conf_good']}")
    print(f"Low Confidence GOOD: {stats['low_conf_good']}")
    print(f"High Confidence BAD: {stats['high_conf_bad']}")
    print(f"Low Confidence BAD: {stats['low_conf_bad']}")

    if bad_urls:
        print("\n--- Bad URLs ---")
        # Sort by confidence (highest first)
        bad_urls.sort(key=lambda x: x[1], reverse=True)
        for url, confidence in bad_urls:
            print(f"[{confidence:.2f}] {url}")


if __name__ == "__main__":
    main()
