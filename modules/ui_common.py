from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QHBoxLayout, QVBoxLayout,
    QFrame, QGraphicsDropShadowEffect,
)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, Signal, QRect, QPoint
from PySide6.QtGui import QPainter, QColor, QLinearGradient, QPen, QFont, QBrush

from .theme import (
    C_BG, C_SURFACE, C_SURFACE2, C_SURFACE3,
    C_ACCENT, C_ACCENT2, C_ACCENT_GLOW, C_SECONDARY,
    C_TEXT, C_TEXT2, C_TEXT3, C_BORDER, C_BORDER2,
    C_GLASS, C_GLASS2, C_GLASS_HOVER,
    C_GRADIENT_1, C_GRADIENT_2, C_SUCCESS, C_ERROR, C_WARNING,
)


# ── Glass Card ──
class GlassCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        glow = QGraphicsDropShadowEffect()
        glow.setBlurRadius(24)
        glow.setColor(QColor(0, 0, 0, 60))
        glow.setOffset(0, 4)
        self.setGraphicsEffect(glow)


# ── Modern Title Bar ──
class ModernTitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(36)
        self._pressed = False
        self._drag_pos = QPoint()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(8)

        self.title = QLabel("Astra AI")
        self.title.setStyleSheet(f"""
            font-size: 13px; font-weight: 600;
            color: {C_TEXT2}; letter-spacing: 1px;
            padding: 0;
        """)
        layout.addWidget(self.title)
        layout.addStretch()

        self._title_label = self.title
        self._btn_list = []

        for icon, tip, slot in [
            ("─", "Свернуть", self._minimize),
            ("□", "Развернуть", self._toggle_max),
            ("✕", "Закрыть", self._close),
        ]:
            btn = QPushButton(icon)
            btn.setFixedSize(28, 28)
            btn.setToolTip(tip)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; border: none;
                    border-radius: 6px; font-size: 12px;
                    color: {C_TEXT3};
                }}
                QPushButton:hover {{ background: {C_SURFACE2}; color: {C_TEXT}; }}
            """)
            if icon == "✕":
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent; border: none;
                        border-radius: 6px; font-size: 12px;
                        color: {C_TEXT3};
                    }}
                    QPushButton:hover {{ background: {C_ERROR}; color: white; }}
                """)
            btn.clicked.connect(slot)
            layout.addWidget(btn)
            self._btn_list.append((btn, icon))

    def refresh_style(self):
        self._title_label.setStyleSheet(f"font-size:13px;font-weight:600;color:{C_TEXT2};letter-spacing:1px;padding:0;")
        for btn, icon in self._btn_list:
            if icon == "✕":
                btn.setStyleSheet(f"QPushButton{{background:transparent;border:none;border-radius:6px;font-size:12px;color:{C_TEXT3};}} QPushButton:hover{{background:{C_ERROR};color:white;}}")
            else:
                btn.setStyleSheet(f"QPushButton{{background:transparent;border:none;border-radius:6px;font-size:12px;color:{C_TEXT3};}} QPushButton:hover{{background:{C_SURFACE2};color:{C_TEXT};}}")

    def _minimize(self):
        w = self.window()
        if w:
            w.showMinimized()

    def _toggle_max(self):
        w = self.window()
        if w:
            if w.isMaximized():
                w.showNormal()
            else:
                w.showMaximized()

    def _close(self):
        w = self.window()
        if w:
            w.close()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._pressed = True
            self._drag_pos = e.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
            e.accept()

    def mouseMoveEvent(self, e):
        if self._pressed and e.buttons() == Qt.LeftButton:
            w = self.window()
            if w:
                w.move(e.globalPosition().toPoint() - self._drag_pos)
            e.accept()

    def mouseReleaseEvent(self, e):
        self._pressed = False


# ── Navigation Bar ──
class NavBar(QWidget):
    navChanged = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(56)
        self._buttons = []
        self._current = 0

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignCenter)

        self.items = [
            ("🏠", "Главная"),
            ("💬", "Чат"),
            ("📝", "Заметки"),
            ("🖥", "Система"),
            ("📊", "Аналитика"),
        ]

        for i, (icon, label) in enumerate(self.items):
            btn = QPushButton(f"  {icon}  {label}  ")
            btn.setObjectName("navBtn")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(36)
            btn.clicked.connect(lambda checked, idx=i: self._select(idx))
            layout.addWidget(btn)
            self._buttons.append(btn)

        self._buttons[0].setChecked(True)

    def refresh_style(self):
        for btn in self._buttons:
            checked = btn.isChecked()
            btn.setChecked(not checked)
            btn.setChecked(checked)

    def _select(self, idx):
        if idx == self._current:
            return
        self._buttons[self._current].setChecked(False)
        self._buttons[idx].setChecked(True)
        self._current = idx
        self.navChanged.emit(idx)

    def set_current(self, idx):
        if 0 <= idx < len(self._buttons):
            self._select(idx)


