import csv
import os
import sys

# Add current directory to path so we can import ml_classifier
sys.path.append(os.getcwd())

from ml_classifier import ContentClassifier


def main():
    csv_path = "data/to_label.csv"
    model_path = "models/content_classifier.bin"

    if not os.path.exists(csv_path):
        print(f"CSV file not found at {csv_path}")
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

    print(f"Reading CSV from {csv_path}...")

    rows = []
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            # Normalize column names just in case (strip whitespace)
            reader.fieldnames = [name.strip() for name in reader.fieldnames]
            for row in reader:
                rows.append(row)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return

    total_items = len(rows)
    print(f"Found {total_items} items in the CSV. Running classification...")

    stats = {
        "good": 0,
        "bad": 0,
        "uncertain": 0,
        "high_confidence": 0,
        "low_confidence": 0,
        "high_conf_good": 0,
        "high_conf_bad": 0,
        "low_conf_good": 0,
        "low_conf_bad": 0,
    }

    # Accuracy stats
    matches = 0
    mismatches = 0
    valid_comparisons = 0

    bad_urls = []
    confidence_threshold = 0.8

    for row in rows:
        url = row.get("url", "")
        title = row.get("title", "")
        content = row.get("snippet", "")  # Using snippet as content
        manual_label = row.get("quality", "").lower().strip()

        # Predict
        label, confidence = classifier.predict(content, url=url, title=title)

        # Update prediction stats
        if label == "good":
            stats["good"] += 1
            if confidence >= confidence_threshold:
                stats["high_conf_good"] += 1
            else:
                stats["low_conf_good"] += 1
        elif label == "bad":
            stats["bad"] += 1
            bad_urls.append((url, confidence, manual_label))
            if confidence >= confidence_threshold:
                stats["high_conf_bad"] += 1
            else:
                stats["low_conf_bad"] += 1
        else:  # uncertain
            stats["uncertain"] += 1

        if confidence >= confidence_threshold:
            stats["high_confidence"] += 1
        else:
            stats["low_confidence"] += 1

        # confusion matrix-ish stats
        # Map manual labels to model labels for comparison
        # manual: good, bad, unsure
        # model: good, bad, uncertain

        model_mapped = label
        manual_mapped = manual_label

        if manual_mapped == "unsure":
            manual_mapped = "uncertain"

        if manual_mapped in ["good", "bad", "uncertain"]:
            if model_mapped == manual_mapped:
                matches += 1
            else:
                mismatches += 1
            valid_comparisons += 1

    print("\n--- Classification Statistics (CSV) ---")
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

    if valid_comparisons > 0:
        print(f"\n--- Accuracy against 'quality' column ---")
        print(f"Matches: {matches}")
        print(f"Mismatches: {mismatches}")
        print(f"Accuracy: {matches/valid_comparisons*100:.1f}%")

    print("\n--- Detailed Breakdown ---")
    print(f"High Confidence GOOD: {stats['high_conf_good']}")
    print(f"Low Confidence GOOD: {stats['low_conf_good']}")
    print(f"High Confidence BAD: {stats['high_conf_bad']}")
    print(f"Low Confidence BAD: {stats['low_conf_bad']}")

    if bad_urls:
        print("\n--- Classified as BAD (Top 50 by confidence) ---")
        # Sort by confidence (highest first)
        bad_urls.sort(key=lambda x: x[1], reverse=True)
        for i, (url, confidence, manual_label) in enumerate(bad_urls[:50]):
            label_info = f" [Manual: {manual_label}]" if manual_label else ""
            print(f"[{confidence:.2f}] {url}{label_info}")


if __name__ == "__main__":
    main()
