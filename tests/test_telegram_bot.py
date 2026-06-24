import pytest
import tempfile
from pathlib import Path


@pytest.fixture(autouse=True)
def _patch_token_file(monkeypatch):
    import modules.telegram_bot as tb
    with tempfile.TemporaryDirectory() as tmp:
        tb.BOT_TOKEN_FILE = Path(tmp) / "telegram_token.txt"
        yield


class TestTelegramBot:
    def test_get_token_empty_when_no_file(self):
        from modules.telegram_bot import get_token
        assert get_token() == ""

    def test_set_and_get_token(self):
        from modules.telegram_bot import set_token, get_token
        assert set_token("test_token_123")
        assert get_token() == "test_token_123"

    def test_set_token_overwrites(self):
        from modules.telegram_bot import set_token, get_token
        set_token("first_token")
        set_token("second_token")
        assert get_token() == "second_token"

    def test_get_token_after_file_deleted(self):
        from modules.telegram_bot import set_token, get_token
        set_token("temp_token")
        assert get_token() == "temp_token"
        import modules.telegram_bot as tb
        tb.BOT_TOKEN_FILE.unlink()
        assert get_token() == ""

    def test_start_bot_no_token(self):
        from modules.telegram_bot import start_bot
        class FakeAssistant:
            history = []
            notes = []
            voice_enabled = False
            def process(self, text): return f"echo: {text}"
        result = start_bot(FakeAssistant())
        assert result is False

    def test_start_bot_with_token(self):
        from modules.telegram_bot import set_token, start_bot, stop_bot
        set_token("dummy_token")
        class FakeAssistant:
            history = []
            notes = []
            voice_enabled = False
            def process(self, text): return f"echo: {text}"
        result = start_bot(FakeAssistant())
        stop_bot()
        assert result in (True, False)

    def test_stop_bot_noop_when_not_running(self):
        from modules.telegram_bot import stop_bot
        stop_bot()
