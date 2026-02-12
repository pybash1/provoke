"""
Provoke: A specialized web crawler and search engine for high-quality personal blog content.
"""

from provoke.config import config, evaluate_page_quality
from provoke.crawler import SimpleCrawler
from provoke.indexer import SearchEngine

__all__ = ["config", "evaluate_page_quality", "SimpleCrawler", "SearchEngine"]
