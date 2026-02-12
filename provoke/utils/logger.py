import csv
import os
import logging
from datetime import datetime
from config import config


class QualityLogger:
    def __init__(self, log_file=None, csv_file=None):
        self.log_file = log_file or config.REJECTED_URLS_LOG
        self.csv_file = csv_file or config.QUALITY_STATS_CSV
        self.stats = {
            "accepted": 0,
            "rejected": 0,
            "rejection_reasons": {},
            "tiers": {"high": 0, "medium": 0, "low": 0},
        }

        # Setup basic logging
        logging.basicConfig(
            filename=self.log_file,
            level=logging.INFO,
            format="%(asctime)s - %(message)s",
        )

        # Initialize CSV if it doesn't exist
        if not os.path.exists(self.csv_file):
            with open(self.csv_file, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "url",
                        "rejection_reasons",
                        "corporate_score",
                        "text_ratio",
                        "word_count",
                        "unified_score",
                        "timestamp",
                    ]
                )

    def log_rejection(self, url, reasons, scores):
        reason_str = ", ".join(reasons)
        logging.info(f"REJECTED: {url} - Reasons: {reason_str}")

        # Update stats
        self.stats["rejected"] += 1
        for reason in reasons:
            self.stats["rejection_reasons"][reason] = (
                self.stats["rejection_reasons"].get(reason, 0) + 1
            )

        # Log to CSV
        with open(self.csv_file, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    url,
                    reason_str,
                    scores.get("corporate_score", 0),
                    round(scores.get("text_ratio", 0), 3),
                    scores.get("word_count", 0),
                    scores.get("unified_score", 0),
                    datetime.now().isoformat(),
                ]
            )

    def log_acceptance(self, url, tier):
        self.stats["accepted"] += 1
        self.stats["tiers"][tier] = self.stats["tiers"].get(tier, 0) + 1
        logging.info(f"ACCEPTED: {url} - Tier: {tier}")

    def get_summary(self):
        summary = [
            "\n--- Crawl Quality Summary ---",
            f"Total Pages Processed: {self.stats['accepted'] + self.stats['rejected']}",
            f"Accepted: {self.stats['accepted']}",
            f"Rejected: {self.stats['rejected']}",
            "\nQuality Tiers (Accepted):",
            f"  High: {self.stats['tiers']['high']}",
            f"  Medium: {self.stats['tiers']['medium']}",
            f"  Low: {self.stats['tiers']['low']}",
            "\nRejection Reasons:",
        ]
        for reason, count in sorted(
            self.stats["rejection_reasons"].items(), key=lambda x: x[1], reverse=True
        ):
            summary.append(f"  - {reason}: {count}")
        summary.append("----------------------------\n")
        return "\n".join(summary)

    def print_summary(self):
        print(self.get_summary())

    def log_rejection_summary(self):
        """Print summary of rejections by category."""
        print("\n=== Rejection Summary ===")
        # Use simple mapping for category names if needed, but here we can just use the keys
        for category, count in sorted(
            self.stats["rejection_reasons"].items(), key=lambda x: x[1], reverse=True
        ):
            if count > 0:
                print(f"{category}: {count}")
