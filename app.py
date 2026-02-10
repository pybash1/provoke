from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import csv
import os
import re
import json
from collections import Counter
from urllib.parse import urlparse
from indexer import SearchEngine

app = Flask(__name__)
engine = SearchEngine()


@app.route("/")
def index():
    query = request.args.get("q", "")
    results = []
    if query:
        results = engine.search(query)

    return render_template("index.html", query=query, results=results)


def get_lists():
    conn = sqlite3.connect("index.db")
    cursor = conn.cursor()
    cursor.execute("SELECT domain FROM blacklisted_domains")
    blacklisted = [row[0] for row in cursor.fetchall()]
    cursor.execute("SELECT domain FROM whitelisted_domains")
    whitelisted = [row[0] for row in cursor.fetchall()]
    conn.close()
    return blacklisted, whitelisted


def get_admin_data():
    conn = sqlite3.connect("index.db")
    cursor = conn.cursor()

    # Ensure tables exist and handle migrations
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS whitelisted_domains (domain TEXT PRIMARY KEY)"
    )

    # Get stats
    cursor.execute("SELECT COUNT(*) FROM pages")
    total_pages = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM blacklisted_domains")
    total_blacklisted = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM whitelisted_domains")
    total_whitelisted = cursor.fetchone()[0]

    # Tier distribution
    cursor.execute("SELECT quality_tier, COUNT(*) FROM pages GROUP BY quality_tier")
    tier_counts = {row[0]: row[1] for row in cursor.fetchall()}

    # Tier ordering for UI
    tier_labels = ["high", "medium", "low"]
    tier_values = [tier_counts.get(t, 0) for t in tier_labels]

    # Top Domains
    cursor.execute("SELECT url FROM pages")
    domain_counter = Counter()
    for (url,) in cursor.fetchall():
        domain_counter[urlparse(url).netloc.lower()] += 1
    top_domains = sorted(domain_counter.items(), key=lambda x: x[1], reverse=True)[:10]

    # Get recent indexed pages
    cursor.execute(
        "SELECT url, title, quality_tier, quality_score FROM pages ORDER BY id DESC LIMIT 50"
    )

    recent_pages = []
    for row in cursor.fetchall():
        raw_score = row[3]
        display_score = raw_score
        try:
            if isinstance(raw_score, str) and "{" in raw_score:
                score_data = json.loads(raw_score)
                display_score = score_data.get("unified_score", raw_score)
        except:
            pass

        recent_pages.append(
            {
                "url": row[0],
                "title": row[1],
                "tier": row[2],
                "score": display_score,
            }
        )

    # Accepted pages metrics
    cursor.execute("SELECT quality_score FROM pages")
    rows = cursor.fetchall()
    accepted_wc = []
    accepted_tr = []
    accepted_readability = []
    accepted_unified = []
    for (q_score_raw,) in rows:
        try:
            if q_score_raw and isinstance(q_score_raw, str) and "{" in q_score_raw:
                data = json.loads(q_score_raw)
                accepted_wc.append(data.get("word_count", 0))
                accepted_tr.append(data.get("text_ratio", 0))
                accepted_readability.append(data.get("readability", 0))
                accepted_unified.append(data.get("unified_score", 0))
            elif q_score_raw is not None:
                accepted_unified.append(float(q_score_raw))
        except:
            pass

    conn.close()

    # Rejection Stats
    rejection_counts = Counter()
    total_rejected = 0
    rejected_word_counts = []
    rejected_text_ratios = []
    if os.path.exists("quality_stats.csv"):
        with open("quality_stats.csv", "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                total_rejected += 1
                reasons_raw = row.get("rejection_reasons", "")
                if reasons_raw:
                    for r in [r.strip() for r in reasons_raw.split(",")]:
                        normalized_r = re.sub(r"\s*\(.*?\)", "", r)
                        if normalized_r in [
                            "Weak personal blog identity signals",
                            "Has blog schema",
                            "Has date indicators",
                            "Content length out of range",
                            "Title matched common phrase",
                        ]:
                            normalized_r = "Deprecated filters"
                        if normalized_r:
                            rejection_counts[normalized_r] += 1
                try:
                    wc = int(row.get("word_count", 0))
                    if wc > 0:
                        rejected_word_counts.append(wc)
                    tr = float(row.get("text_ratio", 0))
                    if tr > 0:
                        rejected_text_ratios.append(tr)
                except:
                    pass

    avg_rejected_wc = (
        sum(rejected_word_counts) / len(rejected_word_counts)
        if rejected_word_counts
        else 0
    )
    avg_rejected_tr = (
        sum(rejected_text_ratios) / len(rejected_text_ratios)
        if rejected_text_ratios
        else 0
    )
    sorted_rejections = sorted(
        rejection_counts.items(), key=lambda x: x[1], reverse=True
    )

    # Labeling Progress
    done_labels = 0
    pending_labels = 0
    if os.path.exists("data/to_label.csv"):
        with open("data/to_label.csv", "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Skip corrupted rows
                if None in row:
                    continue
                if not all(k in row for k in ["url", "title", "snippet", "quality"]):
                    continue

                q = (row.get("quality") or "").strip().lower()

                # Skip rows with corrupted quality field
                if len(q) > 50:
                    continue

                if q in ["good", "bad", "unsure"]:
                    done_labels += 1
                else:
                    pending_labels += 1

    return {
        "total_pages": total_pages,
        "total_blacklisted": total_blacklisted,
        "total_whitelisted": total_whitelisted,
        "total_rejected": total_rejected,
        "efficiency": (
            round(total_pages / (total_pages + total_rejected) * 100, 1)
            if (total_pages + total_rejected) > 0
            else 0
        ),
        "recent_pages": recent_pages,
        "rejection_labels": [x[0] for x in sorted_rejections],
        "rejection_values": [x[1] for x in sorted_rejections],
        "tier_labels": tier_labels,
        "tier_values": tier_values,
        "top_domains_labels": [x[0] for x in top_domains],
        "top_domains_values": [x[1] for x in top_domains],
        "avg_wc": int(sum(accepted_wc) / len(accepted_wc)) if accepted_wc else 0,
        "avg_tr": round(sum(accepted_tr) / len(accepted_tr), 3) if accepted_tr else 0,
        "avg_readability": (
            int(sum(accepted_readability) / len(accepted_readability))
            if accepted_readability
            else 0
        ),
        "avg_unified": (
            int(sum(accepted_unified) / len(accepted_unified))
            if accepted_unified
            else 0
        ),
        "avg_rejected_wc": int(avg_rejected_wc),
        "avg_rejected_tr": round(avg_rejected_tr, 3),
        "pending_labels": pending_labels,
        "done_labels": done_labels,
        "labeling_progress": (
            round(done_labels / (pending_labels + done_labels) * 100, 1)
            if (pending_labels + done_labels) > 0
            else 0
        ),
    }


def get_domain_info(target_domain=None):
    import sqlite3
    from urllib.parse import urlparse

    conn = sqlite3.connect("index.db")
    cursor = conn.cursor()

    # Get all URLs to extract domains
    cursor.execute("SELECT url, title, quality_tier, quality_score FROM pages")
    rows = cursor.fetchall()

    domains_map = {}
    for url, title, tier, score in rows:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain not in domains_map:
            domains_map[domain] = []
        domains_map[domain].append(
            {"url": url, "title": title, "tier": tier, "score": score}
        )

    unique_domains = sorted(list(domains_map.keys()))

    pages = []
    if target_domain and target_domain in domains_map:
        pages = domains_map[target_domain]

    conn.close()
    return unique_domains, pages


@app.route("/domains")
def domains():
    selected_domain = request.args.get("domain")
    unique_domains, pages = get_domain_info(selected_domain)
    return render_template(
        "domains.html",
        domains=unique_domains,
        pages=pages,
        selected_domain=selected_domain,
    )


@app.route("/admin")
def admin():
    data = get_admin_data()
    return render_template("admin.html", **data)


@app.route("/admin/lists")
def admin_lists():
    blacklisted, whitelisted = get_lists()
    return render_template(
        "lists.html", blacklisted_domains=blacklisted, whitelisted_domains=whitelisted
    )


@app.route("/api/stats")
def api_stats():
    from flask import jsonify

    data = get_admin_data()
    blacklisted, whitelisted = get_lists()
    data["blacklisted_domains"] = blacklisted
    data["whitelisted_domains"] = whitelisted
    return jsonify(data)


@app.route("/admin/test_url")
def test_url():
    from flask import jsonify, request
    import requests
    from bs4 import BeautifulSoup
    from quality_filter import evaluate_page_quality

    url = request.args.get("url")
    if not url:
        return jsonify({"error": "URL is required"}), 400

    try:
        # Simple fetch (no dynamic for dry run to keep it fast)
        # Use a real user agent to avoid basic bot blocks
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, timeout=10, headers=headers)
        response.raise_for_status()
        html = response.text

        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.string if soup.title else url
        text = soup.get_text(separator=" ", strip=True)

        # Get whitelist for context
        _, whitelisted = get_lists()

        # Evaluate
        result = evaluate_page_quality(
            url, html, text, whitelist=whitelisted, force_ml=True
        )

        return jsonify(
            {
                "url": url,
                "title": str(title),
                "is_acceptable": result["is_acceptable"],
                "quality_tier": result["quality_tier"],
                "rejection_reasons": result["rejection_reasons"],
                "scores": result["scores"],
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/admin/blacklist", methods=["POST"])
def blacklist_add():
    domain = request.form.get("domain", "").strip().lower()
    if domain:
        import sqlite3

        conn = sqlite3.connect("index.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO blacklisted_domains (domain) VALUES (?)", (domain,)
        )
        conn.commit()
        conn.close()

    return redirect(url_for("admin_lists"))


@app.route("/admin/blacklist/remove", methods=["POST"])
def blacklist_remove():
    domain = request.form.get("domain", "").strip()
    if domain:
        import sqlite3

        conn = sqlite3.connect("index.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM blacklisted_domains WHERE domain = ?", (domain,))
        conn.commit()
        conn.close()

    return redirect(url_for("admin_lists"))


@app.route("/admin/whitelist", methods=["POST"])
def whitelist_add():
    domain = request.form.get("domain", "").strip().lower()
    if domain:
        import sqlite3

        conn = sqlite3.connect("index.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO whitelisted_domains (domain) VALUES (?)",
            (domain,),
        )
        conn.commit()
        conn.close()

    return redirect(url_for("admin_lists"))


@app.route("/admin/whitelist/remove", methods=["POST"])
def whitelist_remove():
    domain = request.form.get("domain", "").strip()
    if domain:
        import sqlite3

        conn = sqlite3.connect("index.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM whitelisted_domains WHERE domain = ?", (domain,))
        conn.commit()
        conn.close()

    return redirect(url_for("admin_lists"))


@app.route("/admin/delete_page", methods=["POST"])
def delete_page():
    url = request.form.get("url")
    if not url:
        return "URL is required", 400

    import sqlite3
    import csv
    import os

    conn = sqlite3.connect("index.db")
    cursor = conn.cursor()

    # Get page data before deleting
    cursor.execute("SELECT title, content FROM pages WHERE url = ?", (url,))
    row = cursor.fetchone()

    if row:
        title, content = row
        # Clean up description/snippet
        snippet = (content or "").replace("\n", " ").replace("\r", " ").strip()
        if len(snippet) > 300:
            snippet = snippet[:297] + "..."

        # Update to_label.csv
        csv_path = "data/to_label.csv"
        # Ensure directory exists
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)

        # Check for duplicates
        urls_in_csv = set()
        if os.path.exists(csv_path):
            try:
                with open(csv_path, "r", newline="", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for r in reader:
                        urls_in_csv.add(r.get("url"))
            except Exception as e:
                print(f"Error reading CSV: {e}")

        if url not in urls_in_csv:
            file_exists = os.path.isfile(csv_path) and os.path.getsize(csv_path) > 0
            with open(csv_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(["url", "title", "snippet", "quality"])
                writer.writerow([url, title, snippet, "bad"])

        # Delete from database
        cursor.execute("DELETE FROM pages WHERE url = ?", (url,))
        conn.commit()

    conn.close()

    # Redirect back to the referrer or domains
    referrer = request.referrer or url_for("domains")
    return redirect(referrer)


@app.route("/admin/crawl")
def admin_crawl():
    url = request.args.get("url")
    depth = request.args.get("depth", "1")

    if not url:
        return "URL is required", 400

    from flask import Response, stream_with_context
    import subprocess
    import sys

    def generate():
        # Use python -u for unbuffered output
        cmd = [sys.executable, "-u", "crawler.py", url, str(depth)]
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
        )

        if process.stdout:
            for line in iter(process.stdout.readline, ""):
                # Flask will buffer if we don't yield enough or if the line is short
                # But for a log viewer, we want line by line
                yield line

        process.wait()
        yield "\n[CRAWL COMPLETE]\n"

    return Response(stream_with_context(generate()), mimetype="text/plain")


@app.route("/admin/label")
def label_ui():
    csv_path = "data/to_label.csv"
    if not os.path.exists(csv_path):
        return "No items to label", 404

    unlabeled_item = None
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Skip rows with None keys (corrupted CSV structure)
            if None in row:
                continue

            # Check if row has all required fields
            if not all(k in row for k in ["url", "title", "snippet", "quality"]):
                continue

            # Get quality field safely
            q = (row.get("quality") or "").strip().lower()

            # Skip if quality field contains snippet text (corrupted data)
            if len(q) > 50:
                continue

            # Found an unlabeled item
            if q not in ["good", "bad", "unsure"]:
                unlabeled_item = row
                break

    return render_template("label.html", item=unlabeled_item)


@app.route("/api/label", methods=["POST"])
def api_label():
    data = request.json
    url = data.get("url")
    label = data.get("label")

    csv_path = "data/to_label.csv"
    rows = []
    updated = False
    fieldnames = ["url", "title", "snippet", "quality"]

    if os.path.exists(csv_path):
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Skip corrupted rows with None keys
                if None in row:
                    continue

                # Ensure row has all required fields
                if not all(k in row for k in fieldnames):
                    continue

                # Skip rows with corrupted quality field (contains snippet text)
                q = (row.get("quality") or "").strip()
                if len(q) > 50:
                    continue

                # Update the matching URL
                if row["url"] == url:
                    row["quality"] = label
                    updated = True

                rows.append(row)

    if updated:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    # Find next unlabeled item
    next_item = None
    for row in rows:
        q = (row.get("quality") or "").strip().lower()
        if q not in ["good", "bad", "unsure"]:
            next_item = row
            break

    return {"success": updated, "next_item": next_item}


if __name__ == "__main__":
    app.run(debug=True, port=4000)
