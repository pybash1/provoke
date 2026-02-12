import sqlite3
import os
import difflib
from provoke.config import config


class SearchEngine:
    def __init__(self, db_file=None):
        self.db_file = db_file or config.DATABASE_PATH
        if not os.path.exists(self.db_file):
            print(f"Warning: {self.db_file} not found. Search results will be empty.")

    def search(self, query):
        if not query:
            return []

        results = []
        try:
            conn = sqlite3.connect(self.db_file)

            # Register a similarity function for fuzzy matching
            def calculate_similarity(s1, s2):
                if not s1 or not s2:
                    return 0
                return difflib.SequenceMatcher(None, s1.lower(), s2.lower()).ratio()

            conn.create_function("similarity", 2, calculate_similarity)
            cursor = conn.cursor()

            # 1. Try Trigram FTS first (fast and handles substrings/partial matches)
            # We use a broad OR search for initial candidates
            words = query.split()
            fts_query = " OR ".join([f'"{word}"' for word in words])

            sql_fts = """
                SELECT 
                    pages.id,
                    pages.title, 
                    pages.url, 
                    snippet(pages_trigram, 1, '<mark>', '</mark>', '...', 32) as snip,
                    rank
                FROM pages_trigram
                JOIN pages ON pages.id = pages_trigram.rowid
                WHERE pages_trigram MATCH ?
                ORDER BY rank
                LIMIT 100
            """

            cursor.execute(sql_fts, (fts_query,))
            fts_rows = cursor.fetchall()

            if fts_rows:
                for row in fts_rows:
                    # Boost score based on title similarity
                    sim_score = calculate_similarity(query, row[1])
                    results.append(
                        {
                            "title": row[1],
                            "url": row[2],
                            "snippet": row[3],
                            "score": round((-row[4] * 0.5) + (sim_score * 10), 2),
                        }
                    )
                # Sort by combined score
                results.sort(key=lambda x: x["score"], reverse=True)

            # 2. If no results or very low confidence, fallback to full-table fuzzy scan
            # Only feasible because the dataset is currently small (around 400-1000 pages)
            if not results or (len(results) < 5 and results[0]["score"] < 5):
                sql_fuzzy = """
                    SELECT title, url, content, similarity(title, ?) as sim
                    FROM pages
                    WHERE sim > 0.3
                    ORDER BY sim DESC
                    LIMIT 20
                """
                cursor.execute(sql_fuzzy, (query,))
                for row in cursor.fetchall():
                    # Check if we already have this URL
                    if any(r["url"] == row[1] for r in results):
                        continue

                    # Generate a simple snippet since we're not using FTS here
                    content = row[2] or ""
                    snippet = content[:160] + "..." if len(content) > 160 else content

                    results.append(
                        {
                            "title": row[0],
                            "url": row[1],
                            "snippet": snippet,
                            "score": round(row[3] * 10, 2),
                        }
                    )

            conn.close()
        except sqlite3.Error as e:
            print(f"SQLite error: {e}")
            return []

        return results


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python indexer.py <query>")
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    engine = SearchEngine()
    results = engine.search(query)

    print(f"Found {len(results)} results for '{query}':")
    for res in results:
        print(f"\n[{res['score']}] {res['title']}")
        print(f"URL: {res['url']}")
        print(f"Snippet: {res['snippet']}")
