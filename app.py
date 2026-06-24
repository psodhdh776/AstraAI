#!/usr/bin/env python3
"""
Astra AI — Modern Desktop Assistant
"""

import sys, os, json, time, logging, threading, datetime, ctypes

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("Astra")

# ── Qt imports ──
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QStackedWidget, QSystemTrayIcon, QMenu,
    QInputDialog, QMessageBox, QDialog, QFormLayout, QLineEdit,
    QComboBox, QListWidget, QListWidgetItem,
)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QIcon, QAction, QFont, QDragEnterEvent, QDropEvent

from modules.theme import C, C_BG, C_ACCENT, C_TEXT, C_GLASS, C_BORDER, C_TEXT2

from modules.ui_common import (
    ModernTitleBar, NavBar, ModernStatusBar, AnimatedBackground,
    SlidingStackedWidget,
)
from modules.chat_widget import ChatWidget
from modules.notes_widget import NotesWidget
from modules.system_widget import SystemWidget

from modules.assistant import Assistant
from modules.dashboard_widget import DashboardWidget
from modules.api_server import start_api
from modules.auto_update import check_async as check_update_async, CURRENT_VERSION
from modules.hotkey_manager import get_manager as get_hotkey_manager, HotkeyManager
from modules.first_run_wizard import FirstRunWizard, is_first_run, mark_done
from modules.search import search_history, highlight as search_highlight
from modules.i18n import t, set_lang, get_i18n
from modules.home_assistant import HomeAssistant as HomeAssistantModule
from modules.portable import ensure_dirs
from pathlib import Path

# Ensure portable dirs on startup
ensure_dirs()