# ── Status Bar ──
class ModernStatusBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(28)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(12)

        self.dot = QLabel("●")
        self.dot.setStyleSheet(f"color: {C_SUCCESS}; font-size: 8px;")
        self.dot.setFixedWidth(12)
        layout.addWidget(self.dot)

        self.status = QLabel("Online")
        self.status.setStyleSheet(f"color: {C_TEXT3}; font-size: 11px;")
        layout.addWidget(self.status)

        self.speaking = QLabel("")
        self.speaking.setStyleSheet(f"color: {C_ACCENT}; font-size: 11px; font-weight: 600;")
        self.speaking.hide()
        layout.addWidget(self.speaking)

        layout.addStretch()

        self.info = QLabel("Astra AI v3.2")
        self.info.setStyleSheet(f"color: {C_TEXT3}; font-size: 11px;")
        layout.addWidget(self.info)

        self.sys = QLabel("")
        self.sys.setStyleSheet(f"color: {C_TEXT3}; font-size: 11px;")
        layout.addWidget(self.sys)

    def set_status(self, text, online=True):
        self.status.setText(text)
        self.dot.setStyleSheet(
            f"color: {C_SUCCESS if online else C_ERROR}; font-size: 8px;"
        )

    def refresh_style(self):
        self.dot.setStyleSheet(f"color: {C_SUCCESS}; font-size: 8px;")
        self.status.setStyleSheet(f"color: {C_TEXT3}; font-size: 11px;")
        self.speaking.setStyleSheet(f"color: {C_ACCENT}; font-size: 11px; font-weight: 600;")
        self.info.setStyleSheet(f"color: {C_TEXT3}; font-size: 11px;")
        self.sys.setStyleSheet(f"color: {C_TEXT3}; font-size: 11px;")

    def set_speaking(self, active):
        if active:
            self.speaking.setText("🔊 Говорю...")
            self.speaking.show()
        else:
            self.speaking.hide()

    def set_info(self, text):
        self.info.setText(text)

    def set_sys(self, text):
        self.sys.setText(text)


# ── Animated Background ──
class AnimatedBackground(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._dots = []
        import random
        for _ in range(40):
            self._dots.append({
                "x": random.randint(0, 2000),
                "y": random.randint(0, 1200),
                "vx": random.uniform(-0.3, 0.3),
                "vy": random.uniform(-0.3, 0.3),
                "r": random.uniform(1.0, 2.5),
                "a": random.uniform(0.1, 0.35),
            })
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(50)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def _tick(self):
        import random
        w = self.width() or 2000
        h = self.height() or 1200
        for d in self._dots:
            d["x"] += d["vx"]
            d["y"] += d["vy"]
            if d["x"] < 0 or d["x"] > w:
                d["vx"] *= -1
                d["x"] = max(0, min(w, d["x"]))
            if d["y"] < 0 or d["y"] > h:
                d["vy"] *= -1
                d["y"] = max(0, min(h, d["y"]))
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        for d in self._dots:
            c = QColor(C_ACCENT)
            c.setAlphaF(d["a"])
            p.setBrush(c)
            p.setPen(Qt.NoPen)
            p.drawEllipse(int(d["x"]), int(d["y"]), int(d["r"] * 2), int(d["r"] * 2))


# ── Sliding Stacked Widget ──
class SlidingStackedWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self._pages = []
        self._current = 0
        self._animating = False

    def addWidget(self, widget):
        widget.setParent(self)
        widget.hide()
        self._pages.append(widget)
        if len(self._pages) == 1:
            widget.show()
            self._layout.addWidget(widget)

    def setCurrentIndex(self, idx):
        if idx == self._current or idx < 0 or idx >= len(self._pages) or self._animating:
            return
        self._animating = True
        old = self._pages[self._current]
        new = self._pages[idx]
        direction = 1 if idx > self._current else -1

        w = self.width()
        new.setGeometry(w * direction, 0, w, self.height())
        new.show()
        new.raise_()

        self._anim_old = QPropertyAnimation(old, b"pos")
        self._anim_old.setDuration(250)
        self._anim_old.setStartValue(QPoint(0, 0))
        self._anim_old.setEndValue(QPoint(-w * direction, 0))
        self._anim_old.setEasingCurve(QEasingCurve.OutCubic)

        self._anim_new = QPropertyAnimation(new, b"pos")
        self._anim_new.setDuration(250)
        self._anim_new.setStartValue(QPoint(w * direction, 0))
        self._anim_new.setEndValue(QPoint(0, 0))
        self._anim_new.setEasingCurve(QEasingCurve.OutCubic)

        self._anim_old.finished.connect(lambda: self._finish_anim(old, new, idx))
        self._anim_old.start()
        self._anim_new.start()

    def _finish_anim(self, old, new, idx):
        old.hide()
        self._layout.addWidget(new)
        self._current = idx
        self._animating = False


# ── Shimmer Loading ──
class ShimmerSkeleton(QFrame):
    def __init__(self, width=200, height=80, parent=None):
        super().__init__(parent)
        self.setFixedSize(width, height)
        self.setStyleSheet(f"background: {C_SURFACE}; border-radius: 12px;")
        self._offset = 0.0
        self._path = None
        self._rect = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(30)

    def _tick(self):
        self._offset = (self._offset + 0.015) % 1.0
        self.update()

    def resizeEvent(self, e):
        self._rect = self.rect()
        self._path = None

    def paintEvent(self, e):
        if not self._rect:
            self._rect = self.rect()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        path = self._path if self._path else self._rect
        grad = QLinearGradient(self._offset * self.width(), 0,
                                self._offset * self.width() + 120, 0)
        c1 = QColor(C_ACCENT)
        c1.setAlphaF(0.05)
        c2 = QColor(C_ACCENT)
        c2.setAlphaF(0.15)
        c3 = QColor(C_ACCENT)
        c3.setAlphaF(0.05)
        grad.setColorAt(0.0, c1)
        grad.setColorAt(0.5, c2)
        grad.setColorAt(1.0, c3)
        p.setBrush(grad)
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(self._rect, 12, 12)
