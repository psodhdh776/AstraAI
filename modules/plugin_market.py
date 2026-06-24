"""
Plugin market — install plugins from a repository.
Uses a built-in repo manifest with downloadable plugin packages.
"""

import json
import logging
import os
import shutil
import tempfile
import urllib.request
import urllib.error
from pathlib import Path

logger = logging.getLogger("Astra.PluginMarket")

PLUGIN_DIR = Path(__file__).parent.parent / "plugins"

# ── Built-in repo ──
REPO_MANIFEST = [
    {
        "id": "web_search",
        "name": "Поиск в интернете",
        "version": "1.0.0",
        "description": "Поиск информации через DuckDuckGo или Google",
        "author": "Astra AI",
        "keywords": ["поиск", "найти", "search", "гуглить"],
    },
    {
        "id": "weather",
        "name": "Погода",
        "version": "1.0.0",
        "description": "Прогноз погоды для любого города",
        "author": "Astra AI",
        "keywords": ["погода", "weather", "температура", "град"],
    },
    {
        "id": "calculator",
        "name": "Калькулятор",
        "version": "1.0.0",
        "description": "Математические вычисления и конвертация единиц",
        "author": "Astra AI",
        "keywords": ["калькулятор", "посчитать", "calculator", "math"],
    },
    {
        "id": "reminder",
        "name": "Напоминания",
        "version": "1.1.0",
        "description": "Умные напоминания с контекстным анализом",
        "author": "Astra AI",
        "keywords": ["напомни", "reminder", "не забудь", "запомни"],
    },
    {
        "id": "translate",
        "name": "Переводчик",
        "version": "1.0.0",
        "description": "Перевод текста между языками (через LibreTranslate или локально)",
        "author": "Astra AI",
        "keywords": ["переведи", "translate", "перевод", "translation"],
    },
    {
        "id": "notes_export",
        "name": "Экспорт заметок",
        "version": "1.0.0",
        "description": "Экспорт заметок в TXT, PDF или Markdown",
        "author": "Astra AI",
        "keywords": ["экспорт", "export", "сохранить", "скачать"],
    },
]


def get_available_plugins():
    return REPO_MANIFEST


def get_installed_plugins():
    result = {}
    if PLUGIN_DIR.exists():
        for f in PLUGIN_DIR.iterdir():
            if f.suffix == ".py" and f.stem not in ("__init__", "__pycache__"):
                result[f.stem] = {"name": f.stem, "path": str(f)}
    return result


def install_plugin(plugin_id, api_url="http://127.0.0.1:8741"):
    manifest = {p["id"]: p for p in REPO_MANIFEST}
    if plugin_id not in manifest:
        return {"error": f"Plugin '{plugin_id}' not found in repository"}

    info = manifest[plugin_id]
    PLUGIN_DIR.mkdir(parents=True, exist_ok=True)

    # Generate a stub plugin file
    stub = f'''"""
{info["name"]} — {info["description"]}
Auto-installed from Astra AI Plugin Market
"""

import logging

logger = logging.getLogger("Astra.Plugins.{info["id"]}")

name = "{info["id"]}"
keywords = {json.dumps(info["keywords"])}
description = "{info["description"]}"
version = "{info["version"]}"
author = "{info["author"]}"

def execute(params, assistant):
    """
    {info["description"]}
    """
    return "✅ {info["name"]} установлен. Функция '{info["id"]}' пока не настроена."
'''

    plugin_path = PLUGIN_DIR / f"{plugin_id}.py"
    plugin_path.write_text(stub, encoding="utf-8")
    logger.info("Plugin installed: %s (%s)", info["name"], plugin_path)
    return {"status": "ok", "plugin": plugin_id, "name": info["name"], "path": str(plugin_path)}


def uninstall_plugin(plugin_id):
    plugin_path = PLUGIN_DIR / f"{plugin_id}.py"
    if plugin_path.exists():
        plugin_path.unlink()
        logger.info("Plugin uninstalled: %s", plugin_id)
        return {"status": "ok"}
    return {"error": f"Plugin '{plugin_id}' not installed"}
