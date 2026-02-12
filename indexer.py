#!/usr/bin/env python3
"""
Backward-compatible shim for provoke.indexer

The SearchEngine class has moved to the provoke package.
This file is maintained for backward compatibility.
"""

from provoke.indexer import SearchEngine

__all__ = ["SearchEngine"]

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
