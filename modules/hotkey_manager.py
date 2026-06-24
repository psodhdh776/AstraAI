"""
Configurable hotkey manager.
"""
import json
import logging
from pathlib import Path

logger = logging.getLogger("Astra.Hotkeys")

DEFAULT_HOTKEYS = {
    "show_window": "Ctrl+Shift+A",
    "voice_toggle": "Ctrl+Shift+V",
    "tts_toggle": "Ctrl+Shift+T",
    "screenshot": "Ctrl+Shift+S",
    "search": "Ctrl+Shift+F",
    "quick_note": "Ctrl+Shift+N",
    "toggle_widgets": "Ctrl+Shift+W",
}


class HotkeyManager:
    def __init__(self):
        self._path = Path(__file__).parent.parent / "data" / "hotkeys.json"
        self._hotkeys = dict(DEFAULT_HOTKEYS)
        self._callbacks = {}
        self.load()

    @property
    def hotkeys(self):
        return dict(self._hotkeys)

    def get(self, action):
        return self._hotkeys.get(action, DEFAULT_HOTKEYS.get(action, ""))

    def set(self, action, shortcut):
        self._hotkeys[action] = shortcut
        self.save()
        logger.info("Hotkey %s -> %s", action, shortcut)

    def register(self, action, callback):
        self._callbacks[action] = callback

    def on_trigger(self, shortcut_str):
        action = self._find_action(shortcut_str)
        if action and action in self._callbacks:
            self._callbacks[action]()

    def _find_action(self, shortcut):
        for action, val in self._hotkeys.items():
            if val.lower() == shortcut.lower():
                return action
        return None

    def save(self):
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps(self._hotkeys, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning("Save hotkeys: %s", e)

    def load(self):
        try:
            if self._path.exists():
                data = json.loads(self._path.read_text(encoding="utf-8"))
                self._hotkeys.update(data)
        except Exception as e:
            logger.warning("Load hotkeys: %s", e)


_global = HotkeyManager()


def get_manager():
    return _global


def get(action):
    return _global.get(action)


def set_hotkey(action, shortcut):
    _global.set(action, shortcut)
