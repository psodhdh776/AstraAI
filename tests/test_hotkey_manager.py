import pytest
import tempfile
from pathlib import Path
from modules.hotkey_manager import HotkeyManager


@pytest.fixture(autouse=True)
def _patch_hotkey_path(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        yield


class TestHotkeyManager:
    def setup_method(self):
        self.m = HotkeyManager()
        self.m._path = Path(tempfile.mktemp(suffix=".json"))

    def test_default_hotkeys(self):
        h = self.m.hotkeys
        assert h["show_window"] == "Ctrl+Shift+A"
        assert h["voice_toggle"] == "Ctrl+Shift+V"

    def test_get_known(self):
        assert self.m.get("show_window") == "Ctrl+Shift+A"

    def test_get_unknown(self):
        assert self.m.get("nonexistent") == ""

    def test_set(self):
        self.m.set("show_window", "Ctrl+Alt+A")
        assert self.m.get("show_window") == "Ctrl+Alt+A"

    def test_register_and_trigger(self):
        calls = []
        self.m.register("show_window", lambda: calls.append("triggered"))
        self.m.on_trigger("Ctrl+Shift+A")
        assert calls == ["triggered"]

    def test_trigger_unknown_shortcut(self):
        calls = []
        self.m.register("show_window", lambda: calls.append("x"))
        self.m.on_trigger("Nonexistent")
        assert calls == []

    def test_find_action(self):
        assert self.m._find_action("Ctrl+Shift+A") == "show_window"
        assert self.m._find_action("ctrl+shift+a") == "show_window"

    def test_find_action_unknown(self):
        assert self.m._find_action("Ctrl+Alt+Z") is None

    def test_save_and_load(self):
        self.m.set("search", "Ctrl+Alt+F")
        path = self.m._path
        assert path.exists()
        m2 = HotkeyManager()
        m2._path = path
        m2.load()
        assert m2.get("search") == "Ctrl+Alt+F"

    def test_load_missing_file(self):
        m = HotkeyManager()
        m._path = Path("nonexistent_file_123.json")
        m.load()

    def test_property_returns_copy(self):
        h = self.m.hotkeys
        h["show_window"] = "changed"
        assert self.m.get("show_window") == "Ctrl+Shift+A"
