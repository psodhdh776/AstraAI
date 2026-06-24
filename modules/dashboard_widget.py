from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QGridLayout,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

import threading
from modules.theme import (
    C_BG, C_SURFACE, C_SURFACE2, C_SURFACE3,
    C_ACCENT, C_ACCENT2, C_SECONDARY,
    C_TEXT, C_TEXT2, C_TEXT3, C_BORDER,
    C_GLASS, C_GLASS2,
    C_GRADIENT_1, C_GRADIENT_2, C_SUCCESS, C_ERROR, C_WARNING, C_INFO,
)
from modules.ui_common import GlassCard


class DashboardWidget(QWidget):
    def __init__(self, assistant, parent_window=None):
        super().__init__()
        self.assistant = assistant
        self._window = parent_window
        self.setStyleSheet("background:transparent;")

        l = QVBoxLayout(self)
        l.setContentsMargins(40, 30, 40, 30)
        l.setAlignment(Qt.AlignTop)

        clock_card = GlassCard()
        cl = QVBoxLayout(clock_card)
        cl.setContentsMargins(24, 20, 24, 20)
        cl.setAlignment(Qt.AlignCenter)

        self._time = QLabel()
        self._time.setStyleSheet(f"font-size:48px;font-weight:700;color:#ffffff;background:transparent;letter-spacing:-1px;")
        self._time.setAlignment(Qt.AlignCenter)
        cl.addWidget(self._time)

        self._date = QLabel()
        self._date.setStyleSheet(f"font-size:14px;color:{C_TEXT3};background:transparent;")
        self._date.setAlignment(Qt.AlignCenter)
        cl.addWidget(self._date)

        self._greeting = QLabel()
        self._greeting.setStyleSheet(f"font-size:18px;color:{C_TEXT2};background:transparent;")
        self._greeting.setAlignment(Qt.AlignCenter)
        cl.addWidget(self._greeting)

        l.addWidget(clock_card)

        welcome = GlassCard()
        wl = QVBoxLayout(welcome)
        wl.setContentsMargins(20, 18, 20, 18)

        h = QLabel("✨ Добро пожаловать в Astra AI")
        h.setStyleSheet(f"font-size:16px;font-weight:700;color:#ffffff;background:transparent;")
        wl.addWidget(h)

        desc = QLabel(
            "Ваш персональный голосовой ассистент с полным offline-режимом.<br>"
            "Я помогу с вопросами, напомню о делах и скрашу вечер беседой."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet(f"font-size:12px;color:{C_TEXT3};background:transparent;line-height:1.6;")
        wl.addWidget(desc)

        l.addWidget(welcome)

        widgets_card = GlassCard()
        wl = QVBoxLayout(widgets_card)
        wl.setContentsMargins(20, 14, 20, 14)

        wh = QLabel("🌤 Виджеты")
        wh.setStyleSheet(f"font-size:14px;font-weight:700;color:{C_TEXT2};background:transparent;")
        wl.addWidget(wh)

        self._weather_lbl = QLabel("Загрузка погоды...")
        self._weather_lbl.setStyleSheet(f"font-size:12px;color:{C_TEXT3};background:transparent;")
        wl.addWidget(self._weather_lbl)

        self._currency_lbl = QLabel("Загрузка курсов...")
        self._currency_lbl.setStyleSheet(f"font-size:12px;color:{C_TEXT3};background:transparent;")
        wl.addWidget(self._currency_lbl)

        self._quote_lbl = QLabel()
        self._quote_lbl.setWordWrap(True)
        self._quote_lbl.setStyleSheet(f"font-size:11px;color:{C_TEXT3};background:transparent;font-style:italic;padding:4px 0;")
        wl.addWidget(self._quote_lbl)

        l.addWidget(widgets_card)

        actions = GlassCard()
        al = QVBoxLayout(actions)
        al.setContentsMargins(20, 18, 20, 18)

        ah = QLabel("🚀 Быстрые действия")
        ah.setStyleSheet(f"font-size:14px;font-weight:700;color:{C_TEXT2};background:transparent;")
        al.addWidget(ah)

        grid = QGridLayout()
        grid.setSpacing(6)

        self._actions = [
            ("💬", "Чат", "Открыть чат", self._go_chat),
            ("✏️", "Заметка", "Быстрая заметка", self._quick_note),
            ("🍅", "Таймер", "Фокус 25 мин", self._start_timer),
            ("📷", "Скриншот", "Снимок экрана", self._screenshot),
            ("🔍", "Поиск", "Поиск в истории", self._open_chat_search),
            ("🎨", "Тема", "Сменить тему", self._switch_theme),
        ]
        for i, (icon, title, desc, cb) in enumerate(self._actions):
            btn = QPushButton(f"  {icon}  {title}")
            btn.setStyleSheet(f"""
                QPushButton {{
                    background:{C_SURFACE2};border:1px solid {C_BORDER};
                    border-radius:10px;padding:16px 12px;font-size:13px;
                    font-weight:600;color:{C_TEXT};
                    text-align:left;
                }}
                QPushButton:hover {{
                    border-color:{C_ACCENT};background:{C_ACCENT}08;
                }}
            """)
            btn.setMinimumHeight(52)
            btn.clicked.connect(cb)
            btn.setCursor(Qt.PointingHandCursor)
            grid.addWidget(btn, i // 3, i % 3)

        al.addLayout(grid)
        l.addWidget(actions)

        status = GlassCard()
        sl = QHBoxLayout(status)
        sl.setContentsMargins(20, 14, 20, 14)

        def _stat(icon, label, val):
            w = QWidget()
            w.setStyleSheet("background:transparent;")
            wl = QVBoxLayout(w)
            wl.setContentsMargins(0, 0, 0, 0)
            wl.setSpacing(2)
            i = QLabel(icon)
            i.setStyleSheet(f"font-size:18px;background:transparent;")
            i.setAlignment(Qt.AlignCenter)
            wl.addWidget(i)
            v = QLabel(val)
            v.setStyleSheet(f"font-size:20px;font-weight:700;color:#ffffff;background:transparent;")
            v.setAlignment(Qt.AlignCenter)
            wl.addWidget(v)
            l2 = QLabel(label)
            l2.setStyleSheet(f"font-size:9px;color:{C_TEXT3};background:transparent;")
            l2.setAlignment(Qt.AlignCenter)
            wl.addWidget(l2)
            return w

        self._stat_msgs = _stat("💬", "Сообщений", "0")
        sl.addWidget(self._stat_msgs)
        sl.addStretch()
        self._stat_notes = _stat("📝", "Заметок", "0")
        sl.addWidget(self._stat_notes)
        sl.addStretch()
        self._stat_plugins = _stat("🧩", "Плагинов", "0")
        sl.addWidget(self._stat_plugins)
        sl.addStretch()
        self._stat_uptime = _stat("📅", "Дней", "0")
        sl.addWidget(self._stat_uptime)

        l.addWidget(status)

        l.addStretch()

        self._widget_timer = QTimer()
        self._widget_timer.timeout.connect(self._refresh_widgets)
        self._widget_timer.start(600000)  # 10 min

        self._timer = QTimer()
        self._timer.timeout.connect(self._update)
        self._timer.start(1000)
        self._update()

    def _update(self):
        now = datetime.now()
        self._time.setText(now.strftime("%H:%M:%S"))
        self._date.setText(now.strftime("%d %B %Y, %A"))
        h = now.hour
        if 5 <= h < 12:
            g = "Доброе утро"
        elif 12 <= h < 18:
            g = "Добрый день"
        elif 18 <= h < 23:
            g = "Добрый вечер"
        else:
            g = "Доброй ночи"
        self._greeting.setText(f"{g}!")

        if self.assistant:
            hist = getattr(self.assistant, "history", [])
            self._stat_msgs.findChildren(QLabel)[1].setText(str(len(hist)))
            notes = getattr(self.assistant, "notes", [])
            self._stat_notes.findChildren(QLabel)[1].setText(str(len(notes)))
            plugs = getattr(self.assistant, "plugins", None)
            if plugs and hasattr(plugs, "plugins"):
                self._stat_plugins.findChildren(QLabel)[1].setText(str(len(plugs.plugins)))

            dates = set()
            for h in hist:
                t = h.get("time", "")
                if t:
                    dates.add(t[:10])
            self._stat_uptime.findChildren(QLabel)[1].setText(str(len(dates)))

    def _refresh_widgets(self):
        from modules.desktop_widgets import get_weather, get_currency, get_random_quote
        def set_w():
            self._quote_lbl.setText(f"💡 {get_random_quote()}")
            t = threading.Thread(target=lambda: self._weather_lbl.setText(f"🌤 {get_weather()}"), daemon=True)
            t.start()
            c = threading.Thread(target=lambda: self._currency_lbl.setText(f"💰 {get_currency()}"), daemon=True)
            c.start()
        threading.Thread(target=set_w, daemon=True).start()

    def _go_chat(self):
        w = self._window
        if w and hasattr(w, 'nav_bar'):
            w.nav_bar.set_current(1)

    def _quick_note(self):
        from PySide6.QtWidgets import QInputDialog
        text, ok = QInputDialog.getMultiLineText(None, "Быстрая заметка", "Текст:")
        if ok and text and self.assistant:
            self.assistant._h_add_note(text)

    def _start_timer(self):
        w = self._window
        if w and hasattr(w, 'nav_bar'):
            w.nav_bar.set_current(3)

    def _screenshot(self):
        if self.assistant:
            self.assistant.process("screenshot")

    def _open_chat_search(self):
        w = self._window
        if w and hasattr(w, 'nav_bar'):
            w.nav_bar.set_current(1)

    def _settings(self):
        from modules.dialogs import SettingsDialog
        d = SettingsDialog(self.assistant)
        d.exec()

    def _switch_theme(self):
        from modules.theme import C
        names = C.theme_names()
        current = C.current
        idx = names.index(current) if current in names else 0
        next_idx = (idx + 1) % len(names)
        next_theme = names[next_idx]
        C.set_theme(next_theme)
        if self._window:
            self._window._refresh_style()
