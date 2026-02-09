import csv
import os

INPUT_FILE = "data/to_label.csv"
OUTPUT_FILE = "data/to_label.csv"


def main():
    if not os.path.exists(INPUT_FILE):
        print(f"File {INPUT_FILE} not found.")
        return

    rows = []
    fieldnames = []
    updated_count = 0

    # Read existing data
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            url = row.get("url", "")
            original_quality = row.get("quality", "")

            # Check for dotink.co
            if "dotink.co" in url:
                if original_quality != "good":
                    row["quality"] = "good"
                    updated_count += 1

            rows.append(row)

    # Write back
    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Processed {len(rows)} rows.")
    print(f"Updated {updated_count} rows containing 'dotink.co' to 'good'.")


if __name__ == "__main__":
    main()
