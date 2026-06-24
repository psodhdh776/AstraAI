import pytest
import tempfile
from pathlib import Path
from modules.plugin_market import (
    REPO_MANIFEST, get_available_plugins, get_installed_plugins,
    install_plugin, uninstall_plugin
)


class TestPluginMarket:
    def test_repo_manifest_has_plugins(self):
        assert len(REPO_MANIFEST) > 0
        ids = [p["id"] for p in REPO_MANIFEST]
        assert "web_search" in ids
        assert "weather" in ids
        assert "calculator" in ids
        assert "reminder" in ids
        assert "translate" in ids
        assert "notes_export" in ids

    def test_get_available_plugins(self):
        plugins = get_available_plugins()
        assert len(plugins) == len(REPO_MANIFEST)
        assert plugins[0]["id"] == "web_search"

    def test_get_installed_empty(self, monkeypatch):
        import modules.plugin_market as pm
        with tempfile.TemporaryDirectory() as tmp:
            pm.PLUGIN_DIR = Path(tmp)
            result = get_installed_plugins()
            assert result == {}

    def test_install_and_get_installed(self, monkeypatch):
        import modules.plugin_market as pm
        with tempfile.TemporaryDirectory() as tmp:
            pm.PLUGIN_DIR = Path(tmp) / "plugins"
            result = install_plugin("weather")
            assert result["status"] == "ok"
            assert result["plugin"] == "weather"
            installed = get_installed_plugins()
            assert "weather" in installed

    def test_install_unknown_plugin(self):
        result = install_plugin("nonexistent")
        assert "error" in result

    def test_uninstall_plugin(self, monkeypatch):
        import modules.plugin_market as pm
        with tempfile.TemporaryDirectory() as tmp:
            pm.PLUGIN_DIR = Path(tmp) / "plugins"
            install_plugin("translate")
            result = uninstall_plugin("translate")
            assert result["status"] == "ok"
            assert "translate" not in get_installed_plugins()

    def test_uninstall_not_installed(self):
        result = uninstall_plugin("ghost")
        assert "error" in result

    def test_install_stub_content(self, monkeypatch):
        import modules.plugin_market as pm
        with tempfile.TemporaryDirectory() as tmp:
            pm.PLUGIN_DIR = Path(tmp) / "plugins"
            result = install_plugin("calculator")
            plugin_path = Path(result["path"])
            assert plugin_path.exists()
            content = plugin_path.read_text(encoding="utf-8")
            assert "calculator" in content
            assert "Калькулятор" in content
