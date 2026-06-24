import pytest
from modules.search import search_history, search_notes, highlight


class TestSearchHistory:
    def test_empty_query(self):
        assert search_history([{"text": "hello"}], "") == []

    def test_basic_match(self):
        history = [{"role": "user", "text": "hello world", "time": "12:00"}]
        results = search_history(history, "hello")
        assert len(results) == 1
        assert results[0]["role"] == "user"
        assert results[0]["query"] == "hello"

    def test_case_insensitive(self):
        history = [{"role": "user", "text": "Hello World", "time": "12:00"}]
        results = search_history(history, "hello")
        assert len(results) == 1

    def test_max_results(self):
        history = [{"role": "user", "text": f"msg {i}", "time": f"{i}:00"} for i in range(10)]
        results = search_history(history, "msg", max_results=3)
        assert len(results) == 3

    def test_no_match(self):
        history = [{"role": "user", "text": "hello", "time": "12:00"}]
        assert search_history(history, "xyz") == []

    def test_reverse_order(self):
        history = [{"role": "user", "text": "first", "time": "1"},
                   {"role": "assistant", "text": "second", "time": "2"}]
        results = search_history(history, "second")
        assert len(results) == 1
        assert results[0]["role"] == "assistant"

    def test_content_key_fallback(self):
        history = [{"role": "user", "content": "fallback text", "time": "12:00"}]
        results = search_history(history, "fallback")
        assert len(results) == 1

    def test_empty_history(self):
        assert search_history([], "hello") == []


class TestSearchNotes:
    def test_empty_query(self):
        assert search_notes([{"text": "hello"}], "") == []

    def test_basic_match(self):
        notes = [{"text": "my note"}, {"text": "other"}]
        results = search_notes(notes, "note")
        assert len(results) == 1

    def test_string_notes(self):
        notes = ["hello world", "goodbye"]
        results = search_notes(notes, "world")
        assert len(results) == 1

    def test_no_match(self):
        assert search_notes([{"text": "hello"}], "xyz") == []

    def test_empty_notes(self):
        assert search_notes([], "hello") == []


class TestHighlight:
    def test_no_query_returns_original(self):
        assert highlight("hello world", "") == "hello world"

    def test_basic_highlight(self):
        result = highlight("hello world", "hello")
        assert "<b style=" in result
        assert "hello</b>" in result

    def test_case_insensitive_highlight(self):
        result = highlight("Hello World", "hello")
        assert "Hello</b>" in result

    def test_no_match_returns_original(self):
        assert highlight("hello", "xyz") == "hello"
