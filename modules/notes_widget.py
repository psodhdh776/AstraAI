from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QScrollArea, QLineEdit, QGraphicsDropShadowEffect,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from modules.theme import (
    C_BG, C_SURFACE, C_SURFACE2, C_SURFACE3,
    C_ACCENT, C_ACCENT2, C_ACCENT_GLOW, C_SECONDARY,
    C_TEXT, C_TEXT2, C_TEXT3, C_BORDER, C_BORDER2,
    C_GLASS, C_GLASS2, C_GLASS_HOVER,
    C_GRADIENT_1, C_GRADIENT_2, C_SUCCESS, C_ERROR, C_WARNING, C_INFO,
)


class NoteCard(QFrame):
    def __init__(self, note_data, on_toggle, on_delete):
        super().__init__()
        self.note_data = note_data
        self.on_toggle = on_toggle
        self.on_delete = on_delete
        self.setObjectName("card")
        done = note_data.get("done", False)
        border = f"{C_SUCCESS}35" if done else C_BORDER
        self.setStyleSheet(f"""
            QFrame#card {{
                background: {C_GLASS};
                border: 1px solid {border};
                border-radius: 10px;
            }}
            QFrame#card:hover {{
                border-color: {C_ACCENT};
            }}
        """)
        glow = QGraphicsDropShadowEffect()
        glow.setBlurRadius(16)
        glow.setColor(QColor(0, 0, 0, 40))
        glow.setOffset(0, 2)
        self.setGraphicsEffect(glow)

        l = QHBoxLayout(self)
        l.setContentsMargins(12, 10, 12, 10)
        l.setSpacing(10)

        self.check_btn = QPushButton("✓" if done else "○")
        self.check_btn.setFixedSize(28, 28)
        cc = C_SUCCESS if done else C_TEXT3
        self.check_btn.setStyleSheet(f"""
            QPushButton {{
                background: {"transparent" if not done else f"{C_SUCCESS}15"};
                border: 2px solid {cc};
                border-radius: 14px;
                font-size: 11px;
                color: {cc};
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: {C_ACCENT}12;
                border-color: {C_ACCENT};
            }}
        """)
        self.check_btn.clicked.connect(lambda: self.on_toggle(self))
        l.addWidget(self.check_btn)

        text_l = QLabel(note_data["text"])
        text_l.setWordWrap(True)
        text_l.setStyleSheet(f"""
            font-size: 13px; color: {C_TEXT if not done else C_TEXT3};
            background: transparent;
            {"text-decoration: line-through;" if done else ""}
        """)
        l.addWidget(text_l, 1)

        time_l = QLabel(note_data.get("created", ""))
        time_l.setStyleSheet(f"font-size: 10px; color: {C_TEXT3}; background: transparent;")
        l.addWidget(time_l)

        del_btn = QPushButton("✕")
        del_btn.setFixedSize(26, 26)
        del_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: none;
                color: {C_TEXT3}; font-size: 11px;
                border-radius: 13px;
            }}
            QPushButton:hover {{ background: {C_ERROR}20; color: {C_ERROR}; }}
        """)
        del_btn.clicked.connect(lambda: self.on_delete(self))
        l.addWidget(del_btn)


class NotesWidget(QWidget):
    def __init__(self, assistant):
        super().__init__()
        self.assistant = assistant
        self.setStyleSheet("background: transparent;")

        l = QVBoxLayout(self)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(0)

        header = QWidget()
        header.setStyleSheet(f"background: {C_GLASS}; border-bottom: 1px solid {C_BORDER};")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(18, 8, 18, 8)

        title = QLabel("📝 Заметки")
        title.setStyleSheet(f"font-size:14px;font-weight:700;color:#ffffff;background:transparent;")
        hl.addWidget(title)
        hl.addStretch()

        self.counter = QLabel("0 активных")
        self.counter.setStyleSheet(f"font-size:11px;color:{C_TEXT3};background:transparent;")
        hl.addWidget(self.counter)
        hl.addSpacing(8)

        clear_done = QPushButton("✕ готовые")
        clear_done.setStyleSheet(f"""
            QPushButton{{
                background:transparent;border:1px solid {C_BORDER};border-radius:5px;
                padding:4px 10px;font-size:10px;color:{C_TEXT3};
            }}
            QPushButton:hover{{border-color:{C_ERROR};color:{C_ERROR};}}
        """)
        clear_done.setToolTip("Очистить готовые заметки")
        clear_done.clicked.connect(self._clear_done)
        hl.addWidget(clear_done)

        l.addWidget(header)

        inp_row = QWidget()
        inp_row.setStyleSheet(f"background:{C_GLASS};border-bottom:1px solid {C_BORDER};")
        il = QHBoxLayout(inp_row)
        il.setContentsMargins(18, 6, 18, 10)

        self.input = QLineEdit()
        self.input.setPlaceholderText("Новая заметка...")
        self.input.setMinimumHeight(36)
        self.input.returnPressed.connect(self._add)
        self.input.setStyleSheet(f"QLineEdit{{background:{C_SURFACE2};border:1px solid {C_BORDER};border-radius:8px;padding:0 12px;font-size:13px;color:{C_TEXT};}} QLineEdit:focus{{border:1px solid {C_ACCENT};}}")
        il.addWidget(self.input)

        self.add_btn = QPushButton("+")
        self.add_btn.setStyleSheet(f"""
            QPushButton{{
                background:{C_ACCENT};color:white;
                border:none;border-radius:8px;
                padding:0 16px;font-weight:700;
                min-height:36px;font-size:16px;
            }}
            QPushButton:hover{{background:{C_ACCENT2};}}
        """)
        self.add_btn.clicked.connect(self._add)
        il.addWidget(self.add_btn)

        l.addWidget(inp_row)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")

        sc = QWidget()
        sc.setStyleSheet("background:transparent;")
        self.notes_layout = QVBoxLayout(sc)
        self.notes_layout.setContentsMargins(20, 12, 20, 12)
        self.notes_layout.setSpacing(6)
        self.notes_layout.addStretch()

        self.scroll.setWidget(sc)
        l.addWidget(self.scroll)

        self._refresh()

    def _refresh(self):
        for i in reversed(range(self.notes_layout.count() - 1)):
            item = self.notes_layout.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        for n in reversed(self.assistant.notes):
            card = NoteCard(n, self._toggle, self._delete)
            self.notes_layout.insertWidget(0, card)

        active = len([n for n in self.assistant.notes if not n["done"]])
        self.counter.setText(f"{active} активных, {len(self.assistant.notes)} всего")

    def _add(self):
        t = self.input.text().strip()
        if t:
            self.assistant.notes.append({
                "id": str(datetime.now().timestamp()),
                "text": t,
                "created": datetime.now().strftime("%d.%m.%Y %H:%M"),
                "done": False,
            })
            self.assistant._save_notes()
            self.input.clear()
            self._refresh()

    def _toggle(self, card):
        nid = card.note_data["id"]
        for note in self.assistant.notes:
            if note["id"] == nid:
                note["done"] = not note["done"]
                break
        self.assistant._save_notes()
        self._refresh()

    def _delete(self, card):
        nid = card.note_data["id"]
        self.assistant.notes[:] = [n for n in self.assistant.notes if n["id"] != nid]
        self.assistant._save_notes()
        self._refresh()

    def _clear_done(self):
        self.assistant.notes[:] = [n for n in self.assistant.notes if not n["done"]]
        self.assistant._save_notes()
        self._refresh()
