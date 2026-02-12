#!/usr/bin/env python3
"""
Training workflow for content quality classifier.

Usage:
    uv run python -m provoke.ml.trainer --export     # Export pages for labeling
    uv run python -m provoke.ml.trainer --train      # Train model after labeling
    uv run python -m provoke.ml.trainer --evaluate   # Evaluate model
"""

import argparse
import os
from provoke.config import config
from provoke.ml.data_prep import (
    export_indexed_pages,
    create_fasttext_training_file,
    split_training_data,
    augment_from_rejected_urls,
)
from provoke.ml.training import train_fasttext_model, evaluate_model


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--export", action="store_true", help="Export pages for labeling"
    )
    parser.add_argument("--train", action="store_true", help="Train model")
    parser.add_argument("--evaluate", action="store_true", help="Evaluate model")
    parser.add_argument(
        "--limit", type=int, default=config.ML_EXPORT_LIMIT, help="Limit for export"
    )
    args = parser.parse_args()

    # Ensure data and models directories exist
    os.makedirs(config.DATA_DIR, exist_ok=True)
    os.makedirs(config.MODELS_DIR, exist_ok=True)

    model_path = config.ML_CONFIG["model_path"]

    if args.export:
        print(f"Exporting data for labeling (Total Limit: {args.limit})...")

        # 1. Clear existing to_label.csv if it exists to start fresh
        if os.path.exists(config.LABEL_CSV):
            os.remove(config.LABEL_CSV)

        # 2. Export indexed pages (potential good/bad mix from DB)
        # We'll take 40% from DB and 60% from rejected logs for a balanced mix
        db_limit = int(args.limit * config.ML_EXPORT_DB_RATIO)
        rejected_limit = args.limit - db_limit

        print(f"Sampling {db_limit} pages from indexed content...")
        export_indexed_pages(config.LABEL_CSV, limit=db_limit)

        print(f"Sampling up to {rejected_limit} pages from rejected URLs...")
        augment_from_rejected_urls(config.LABEL_CSV, limit=rejected_limit)

        print("\nNext steps:")
        print(f"1. Open {config.LABEL_CSV}")
        print("2. Review and label the 'quality' column with 'good' or 'bad'")
        print("   (Note: Rejected URLs are pre-filled as 'bad')")
        print("3. Run: uv run python -m provoke.ml.trainer --train")

    elif args.train:
        print("Preparing training data...")
        create_fasttext_training_file(config.LABEL_CSV, config.TRAINING_DATA_FILE)

        split_training_data(
            config.TRAINING_DATA_FILE,
            config.TRAIN_SPLIT_FILE,
            config.TEST_SPLIT_FILE,
            test_ratio=config.ML_TEST_RATIO,
        )

        print("\nTraining model...")
        model = train_fasttext_model(
            config.TRAIN_SPLIT_FILE,
            model_path,
            lr=config.ML_LEARNING_RATE,
            epoch=config.ML_EPOCHS,
            wordNgrams=config.ML_WORD_NGRAMS,
        )

        if model:
            print("\nEvaluating on test set...")
            evaluate_model(model_path, config.TEST_SPLIT_FILE)
            print(f"\nTraining complete! Model saved to {model_path}")

    elif args.evaluate:
        print("Evaluating model...")
        evaluate_model(model_path, config.TEST_SPLIT_FILE)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
