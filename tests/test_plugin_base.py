import pytest
import tempfile
from pathlib import Path
from modules.plugin_base import Plugin, PluginManager


class TestPlugin:
    def test_default_attributes(self):
        p = Plugin()
        assert p.name == ""
        assert p.keywords == []
        assert p.weight == 1.0
        assert p.description == ""
        assert p.cooldown_seconds == 0

    def test_is_on_cooldown_no_cooldown(self):
        p = Plugin()
        assert not p.is_on_cooldown()

    def test_cooldown_active(self):
        p = Plugin()
        p.cooldown_seconds = 10
        p.mark_used()
        assert p.is_on_cooldown()

    def test_extract_params_default(self):
        p = Plugin()
        assert p.extract_params("hello", "hello") is None

    def test_execute_raises(self):
        p = Plugin()
        with pytest.raises(NotImplementedError):
            p.execute(None, None)

    def test_format_response_default(self):
        p = Plugin()
        assert p.format_response("test") == "test"


class TestPluginManager:
    def test_init(self):
        pm = PluginManager()
        assert pm.plugins == []

    def test_add_unique(self):
        pm = PluginManager()
        p1 = Plugin()
        p1.name = "test"
        p2 = Plugin()
        p2.name = "test"
        pm._add(p1)
        pm._add(p2)
        assert len(pm.plugins) == 1

    def test_add_different(self):
        pm = PluginManager()
        p1 = Plugin()
        p1.name = "a"
        p2 = Plugin()
        p2.name = "b"
        pm._add(p1)
        pm._add(p2)
        assert len(pm.plugins) == 2

    def test_match_cold(self):
        pm = PluginManager()
        p = Plugin()
        p.name = "test"
        p.keywords = ["hello", "world"]
        p.weight = 1.0
        pm._add(p)
        results = pm.match("hello world", "hello world")
        assert len(results) == 1
        assert results[0]["name"] == "test"
        assert results[0]["score"] > 0

    def test_match_no_keywords(self):
        pm = PluginManager()
        p = Plugin()
        p.name = "test"
        p.keywords = ["hello"]
        pm._add(p)
        results = pm.match("goodbye", "goodbye")
        assert results == []

    def test_match_on_cooldown(self):
        pm = PluginManager()
        p = Plugin()
        p.name = "test"
        p.keywords = ["hello"]
        p.weight = 1.0
        p.cooldown_seconds = 10
        pm._add(p)
        p.mark_used()
        results = pm.match("hello", "hello")
        assert results == []

    def test_match_context_boost(self):
        pm = PluginManager()
        p = Plugin()
        p.name = "test"
        p.keywords = ["hello"]
        p.weight = 1.0
        pm._add(p)
        results = pm.match("hello", "hello", context={"last_intent": "test"})
        assert len(results) == 1
        assert results[0]["score"] > 0.5

    def test_match_exact_keyword_boost(self):
        pm = PluginManager()
        p = Plugin()
        p.name = "test"
        p.keywords = ["hello world"]
        p.weight = 1.0
        pm._add(p)
        results = pm.match("hello world", "hello world")
        assert len(results) == 1

    def test_load_directory_nonexistent(self):
        pm = PluginManager()
        pm.load_directory("/nonexistent/path")

    def test_load_directory_empty(self):
        pm = PluginManager()
        with tempfile.TemporaryDirectory() as tmp:
            pm.load_directory(tmp)
