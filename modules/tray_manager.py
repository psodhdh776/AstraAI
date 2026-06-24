"""
Global hotkey + system tray manager.

Регистрирует Ctrl+Alt+A для:
  1. Показа/скрытия окна
  2. Запуска голосового ввода (если зажата голосовая кнопка)

Системный трей с меню:
  - Показать/Скрыть
  - Голосовой ввод (вкл/выкл)
  - Быстрая заметка
  - Тихий режим
  - О программе
  - Выход
"""

import ctypes
import ctypes.wintypes
import threading
import logging

logger = logging.getLogger("Astra.Hotkey")

# ── Windows API constants ──
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312

# ── Global hotkey IDs ──
HK_SHOW_WINDOW = 1
HK_VOICE = 2
HK_TTS = 3


class TrayManager:
    def __init__(self, main_window, assistant):
        self.window = main_window
        self.assistant = assistant
        self._hotkey_thread = None
        self._running = False

    def register_hotkeys(self):
        try:
            hwnd = int(self.window.winId())
            user32 = ctypes.windll.user32

            # Ctrl+Alt+A → показать окно
            if not user32.RegisterHotKey(hwnd, HK_SHOW_WINDOW, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, ord('A')):
                logger.warning("Hotkey Ctrl+Alt+A registration failed")

            # Ctrl+Alt+V → голосовой ввод
            if not user32.RegisterHotKey(hwnd, HK_VOICE, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, ord('V')):
                logger.warning("Hotkey Ctrl+Alt+V registration failed")

            # Ctrl+Alt+T → TTS вкл/выкл
            if not user32.RegisterHotKey(hwnd, HK_TTS, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, ord('T')):
                logger.warning("Hotkey Ctrl+Alt+T registration failed")

            logger.info("Global hotkeys registered: Ctrl+Alt+A (show), Ctrl+Alt+V (voice), Ctrl+Alt+T (TTS toggle)")
            return True
        except Exception as e:
            logger.error("Hotkey registration failed: %s", e)
            return False

    def unregister_hotkeys(self):
        try:
            hwnd = int(self.window.winId())
            user32 = ctypes.windll.user32
            user32.UnregisterHotKey(hwnd, HK_SHOW_WINDOW)
            user32.UnregisterHotKey(hwnd, HK_VOICE)
            user32.UnregisterHotKey(hwnd, HK_TTS)
        except Exception as e:
            logger.error("Hotkey unregister failed: %s", e)

    def handle_hotkey(self, hkid):
        if hkid == HK_SHOW_WINDOW:
            if self.window.isVisible():
                self.window.hide()
            else:
                self.window._show_window()
                self.window.activateWindow()
        elif hkid == HK_VOICE:
            if hasattr(self.window, 'chat') and self.window.chat:
                self.window.chat._toggle_voice()
        elif hkid == HK_TTS:
            self.assistant.voice_enabled = not self.assistant.voice_enabled
            if hasattr(self.window, 'chat') and self.window.chat and hasattr(self.window.chat, 'tts_btn'):
                self.window.chat.tts_btn.setChecked(self.assistant.voice_enabled)

    def build_tray_menu(self, menu):
        menu.clear()

        show_a = menu.addAction("📂 Показать")
        show_a.triggered.connect(self.window._show_window)

        hide_a = menu.addAction("🙈 Скрыть")
        hide_a.triggered.connect(self.window.hide)

        menu.addSeparator()

        voice_a = menu.addAction("🎤 Голосовой ввод")
        voice_a.setCheckable(True)
        voice_a.setChecked(self.assistant.voice_enabled)
        voice_a.toggled.connect(self._on_voice_toggled)

        silent_a = menu.addAction("🔇 Тихий режим")
        silent_a.setCheckable(True)
        silent_a.toggled.connect(self._on_silent_toggled)

        menu.addSeparator()

        note_a = menu.addAction("📝 Быстрая заметка")
        note_a.triggered.connect(self._quick_note)

        menu.addSeparator()

        about_a = menu.addAction("ℹ️ О программе")
        about_a.triggered.connect(self.window._about)

        quit_a = menu.addAction("🚪 Выход")
        quit_a.triggered.connect(self.window._quit)

    def _on_voice_toggled(self, checked):
        self.assistant.voice_enabled = checked

    def _on_silent_toggled(self, enabled):
        self.assistant.voice_enabled = not enabled
        if hasattr(self.assistant, 'tts_engine') and self.assistant.tts_engine:
            try:
                self.assistant.tts_engine.setProperty("volume", 0.0 if enabled else 0.9)
            except Exception:
                pass

    def _quick_note(self):
        from PySide6.QtWidgets import QInputDialog, QLineEdit
        text, ok = QInputDialog.getText(
            self.window, "📝 Быстрая заметка",
            "Текст заметки:", QLineEdit.Normal, ""
        )
        if ok and text:
            self.assistant._h_add_note(text)
            if hasattr(self.window, 'chat') and self.window.chat:
                self.window.chat.add_message("system",
                    f"📝 <b>Заметка добавлена:</b> {text}")
