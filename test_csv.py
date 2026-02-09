import csv

csv_path = "data/to_label.csv"

# Test stats calculation
done_labels = 0
pending_labels = 0
corrupted = 0

with open(csv_path, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        # Skip corrupted rows
        if None in row:
            corrupted += 1
            continue
        if not all(k in row for k in ["url", "title", "snippet", "quality"]):
            corrupted += 1
            continue

        q = (row.get("quality") or "").strip().lower()

        # Skip rows with corrupted quality field
        if len(q) > 50:
            corrupted += 1
            continue

        if q in ["good", "bad", "unsure"]:
            done_labels += 1
        else:
            pending_labels += 1

print(f"Done: {done_labels}")
print(f"Pending: {pending_labels}")
print(f"Corrupted (skipped): {corrupted}")
print(f"Total valid: {done_labels + pending_labels}")
