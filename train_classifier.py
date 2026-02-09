#!/usr/bin/env python3
"""
Training workflow for content quality classifier.

Usage:
    python train_classifier.py --export     # Export pages for labeling
    python train_classifier.py --train      # Train model after labeling
    python train_classifier.py --evaluate   # Evaluate model
"""

import argparse
import os
from ml_data_prep import (
    export_indexed_pages,
    create_fasttext_training_file,
    split_training_data,
    augment_from_rejected_urls,
)
from ml_train import train_fasttext_model, evaluate_model


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--export", action="store_true", help="Export pages for labeling"
    )
    parser.add_argument("--train", action="store_true", help="Train model")
    parser.add_argument("--evaluate", action="store_true", help="Evaluate model")
    parser.add_argument("--limit", type=int, default=500, help="Limit for export")
    args = parser.parse_args()

    # Ensure data and models directories exist
    os.makedirs("data", exist_ok=True)
    os.makedirs("models", exist_ok=True)

    if args.export:
        print(f"Exporting data for labeling (Total Limit: {args.limit})...")

        # 1. Clear existing to_label.csv if it exists to start fresh
        if os.path.exists("data/to_label.csv"):
            os.remove("data/to_label.csv")

        # 2. Export indexed pages (potential good/bad mix from DB)
        # We'll take 40% from DB and 60% from rejected logs for a balanced mix
        db_limit = int(args.limit * 0.4)
        rejected_limit = args.limit - db_limit

        print(f"Sampling {db_limit} pages from indexed content...")
        export_indexed_pages("data/to_label.csv", limit=db_limit)

        print(f"Sampling up to {rejected_limit} pages from rejected URLs...")
        augment_from_rejected_urls("data/to_label.csv", limit=rejected_limit)

        print("\nNext steps:")
        print("1. Open data/to_label.csv")
        print("2. Review and label the 'quality' column with 'good' or 'bad'")
        print("   (Note: Rejected URLs are pre-filled as 'bad')")
        print("3. Run: python train_classifier.py --train")

    elif args.train:
        print("Preparing training data...")
        create_fasttext_training_file("data/to_label.csv", "data/training_data.txt")

        split_training_data(
            "data/training_data.txt", "data/train.txt", "data/test.txt", test_ratio=0.25
        )

        print("\nTraining model...")
        model = train_fasttext_model(
            "data/train.txt",
            "models/content_classifier.bin",
            lr=0.5,
            epoch=25,
            wordNgrams=2,
        )

        if model:
            print("\nEvaluating on test set...")
            evaluate_model("models/content_classifier.bin", "data/test.txt")
            print("\nTraining complete! Model saved to models/content_classifier.bin")

    elif args.evaluate:
        print("Evaluating model...")
        evaluate_model("models/content_classifier.bin", "data/test.txt")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
