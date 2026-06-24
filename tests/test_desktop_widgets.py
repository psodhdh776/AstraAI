import pytest
from modules.desktop_widgets import (
    QUOTES_RU, CURRENCY_PAIRS, get_random_quote, get_weather, get_currency
)


class TestDesktopWidgets:
    def test_quotes_list_not_empty(self):
        assert len(QUOTES_RU) > 0

    def test_quotes_format(self):
        for q, a in QUOTES_RU:
            assert isinstance(q, str) and len(q) > 0
            assert isinstance(a, str) and len(a) > 0

    def test_currency_pairs(self):
        assert len(CURRENCY_PAIRS) >= 3
        for pair, name in CURRENCY_PAIRS:
            assert "/" in pair
            assert isinstance(name, str)

    def test_get_random_quote_returns_string(self, monkeypatch):
        monkeypatch.setattr("random.choice", lambda seq: seq[0])
        quote = get_random_quote()
        assert isinstance(quote, str)
        assert "«" in quote
        assert "»" in quote

    def test_get_random_quote_various(self, monkeypatch):
        seen = set()
        for _ in range(len(QUOTES_RU)):
            monkeypatch.setattr("random.choice", lambda seq, i=_: seq[i])
            q = get_random_quote()
            seen.add(q)
        assert len(seen) == len(QUOTES_RU)

    def test_get_weather_network_error(self, monkeypatch):
        def mock_urlopen(*args, **kwargs):
            raise Exception("Network error")
        monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)
        result = get_weather("TestCity")
        assert isinstance(result, str)
        assert "TestCity" in result

    def test_get_weather_success(self, monkeypatch):
        class MockResp:
            def read(self): return b"+15 Sunny 5km/h"
            def __enter__(self): return self
            def __exit__(self, *a): pass
        def mock_urlopen(*args, **kwargs):
            return MockResp()
        monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)
        result = get_weather("Moscow")
        assert "+15" in result

    def test_get_weather_cache(self, monkeypatch):
        import modules.desktop_widgets as dw
        dw._weather_cache = None
        dw._weather_time = 0
        calls = []
        class MockResp:
            def read(self): return b"+10"
            def __enter__(self): return self
            def __exit__(self, *a): pass
        def mock_urlopen(*args, **kwargs):
            calls.append(1)
            return MockResp()
        monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)
        get_weather("City")
        get_weather("City")
        assert len(calls) == 1

    def test_currency_network_error(self, monkeypatch):
        def mock_urlopen(*args, **kwargs):
            raise Exception("Network error")
        monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)
        result = get_currency()
        assert isinstance(result, str)

    def test_currency_success(self, monkeypatch):
        import json
        class MockResp:
            def read(self): return json.dumps({"usd": {"rub": 85.5}}).encode()
            def __enter__(self): return self
            def __exit__(self, *a): pass
        calls = []
        def mock_urlopen(*args, **kwargs):
            calls.append(1)
            return MockResp()
        monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)
        result = get_currency()
        assert "85.5" in result or "доллар" in result
