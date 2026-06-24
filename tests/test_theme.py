import pytest
from modules.theme import _ThemeState


class TestTheme:
    def setup_method(self):
        self.t = _ThemeState()

    def test_default_theme(self):
        assert self.t.current == "indigo"

    def test_theme_names(self):
        names = self.t.theme_names()
        assert "indigo" in names
        assert "cyberpunk" in names
        assert "light" in names
        assert "forest" in names

    def test_set_theme(self):
        self.t.set_theme("cyberpunk", notify=False)
        assert self.t.current == "cyberpunk"
        assert self.t.ACCENT == "#00ff88"

    def test_set_theme_light(self):
        self.t.set_theme("light", notify=False)
        assert self.t.current == "light"
        assert self.t.BG == "#f5f5f9"

    def test_set_theme_forest(self):
        self.t.set_theme("forest", notify=False)
        assert self.t.current == "forest"
        assert self.t.ACCENT == "#22c55e"

    def test_unknown_theme(self):
        self.t.set_theme("unknown", notify=False)
        assert self.t.current == "indigo"

    def test_attributes_present(self):
        for attr in ("BG", "SURFACE", "ACCENT", "TEXT", "BORDER",
                     "GRADIENT_1", "GLASS", "GLASS_HOVER"):
            assert hasattr(self.t, attr)

    def test_build_qss_returns_string(self):
        qss = self.t.build_qss()
        assert isinstance(qss, str)
        assert len(qss) > 100
        assert "QWidget" in qss
        assert "QPushButton" in qss
        assert "#0a0a14" in qss

    def test_build_qss_different_theme(self):
        self.t.set_theme("light", notify=False)
        qss = self.t.build_qss()
        assert "#f5f5f9" in qss

    def test_on_change_callback(self):
        calls = []
        self.t.on_change(lambda name: calls.append(name))
        self.t.set_theme("cyberpunk")
        assert len(calls) == 1
        assert calls[0] == "cyberpunk"

    def test_on_change_callback_error_ignored(self):
        calls = []
        self.t.on_change(lambda name: (_ for _ in ()).throw(Exception("cb error")))
        self.t.on_change(lambda name: calls.append(name))
        self.t.set_theme("forest")
        assert len(calls) == 1
        assert calls[0] == "forest"

    def test_set_theme_no_notify(self):
        calls = []
        self.t.on_change(lambda name: calls.append(name))
        self.t.set_theme("cyberpunk", notify=False)
        assert len(calls) == 0
