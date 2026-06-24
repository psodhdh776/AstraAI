"""Tests for semantic engine — TF-IDF, Markov, Self-Learning."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "modules"))

import pytest
from semantic_engine import TfidfEngine


class TestTfidfEngine:
    def setup_method(self):
        self.tfidf = TfidfEngine()

    def test_add_document(self):
        self.tfidf.add_document("привет мир", "greeting")
        assert len(self.tfidf.documents) == 1

    def test_build_and_search(self):
        self.tfidf.add_document("привет как дела", "greeting")
        self.tfidf.add_document("пока до свидания", "farewell")
        self.tfidf.add_document("расскажи шутку", "joke")
        results = self.tfidf.search("привет", top_k=3)
        assert len(results) >= 1

    def test_search_empty_corpus(self):
        results = self.tfidf.search("тест", top_k=5)
        assert results == []

    def test_add_patterns(self):
        patterns = [(r"\bпривет\b", "greeting"), (r"\bпока\b", "farewell")]
        self.tfidf.add_patterns(patterns)
        assert len(self.tfidf.documents) >= 1

    def test_search_ranking(self):
        self.tfidf.add_document("python программирование код", "tech")
        self.tfidf.add_document("python змея животное", "nature")
        results = self.tfidf.search("программирование", top_k=2)
        assert len(results) >= 1
        assert results[0]["label"] == "tech"
