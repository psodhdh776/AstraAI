"""Base classes for the plugin system."""
import importlib.util
import inspect
import os
import datetime
from pathlib import Path


class Plugin:
    """Base class for all command plugins."""

    name: str = ""
    keywords: list[str] = []
    weight: float = 1.0
    description: str = ""
    cooldown_seconds: float = 0

    def __init__(self):
        self._last_used = datetime.datetime.min

    def is_on_cooldown(self):
        if self.cooldown_seconds <= 0:
            return False
        elapsed = (datetime.datetime.now() - self._last_used).total_seconds()
        return elapsed < self.cooldown_seconds

    def mark_used(self):
        self._last_used = datetime.datetime.now()

    def extract_params(self, text: str, tl: str):
        return None

    def execute(self, params, assistant):
        raise NotImplementedError

    def format_response(self, result: str) -> str:
        return result


class PluginManager:
    """Discovers, loads, and scores plugins against user input."""

    def __init__(self):
        self.plugins: list[Plugin] = []

    def _add(self, plugin):
        """Add a plugin, avoiding duplicates by name."""
        if not any(p.name == plugin.name for p in self.plugins):
            self.plugins.append(plugin)

    def load_builtins(self, assistant):
        """Load built-in command plugins from assistant methods."""
        self._builtins = assistant
        from .plugins_core import get_core_plugins
        for p in get_core_plugins(assistant):
            self._add(p)

    def load_directory(self, directory: str):
        """Scan a directory for plugin files and load them."""
        path = Path(directory)
        if not path.exists():
            return
        for f in sorted(path.iterdir()):
            if f.suffix != ".py" or f.name.startswith("_"):
                continue
            try:
                spec = importlib.util.spec_from_file_location(f.stem, f)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    for name, obj in inspect.getmembers(mod):
                        if (inspect.isclass(obj) and issubclass(obj, Plugin)
                                and obj is not Plugin):
                            self._add(obj())
            except Exception as e:
                print(f"[plugin] Failed to load {f.name}: {e}")

    def match(self, text: str, tl: str, context: dict | None = None) -> list[dict]:
        """Score all plugins against the input text and return ranked results."""
        scored = []
        for plugin in self.plugins:
            if plugin.is_on_cooldown():
                continue
            score = 0
            for kw in plugin.keywords:
                if kw in tl:
                    score += 1
            if score > 0:
                final_score = (score / max(len(plugin.keywords), 1)) * plugin.weight

                if context and context.get("last_intent") == plugin.name:
                    final_score += 0.15

                for kw in plugin.keywords:
                    if tl == kw or tl.startswith(kw + " ") or tl.endswith(" " + kw) or (" " + kw + " ") in (" " + tl + " "):
                        final_score += 0.5
                        break

                params = plugin.extract_params(text, tl)
                scored.append({
                    "name": plugin.name,
                    "score": min(1.0, final_score),
                    "plugin": plugin,
                    "params": params,
                })

        scored.sort(key=lambda x: -x["score"])
        return scored
