import pytest
from modules.plugins_core import (
    _extract_after, _extract_weather_city, _parse_remind, fmt
)


class TestExtractAfter:
    def test_basic(self):
        result = _extract_after("напечатай hello world", ["напечатай"])
        assert result == "hello world"

    def test_no_match(self):
        result = _extract_after("hello world", ["test"])
        assert result is None

    def test_strips_punctuation(self):
        result = _extract_after("найди, привет!", ["найди"])
        assert result == "привет!"

    def test_short_after(self):
        result = _extract_after("найди a", ["найди"])
        assert result is None

    def test_case_sensitive_preserved(self):
        result = _extract_after("скажи Hello World", ["скажи"])
        assert result == "Hello World"

    def test_empty_text(self):
        assert _extract_after("", ["test"]) is None


class TestExtractWeatherCity:
    def test_in_city(self):
        assert _extract_weather_city("погода в Москве", "погода в москве") == "Москве"

    def test_na_city(self):
        assert _extract_weather_city("погода на завтра в Питере", "погода на завтра в питере") == "завтра"

    def test_no_city(self):
        assert _extract_weather_city("погода", "погода") is None

    def test_v_gorode(self):
        assert _extract_weather_city("погода в Казани", "погода в казани") == "Казани"


class TestParseRemind:
    def test_through_minutes(self):
        result = _parse_remind("через 10 минут купить хлеб", "через 10 минут купить хлеб")
        assert result is not None
        num, text = result
        assert num == "10"
        assert "купить хлеб" in text

    def test_polchasa(self):
        result = _parse_remind("напомни через полчаса встречу", "напомни через полчаса встречу")
        assert result is not None
        num, text = result
        assert num == "30"
        assert "встречу" in text

    def test_chas(self):
        result = _parse_remind("через час позвонить", "через час позвонить")
        assert result is not None
        num, text = result
        assert num == "60"

    def test_no_match(self):
        assert _parse_remind("привет", "привет") is None


class TestFmt:
    def test_known_template(self):
        result = fmt("time", "12:00")
        assert "12:00" in result

    def test_unknown_template(self):
        result = fmt("nonexistent", "raw")
        assert result == "raw"

    def test_screenshot_template(self):
        result = fmt("screenshot", "done.png")
        assert "done.png" in result

    def test_weather_template(self):
        result = fmt("weather", "солнечно, +25")
        assert "солнечно, +25" in result
