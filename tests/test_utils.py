import pytest
from modules.utils import _tokenize, _clamp


class TestTokenize:
    def test_empty_string(self):
        assert _tokenize("") == []

    def test_basic_russian(self):
        tokens = _tokenize("привет мир")
        assert "привет" in tokens
        assert "мир" in tokens

    def test_basic_english(self):
        tokens = _tokenize("hello world")
        assert "hello" in tokens
        assert "world" in tokens

    def test_stop_words_removed(self):
        tokens = _tokenize("это просто тест")
        assert "это" not in tokens
        assert "просто" not in tokens
        assert "тест" in tokens

    def test_short_words_removed(self):
        tokens = _tokenize("a an in on")
        assert tokens == []

    def test_mixed_case(self):
        tokens = _tokenize("Привет Мир")
        assert "привет" in tokens
        assert "мир" in tokens

    def test_punctuation(self):
        tokens = _tokenize("привет, мир!")
        assert "привет" in tokens
        assert "мир" in tokens

    def test_numbers_ignored(self):
        tokens = _tokenize("123 456")
        assert tokens == []


class TestClamp:
    def test_within_range(self):
        assert _clamp(0.5) == 0.5

    def test_below_min(self):
        assert _clamp(-0.5) == 0.0

    def test_above_max(self):
        assert _clamp(1.5) == 1.0

    def test_custom_bounds(self):
        assert _clamp(5, 0, 10) == 5
        assert _clamp(-5, 0, 10) == 0
        assert _clamp(15, 0, 10) == 10

    def test_edge_cases(self):
        assert _clamp(0.0) == 0.0
        assert _clamp(1.0) == 1.0
