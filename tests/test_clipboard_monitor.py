import pytest
from modules.clipboard_monitor import ClipboardMonitor, URL_PATTERN, PHONE_PATTERN, EMAIL_PATTERN, IP_PATTERN


class TestClipboardPatterns:
    def test_url_pattern(self):
        assert URL_PATTERN.fullmatch("https://example.com")
        assert URL_PATTERN.fullmatch("http://test.ru/path?q=1")
        assert not URL_PATTERN.fullmatch("not a url")

    def test_phone_pattern(self):
        assert PHONE_PATTERN.fullmatch("+7 999 123 45 67")
        assert PHONE_PATTERN.fullmatch("89991234567")
        assert not PHONE_PATTERN.fullmatch("12345")

    def test_email_pattern(self):
        assert EMAIL_PATTERN.fullmatch("test@example.com")
        assert EMAIL_PATTERN.fullmatch("user.name+tag@domain.co.uk")
        assert not EMAIL_PATTERN.fullmatch("not an email")

    def test_ip_pattern(self):
        assert IP_PATTERN.fullmatch("192.168.1.1")
        assert IP_PATTERN.fullmatch("10.0.0.255")
        assert not IP_PATTERN.fullmatch("not.an.ip")


class FakeAssistant:
    history = []
    notes = []
    voice_enabled = False
    _voice_engine = None
    tts_engine = None

    def process(self, text):
        return f"echo: {text}"


class TestClipboardMonitor:
    def setup_method(self):
        self.m = ClipboardMonitor(FakeAssistant())

    def test_init(self):
        assert self.m.enabled is False
        assert self.m._running is False

    def test_detect_type_url(self):
        result = self.m._detect_type("https://example.com")
        assert result is not None
        assert result["type"] == "url"
        assert result["action"] == "open_url"

    def test_detect_type_phone(self):
        result = self.m._detect_type("+7 999 123 45 67")
        assert result is not None
        assert result["type"] == "phone"
        assert result["action"] == "search"

    def test_detect_type_email(self):
        result = self.m._detect_type("user@example.com")
        assert result is not None
        assert result["type"] == "email"
        assert result["action"] == "email"

    def test_detect_type_ip(self):
        result = self.m._detect_type("192.168.1.1")
        assert result is not None
        assert result["type"] == "ip"
        assert result["action"] == "search"

    def test_detect_type_long_text(self):
        result = self.m._detect_type("a " * 30 + "long text " * 10)
        assert result is not None
        assert result["type"] == "long_text"
        assert result["action"] == "note"

    def test_detect_type_short_text(self):
        assert self.m._detect_type("hello") is None

    def test_detect_type_empty(self):
        assert self.m._detect_type("") is None
        assert self.m._detect_type("  ") is None

    def test_detect_type_short_long_text(self):
        assert self.m._detect_type("short text with few words only") is None

    def test_process_action_url(self, monkeypatch):
        urls = []
        monkeypatch.setattr("webbrowser.open", lambda u: urls.append(u))
        result = self.m.process_action({"action": "open_url", "value": "https://example.com"})
        assert result == "🔗 Открываю: https://example.com"
        assert urls == ["https://example.com"]

    def test_process_action_email(self, monkeypatch):
        urls = []
        monkeypatch.setattr("webbrowser.open", lambda u: urls.append(u))
        result = self.m.process_action({"action": "email", "value": "test@example.com"})
        assert result == "✉️ Открываю почту: test@example.com"
        assert "mailto:test@example.com" in urls[0]

    def test_process_action_none(self):
        assert self.m.process_action(None) is None

    def test_process_action_unknown(self):
        assert self.m.process_action({"action": "unknown", "value": "x"}) is None

    def test_skip_next(self):
        self.m._skip_once = False
        self.m.skip_next()
        assert self.m._skip_once is True

    def test_start_stop(self):
        self.m.start()
        assert self.m._running is True
        self.m.stop()
        assert self.m._running is False

    def test_start_idempotent(self):
        self.m.start()
        self.m.start()
        self.m.stop()
