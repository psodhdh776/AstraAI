import pytest
from modules.home_assistant import HomeAssistant


class TestHomeAssistant:
    def setup_method(self):
        self.ha = HomeAssistant("http://test:8123", "test_token")

    def test_init(self):
        assert self.ha.url == "http://test:8123"
        assert self.ha.token == "test_token"

    def test_set_config(self):
        self.ha.set_config("http://new:8123", "new_token")
        assert self.ha.url == "http://new:8123"
        assert self.ha.token == "new_token"

    def test_url_strips_trailing_slash(self):
        self.ha.set_config("http://test:8123/", "token")
        assert self.ha.url == "http://test:8123"

    def test_headers(self):
        headers = self.ha._headers()
        assert headers["Authorization"] == "Bearer test_token"
        assert headers["Content-Type"] == "application/json"

    def test_get_states_returns_none_on_error(self):
        result = self.ha.get_states()
        assert result is None

    def test_get_entities_returns_none_on_error(self):
        result = self.ha.get_entities("light")
        assert result is None or result == []

    def test_get_weather_returns_none_on_error(self):
        result = self.ha.get_weather()
        assert result is None

    def test_get_sensor_returns_none_on_error(self):
        result = self.ha.get_sensor("sensor.temperature")
        assert result is None

    def test_turn_on(self):
        result = self.ha.turn_on("light.living_room")
        assert result is None

    def test_turn_off(self):
        result = self.ha.turn_off("light.living_room")
        assert result is None

    def test_call_service(self):
        result = self.ha.call_service("light", "turn_on", entity_id="light.test")
        assert result is None

    def test_turn_on_no_domain(self):
        result = self.ha.turn_on("living_room")
        assert result is None