def _build_main_style():
    return f"""
QMainWindow, QWidget#central {{
    background-color: {C_BG};
}}
QMenu {{
    background-color: {C_GLASS};
    border: 1px solid {C_BORDER};
    border-radius: 10px;
    padding: 4px;
    color: {C_TEXT};
}}
QMenu::item {{
    padding: 8px 24px;
    border-radius: 6px;
}}
QMenu::item:selected {{
    background-color: {C_ACCENT};
    color: white;
}}
"""
MAIN_STYLE = _build_main_style()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Astra AI")
        self.setMinimumSize(880, 580)
        self.resize(1100, 720)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window | Qt.WindowMinimizeButtonHint)
        self.setAcceptDrops(True)

        self.assistant = Assistant()
        self._voice_24 = None
        self._widgets_overlay = None
        self._ha = HomeAssistantModule()
        self._hotkey_mgr = get_hotkey_manager()
        self._search_results = []

        # First-run wizard
        if is_first_run():
            self._run_wizard()

        self._build_ui()
        self._init_tray()
        self._init_features()
        self._init_api()
        self._init_voice_24()
        self._init_updater()
        self._init_hotkeys()

        self._refresh_style()
        self._round_corners()
        self._init_analytics()
        C.on_change(self._on_theme_change)

        logger.info("MainWindow displayed successfully")

    def _run_wizard(self):
        wiz = FirstRunWizard()
        if wiz.exec() == QDialog.Accepted:
            cfg = wiz.get_config()
            if cfg["voice_enabled"]:
                self.assistant.voice_enabled = True
            if cfg["voice_24"]:
                self._init_voice_24()
            theme_names = ["indigo", "cyberpunk", "light", "forest"]
            if 0 <= cfg["theme_index"] < len(theme_names):
                C.set_theme(theme_names[cfg["theme_index"]])
            mark_done()

    def _refresh_style(self):
        global MAIN_STYLE
        MAIN_STYLE = _build_main_style()
        self.setStyleSheet(MAIN_STYLE + C.build_qss())
        self.nav_bar.refresh_style()
        self.title_bar.refresh_style()
        self.status_bar.refresh_style()

    def _on_theme_change(self, name):
        self._refresh_style()

    def _init_voice_24(self):
        try:
            from modules.voice_24 import VoiceAssistant24
            self._voice_24 = VoiceAssistant24(self.assistant)
            if self._voice_24.start():
                logger.info("24/7 voice listening active")
        except Exception as e:
            logger.warning("24/7 voice: %s", e)

    def _init_updater(self):
        def on_check(info):
            if info.get("has_update"):
                self.tray.showMessage(
                    "Astra AI",
                    f"Доступна новая версия {info['latest']}!\n{info['url']}",
                    QSystemTrayIcon.Information, 8000
                )
        try:
            check_update_async(on_check)
        except Exception:
            pass

    def _init_hotkeys(self):
        hk = self._hotkey_mgr
        hk.register("show_window", lambda: (self.show(), self.raise_(), self.activateWindow()))
        hk.register("voice_toggle", lambda: setattr(self.assistant, 'voice_enabled', not self.assistant.voice_enabled))
        hk.register("tts_toggle", lambda: setattr(self.assistant, 'tts_enabled', not getattr(self.assistant, 'tts_enabled', True)))
        hk.register("screenshot", lambda: self.system_widget.take_screenshot() if hasattr(self.system_widget, 'take_screenshot') else None)
        hk.register("search", lambda: self._on_nav(1) or self.chat_widget._search_input.setFocus() if hasattr(self.chat_widget, '_search_input') else None)
        hk.register("quick_note", self._quick_note)
        hk.register("toggle_widgets", self._toggle_widgets)

    def _toggle_widgets(self):
        if self._widgets_overlay:
            self._widgets_overlay.hide_all()
            self._widgets_overlay = None
        else:
            try:
                from modules.desktop_widgets_overlay import DesktopWidgets
                self._widgets_overlay = DesktopWidgets()
                self._widgets_overlay.show_clock()
            except Exception as e:
                logger.warning("Widgets: %s", e)

    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e: QDropEvent):
        for url in e.mimeData().urls():
            fpath = url.toLocalFile()
            if fpath:
                self._handle_dropped_file(fpath)
        e.acceptProposedAction()

    def _handle_dropped_file(self, fpath):
        try:
            from modules.chat_widget import read_file_content
            content = read_file_content(fpath)
            if content:
                self._on_nav(1)
                self.chat_widget._send_message(f"📄 {Path(fpath).name}:\n{content}")
        except Exception as e:
            logger.warning("Drop file: %s", e)

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.title_bar = ModernTitleBar()
        main_layout.addWidget(self.title_bar)

        self.nav_bar = NavBar()
        main_layout.addWidget(self.nav_bar)

        separator = QWidget()
        separator.setFixedHeight(1)
        separator.setStyleSheet(f"background: {C_BORDER};")
        main_layout.addWidget(separator)

        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack, 1)

        self.dashboard_widget = DashboardWidget(self.assistant, parent_window=self)
        self.chat_widget = ChatWidget(self.assistant)
        self.notes_widget = NotesWidget(self.assistant)
        self.system_widget = SystemWidget(self.assistant)
        from modules.analytics_widget import AnalyticsWidget
        self.analytics_widget = AnalyticsWidget(self.assistant)

        self.stack.addWidget(self.dashboard_widget)
        self.stack.addWidget(self.chat_widget)
        self.stack.addWidget(self.notes_widget)
        self.stack.addWidget(self.system_widget)
        self.stack.addWidget(self.analytics_widget)

        separator2 = QWidget()
        separator2.setFixedHeight(1)
        separator2.setStyleSheet(f"background: {C_BORDER};")
        main_layout.addWidget(separator2)
        self.status_bar = ModernStatusBar()
        self.assistant._status_bar = self.status_bar

        main_layout.addWidget(self.status_bar)

        self.nav_bar.navChanged.connect(self._on_nav)

    def _on_nav(self, idx):
        self.stack.setCurrentIndex(idx)

    def _round_corners(self):
        try:
            hwnd = int(self.winId())
            dll = ctypes.windll.dwmapi
            val = 2
            dll.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(ctypes.c_int(val)), 4)
            margins = ctypes.wintypes.RECT(0, 0, self.width(), self.height())
            dll.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(margins))
        except Exception:
            pass

    def _init_tray(self):
        self.tray = QSystemTrayIcon(self)
        self.tray.setToolTip("Astra AI")

        icon = QIcon()
        from PySide6.QtGui import QPixmap, QPainter, QColor
        pm = QPixmap(64, 64)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QColor(C_ACCENT))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(4, 4, 56, 56, 12, 12)
        p.setPen(QColor("white"))
        f = QFont("Segoe UI", 24, QFont.Bold)
        p.setFont(f)
        p.drawText(pm.rect(), Qt.AlignCenter, "A")
        p.end()
        icon.addPixmap(pm)
        self.tray.setIcon(icon)

        menu = QMenu()

        show_action = QAction("Показать", self)
        show_action.triggered.connect(self.show)
        menu.addAction(show_action)

        hide_action = QAction("Скрыть", self)
        hide_action.triggered.connect(self.hide)
        menu.addAction(hide_action)

        menu.addSeparator()

        voice_action = QAction("🎤 Голосовой ввод", self)
        voice_action.setCheckable(True)
        voice_action.setChecked(self.assistant.voice_enabled)
        voice_action.triggered.connect(lambda v: setattr(self.assistant, "voice_enabled", v))
        menu.addAction(voice_action)

        silent_action = QAction("🔇 Без звука", self)
        silent_action.setCheckable(True)
        silent_action.triggered.connect(lambda v: setattr(self.assistant, "voice_enabled", not v))
        menu.addAction(silent_action)

        menu.addSeparator()

        note_action = QAction("📝 Быстрая заметка", self)
        note_action.triggered.connect(self._quick_note)
        menu.addAction(note_action)

        lang_menu = QMenu("🌐 Язык", self)
        lang_ru = QAction("Русский", self)
        lang_ru.triggered.connect(lambda: self._set_lang("ru"))
        lang_en = QAction("English", self)
        lang_en.triggered.connect(lambda: self._set_lang("en"))
        lang_de = QAction("Deutsch", self)
        lang_de.triggered.connect(lambda: self._set_lang("de"))
        lang_fr = QAction("Français", self)
        lang_fr.triggered.connect(lambda: self._set_lang("fr"))
        lang_menu.addActions([lang_ru, lang_en, lang_de, lang_fr])
        menu.addMenu(lang_menu)

        widgets_action = QAction("🪟 Виджеты (часы)", self)
        widgets_action.setCheckable(True)
        widgets_action.triggered.connect(lambda v: self._toggle_widgets())
        menu.addAction(widgets_action)

        hotkey_action = QAction("⌨ Горячие клавиши", self)
        hotkey_action.triggered.connect(self._show_hotkey_settings)
        menu.addAction(hotkey_action)

        search_action = QAction("🔍 Поиск", self)
        search_action.triggered.connect(lambda: self._show_search())
        menu.addAction(search_action)

        about_action = QAction("ℹ О программе", self)
        about_action.triggered.connect(self._show_about)
        menu.addAction(about_action)

        menu.addSeparator()

        quit_action = QAction("Выход", self)
        quit_action.triggered.connect(self._quit_app)
        menu.addAction(quit_action)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray)
        self.tray.show()

    def _on_tray(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.raise_()
                self.activateWindow()

    def _quick_note(self):
        text, ok = QInputDialog.getMultiLineText(None, "Быстрая заметка", "Текст заметки:")
        if ok and text:
            self.assistant._h_add_note(text)

    def _show_about(self):
        from modules.auto_update import CURRENT_VERSION
        QMessageBox.about(self, "Astra AI",
            f"Astra AI v{CURRENT_VERSION}\n\n"
            "Современный голосовой ассистент\n"
            "с полным offline-режимом.\n\n"
            "• Локальные LLM (llama.cpp/GPT4All)\n"
            "• 4 темы оформления\n"
            "• 4 языка (RU/EN/DE/FR)\n"
            "• 24/7 голосовой ассистент\n"
            "• REST API + Web UI\n"
            "• Telegram бот\n"
            "• Home Assistant интеграция\n"
            "• Десктоп-виджеты\n"
            "• 25 встроенных плагинов"
        )

    def _init_features(self):
        self._last_cb = ""
        self._clipboard_timer = QTimer(self)
        self._clipboard_timer.timeout.connect(self._check_clipboard)
        self._clipboard_timer.start(2000)

        self._reminder_timer = QTimer(self)
        self._reminder_timer.timeout.connect(self._check_reminders)
        self._reminder_timer.start(10000)

        self._sys_timer = QTimer(self)
        self._sys_timer.timeout.connect(self._update_status)
        self._sys_timer.start(3000)

    def _check_clipboard(self):
        try:
            cb = QApplication.clipboard()
            text = cb.text()
            if text and hasattr(self, '_last_cb') and text != self._last_cb and \
               self.assistant and hasattr(self.assistant, 'core') and self.assistant.core:
                self._last_cb = text
        except Exception:
            pass

    def _check_reminders(self):
        if not self.assistant:
            return
        due = self.assistant.get_due_reminders()
        for r in due:
            self.tray.showMessage("Astra AI", f"⏰ {r['text']}", QSystemTrayIcon.Information, 5000)

    def _update_status(self):
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0)
            mem = psutil.virtual_memory()
            self.status_bar.set_sys(
                f"CPU: {cpu:.0f}%  RAM: {mem.used // 1024**3}/{mem.total // 1024**3} GB"
            )
        except Exception:
            pass

    def _set_lang(self, lang):
        set_lang(lang)
        QMessageBox.information(self, "Astra AI",
            "Язык изменён. Перезапустите приложение для полного применения." if lang != "ru"
            else "Language changed. Restart to apply fully." if lang == "en"
            else "Sprache geändert. Neustart erforderlich.")

    def _show_hotkey_settings(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("⌨ Горячие клавиши")
        dlg.setMinimumWidth(400)
        dlg.setStyleSheet(f"background:{C_BG}; color:{C_TEXT};")
        layout = QVBoxLayout(dlg)
        form = QFormLayout()
        hk = self._hotkey_mgr
        edits = {}
        for action, default in HotkeyManager.DEFAULT_HOTKEYS.items():
            le = QLineEdit(hk.get(action))
            le.setPlaceholderText(default)
            le.setStyleSheet(
                "background:#1e1e3f; color:#e2e8f0; border:1px solid #334155; "
                "border-radius:6px; padding:6px 10px; font-size:13px;"
            )
            form.addRow(action + ":", le)
            edits[action] = le
        layout.addLayout(form)
        btn = QPushButton("💾 Сохранить")
        btn.setStyleSheet(
            f"background:{C_ACCENT}; color:white; border:none; "
            "border-radius:8px; padding:10px 24px; font-size:14px; font-weight:bold;"
        )
        def save():
            for action, le in edits.items():
                hk.set(action, le.text())
            dlg.accept()
        btn.clicked.connect(save)
        layout.addWidget(btn)
        dlg.exec()

    def _show_search(self):
        text, ok = QInputDialog.getText(self, "🔍 Поиск", "Запрос:")
        if ok and text:
            history = getattr(self.assistant, 'history', [])
            results = search_history(history, text)
            if not results:
                QMessageBox.information(self, "Поиск", "Ничего не найдено")
                return
            msg = f"Найдено {len(results)} совпадений:\n\n"
            for r in results[:10]:
                snippet = r['text'][:100]
                msg += f"[{r['role']}] {snippet}...\n"
            QMessageBox.information(self, "🔍 Результаты поиска", msg)

    def _init_api(self):
        try:
            self._api_server = start_api(self.assistant)
        except Exception as e:
            logger.warning("API server: %s", e)

    def _init_analytics(self):
        pass

    def _quit_app(self):
        self.tray.hide()
        QApplication.quit()

    def closeEvent(self, e):
        e.ignore()
        self.hide()
        if self.tray:
            self.tray.showMessage("Astra AI", "Приложение свёрнуто в трей", QSystemTrayIcon.Information, 2000)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setQuitOnLastWindowClosed(False)

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
