"""
Desktop widgets — transparent overlay windows for weather, clock, quote.
"""
import logging
import threading
import time
from datetime import datetime

logger = logging.getLogger("Astra.Widgets")

try:
    from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QApplication
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QFont, QPainter, QColor, QPen
    HAS_QT = True
except ImportError:
    HAS_QT = False


class WidgetWindow(QWidget):
    def __init__(self, title, width=280, height=120):
        super().__init__()
        self.setWindowTitle(title)
        self.setFixedSize(width, height)
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint |
            Qt.Tool | Qt.X11BypassWindowManagerHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setAlignment(Qt.AlignCenter)

        self.label = QLabel()
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setWordWrap(True)
        self.label.setStyleSheet("color: rgba(248, 250, 252, 0.9); font-size: 14px; background: transparent;")
        font = QFont("Segoe UI", 13)
        font.setBold(True)
        self.label.setFont(font)
        layout.addWidget(self.label)

        self._pressed = False
        self._drag_pos = None

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        c = QColor(12, 12, 26, 180)
        p.setBrush(c)
        p.setPen(QPen(QColor(99, 102, 241, 40), 1))
        p.drawRoundedRect(self.rect().adjusted(2, 2, -2, -2), 16, 16)
        p.end()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._pressed = True
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            e.accept()

    def mouseMoveEvent(self, e):
        if self._pressed and e.buttons() == Qt.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos)
            e.accept()

    def mouseReleaseEvent(self, e):
        self._pressed = False

    def set_content(self, text):
        self.label.setText(text)


class DesktopWidgets:
    def __init__(self):
        self._windows = []

    def show_clock(self, x=20, y=20):
        if not HAS_QT:
            return
        w = WidgetWindow("Часы", 200, 80)
        w.move(x, y)
        w.show()
        self._windows.append(("clock", w))
        self._update_clock()
        return w

    def _update_clock(self):
        for name, w in self._windows:
            if name == "clock":
                now = datetime.now()
                w.set_content(
                    f'<span style="font-size:32px;">{now.strftime("%H:%M")}</span><br>'
                    f'<span style="font-size:11px;color:rgba(100,116,139,0.8);">{now.strftime("%d %B %Y")}</span>'
                )
        QTimer.singleShot(1000, self._update_clock)

    def hide_all(self):
        for _, w in self._windows:
            w.hide()
        self._windows.clear()

    def toggle(self, name):
        existing = [w for n, w in self._windows if n == name]
        if existing:
            if existing[0].isVisible():
                existing[0].hide()
            else:
                existing[0].show()
            return
        if name == "clock":
            self.show_clock()
