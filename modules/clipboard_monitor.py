"""
Фоновый монитор буфера обмена.

Автоматически определяет:
  - URL → предложить открыть
  - Номер телефона → предложить поиск
  - E-mail → предложить открыть почтовик
  - Числовой код → предложить поиск
  - Длинный текст → предложить создать заметку
"""

import re
import threading
import time
import logging

logger = logging.getLogger("Astra.Clipboard")


URL_PATTERN = re.compile(
    r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
    r'(?:/[-\w$.+!*\'(),;:@&=?~#%]*)*', re.IGNORECASE
)

PHONE_PATTERN = re.compile(
    r'(?:\+7|8)[\s(-]?\d{3}[\s)-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}'
)

EMAIL_PATTERN = re.compile(
    r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
)

IP_PATTERN = re.compile(
    r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
)


class ClipboardMonitor:
    def __init__(self, assistant):
        self.assistant = assistant
        self._running = False
        self._thread = None
        self._last_text = ""
        self._callback = None
        self.enabled = False
        self._skip_once = False

    def start(self, callback=None):
        if self._running:
            return
        self._running = True
        self._callback = callback
        self._thread = threading.Thread(target=self._monitor, daemon=True)
        self._thread.start()
        logger.info("Clipboard monitor started")

    def stop(self):
        self._running = False

    def _get_clipboard(self):
        try:
            import pyperclip
            return pyperclip.paste()
        except Exception:
            import win32clipboard
            try:
                win32clipboard.OpenClipboard()
                data = win32clipboard.GetClipboardData()
                win32clipboard.CloseClipboard()
                return data
            except Exception:
                return ""

    def _detect_type(self, text):
        if not text or len(text.strip()) < 3:
            return None

        text = text.strip()

        if URL_PATTERN.fullmatch(text):
            return {"type": "url", "value": text,
                    "label": "🔗 Открыть ссылку",
                    "action": "open_url"}

        if PHONE_PATTERN.fullmatch(text):
            return {"type": "phone", "value": text,
                    "label": "📞 Набрать номер (поиск)",
                    "action": "search"}

        if EMAIL_PATTERN.fullmatch(text):
            return {"type": "email", "value": text,
                    "label": "✉️ Написать письмо",
                    "action": "email"}

        if IP_PATTERN.fullmatch(text):
            return {"type": "ip", "value": text,
                    "label": "🌐 Что за IP? (поиск)",
                    "action": "search"}

        # Длинный текст → заметка
        if len(text) > 50 and len(text.split()) > 5:
            short = text[:80] + ("..." if len(text) > 80 else "")
            return {"type": "long_text", "value": text,
                    "label": f"📝 Заметка: {short}",
                    "action": "note"}

        return None

    def _monitor(self):
        try:
            import pyperclip
        except Exception:
            self._running = False
            return
        time.sleep(1)
        try:
            self._last_text = pyperclip.paste()
        except Exception:
            self._last_text = ""
            self._running = False
            return

        while self._running:
            try:
                current = pyperclip.paste()
                if current and current != self._last_text:
                    self._last_text = current
                    if self._skip_once:
                        self._skip_once = False
                        continue
                    detected = self._detect_type(current)
                    if detected and self._callback:
                        self._callback(detected)
                time.sleep(1.0)
            except Exception:
                time.sleep(2.0)

    def skip_next(self):
        self._skip_once = True

    def process_action(self, detected):
        if not detected:
            return None
        action = detected.get("action")
        value = detected.get("value")

        if action == "open_url":
            import webbrowser
            webbrowser.open(value)
            return f"🔗 Открываю: {value}"

        elif action == "search":
            if hasattr(self.assistant, "_h_web_search"):
                result = self.assistant._h_web_search(value)
                return result or f"🔍 Ищу: {value}"

        elif action == "note":
            if hasattr(self.assistant, "_h_add_note"):
                result = self.assistant._h_add_note(value)
                return result or f"📝 Заметка: {value[:50]}..."
                return f"📝 Заметка сохранена"

        elif action == "email":
            import webbrowser
            webbrowser.open(f"mailto:{value}")
            return f"✉️ Открываю почту: {value}"

        return None
