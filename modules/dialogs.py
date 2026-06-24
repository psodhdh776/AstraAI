import json
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QListWidget, QListWidgetItem, QCheckBox, QComboBox,
    QFormLayout, QDialogButtonBox, QInputDialog, QFileDialog, QMessageBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QKeySequence, QShortcut

from modules.theme import (
    C, C_BG, C_SURFACE, C_SURFACE2, C_BORDER,
    C_TEXT, C_TEXT2, C_TEXT3, C_ACCENT, C_ACCENT2, C_SUCCESS, C_ERROR,
    C_WARNING, C_GRADIENT_1, C_GRADIENT_2, C_GLASS,
)


class SettingsDialog(QDialog):
    def __init__(self, assistant):
        super().__init__()
        self.assistant = assistant
        self.setWindowTitle("Настройки")
        self.setFixedSize(450, 400)
        self.setStyleSheet(C.build_qss())

        l = QVBoxLayout(self)
        l.setSpacing(14)
        l.setContentsMargins(24, 24, 24, 24)

        title = QLabel("⚙️  Настройки")
        title.setObjectName("header")
        l.addWidget(title)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight)

        self.voice_cb = QCheckBox("Голосовой вывод (TTS)")
        self.voice_cb.setChecked(assistant.voice_enabled)
        form.addRow("🔊", self.voice_cb)

        self.wakeword_edit = QLineEdit("астра")
        self.wakeword_edit.setPlaceholderText("Слово для активации")
        form.addRow("🗣 Wake-word", self.wakeword_edit)

        sep = QLabel("─" * 36)
        sep.setStyleSheet(f"color: {C_BORDER}; background: transparent;")
        form.addRow("", sep)

        self.auto_start_cb = QCheckBox("Автозапуск при входе в Windows")
        self.auto_start_cb.setChecked(assistant.get_auto_start())
        form.addRow("🚀", self.auto_start_cb)

        backup_btn = QPushButton("💾 Создать резервную копию")
        backup_btn.setMinimumHeight(34)
        backup_btn.setCursor(Qt.PointingHandCursor)
        backup_btn.clicked.connect(self._do_backup)
        form.addRow("", backup_btn)

        restore_btn = QPushButton("📂 Восстановить из копии")
        restore_btn.setMinimumHeight(34)
        restore_btn.setCursor(Qt.PointingHandCursor)
        restore_btn.clicked.connect(self._do_restore)
        form.addRow("", restore_btn)

        export_btn = QPushButton("📄 Экспорт в JSON")
        export_btn.setMinimumHeight(34)
        export_btn.setCursor(Qt.PointingHandCursor)
        export_btn.clicked.connect(self._do_export)
        form.addRow("", export_btn)

        l.addLayout(form)
        l.addStretch()

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._save)
        btns.rejected.connect(self.reject)
        l.addWidget(btns)

    def _save(self):
        voice = self.voice_cb.isChecked()
        auto_start = self.auto_start_cb.isChecked()
        wakeword = self.wakeword_edit.text().strip().lower()
        self.assistant.voice_enabled = voice
        self.assistant.save_config(voice_enabled=voice)
        self.assistant.set_auto_start(auto_start)
        if wakeword and hasattr(self.assistant, '_voice_engine'):
            ve = self.assistant._voice_engine
            if hasattr(ve, '_wake_word'):
                ve._wake_word = wakeword
        self.accept()

    def _do_backup(self):
        if not self.assistant.db:
            QMessageBox.warning(self, "Ошибка", "База данных не подключена")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить резервную копию",
            str(Path.home() / f"astra_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"),
            "SQLite (*.db)")
        if path:
            try:
                result = self.assistant.db.backup(path)
                QMessageBox.information(self, "Готово", f"✅ Резервная копия сохранена:\n{result}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"❌ {e}")

    def _do_restore(self):
        path, _ = QFileDialog.getOpenFileName(self, "Выбрать резервную копию",
            str(Path.home()), "SQLite (*.db)")
        if path:
            try:
                self.assistant.db.close()
                import shutil
                shutil.copy2(path, self.assistant.db.db_path)
                self.assistant.db = type(self.assistant.db)(self.assistant.db.db_path)
                QMessageBox.information(self, "Готово", "✅ База данных восстановлена")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"❌ {e}")

    def _do_export(self):
        if not self.assistant.db:
            QMessageBox.warning(self, "Ошибка", "База данных не подключена")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Экспорт данных",
            str(Path.home() / f"astra_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"),
            "JSON (*.json)")
        if path:
            try:
                result = self.assistant.db.export_json(path)
                QMessageBox.information(self, "Готово", f"✅ Данные экспортированы:\n{result}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"❌ {e}")


class CommandPalette(QDialog):
    def __init__(self, parent, main_window):
        super().__init__(parent)
        self.main_window = main_window
        self.setWindowTitle("Команды")
        self.setFixedSize(500, 400)
        self.setStyleSheet(f"""
            QDialog {{
                background: {C_SURFACE};
                border: 1px solid {C_BORDER};
                border-radius: 14px;
            }}
        """)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        self.commands = self._build_commands()

        l = QVBoxLayout(self)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(0)

        header = QWidget()
        header.setStyleSheet(
            f"background: {C_SURFACE2}; border-radius: 14px 14px 0 0; "
            f"border-bottom: 1px solid {C_BORDER};"
        )
        hl = QHBoxLayout(header)
        hl.setContentsMargins(14, 10, 14, 10)
        icon_l = QLabel("🔍")
        icon_l.setStyleSheet("font-size: 15px; background: transparent;")
        hl.addWidget(icon_l)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск команд...")
        self.search.setStyleSheet(f"""
            QLineEdit {{
                background: transparent; border: none;
                font-size: 14px; color: {C_TEXT};
                padding: 4px 0;
            }}
        """)
        self.search.textChanged.connect(self._filter)
        hl.addWidget(self.search, 1)
        shortcut_l = QLabel("Ctrl+K")
        shortcut_l.setStyleSheet(
            f"color: {C_TEXT3}; font-size: 10px; background: transparent; "
            f"padding: 3px 6px; border: 1px solid {C_BORDER}; border-radius: 4px;"
        )
        hl.addWidget(shortcut_l)
        l.addWidget(header)

        self.list = QListWidget()
        self.list.setStyleSheet(f"""
            QListWidget {{
                background: {C_SURFACE}; border: none;
                border-radius: 0 0 14px 14px;
                padding: 4px;
            }}
            QListWidget::item {{
                padding: 8px 14px; border-radius: 6px; margin: 1px 4px;
            }}
            QListWidget::item:hover {{ background: {C_SURFACE2}; }}
            QListWidget::item:selected {{ background: {C_ACCENT}25; color: {C_TEXT}; }}
        """)
        self.list.itemClicked.connect(self._execute)
        self.list.activated.connect(self._execute)
        l.addWidget(self.list)

        self._populate()

        self.search.setFocus()
        QShortcut(QKeySequence("Down"), self).activated.connect(lambda: self._move(1))
        QShortcut(QKeySequence("Up"), self).activated.connect(lambda: self._move(-1))
        QShortcut(QKeySequence("Escape"), self).activated.connect(self.close)

    def _build_commands(self):
        mw = self.main_window
        return [
            ("💬", "Перейти в чат", "Навигация", lambda: self._go(0)),
            ("📝", "Перейти в заметки", "Навигация", lambda: self._go(1)),
            ("🖥", "Перейти в монитор", "Навигация", lambda: self._go(2)),
            ("🗑", "Очистить чат", "Действия", lambda: mw.chat._clear_chat()),
            ("📷", "Снимок экрана", "Действия", lambda: mw.sys._screenshot()),
            ("🔄", "Обновить систему", "Действия", lambda: mw.sys._update()),
            ("⚙️", "Открыть настройки", "Действия", lambda: mw.chat._open_settings()),
            ("🔔", "Напомнить через 5 мин", "Напоминания", lambda: self._quick_remind(5)),
            ("🔔", "Напомнить через 15 мин", "Напоминания", lambda: self._quick_remind(15)),
            ("🔔", "Напомнить через 30 мин", "Напоминания", lambda: self._quick_remind(30)),
            ("🔔", "Напомнить через 1 час", "Напоминания", lambda: self._quick_remind(60)),
            ("🍅", "Фокус 25 мин", "Таймер", lambda: mw._start_pomodoro(25)),
            ("☕", "Перерыв 5 мин", "Таймер", lambda: mw._start_pomodoro(5)),
            ("⏹", "Остановить таймер", "Таймер", lambda: mw._stop_pomodoro()),
            ("📝", "Быстрая заметка", "Заметки", self._quick_note),
            ("📋", "Показать заметки", "Заметки", lambda: self._go(1)),
            ("❓", "Помощь / команды", "Справка", lambda: self._send_cmd("помощь")),
        ]

    def _go(self, idx):
        self.main_window.sidebar.buttons[idx].click()
        self.main_window.stack.setCurrentIndex(idx)
        self.accept()

    def _quick_remind(self, minutes):
        self.accept()
        text, ok = QInputDialog.getText(
            self, "Напоминание", f"Что напомнить через {minutes} мин?"
        )
        if ok and text.strip():
            self.main_window.assistant.add_reminder(text.strip(), minutes)
            self.main_window.chat.add_message(
                "system", f"🔔 Напомню через {minutes} мин: {text.strip()}"
            )

    def _quick_note(self):
        self.accept()
        text, ok = QInputDialog.getText(self, "Быстрая заметка", "Текст заметки:")
        if ok and text.strip():
            n = {
                "id": str(datetime.now().timestamp()),
                "text": text.strip(),
                "created": datetime.now().strftime("%d.%m.%Y %H:%M"),
                "done": False,
            }
            self.main_window.assistant.notes.append(n)
            self.main_window.assistant._save_notes()
            self.main_window.notes._refresh()
            self.main_window.chat.add_message("system", "📝 Заметка добавлена")

    def _send_cmd(self, cmd):
        self.main_window.chat.input_field.setText(cmd)
        self.main_window.chat._send()
        self.accept()

    def _populate(self, filter_text=""):
        self.list.clear()
        ft = filter_text.lower()
        for icon, text, cat, cb in self.commands:
            if ft and ft not in text.lower() and ft not in cat.lower():
                continue
            item = QListWidgetItem(f"  {icon}  {text}")
            item.setData(Qt.UserRole, cb)
            self.list.addItem(item)

    def _filter(self, text):
        self._populate(text)
        if self.list.count() > 0:
            self.list.setCurrentRow(0)

    def _move(self, direction):
        r = self.list.currentRow()
        if r < 0:
            r = 0
        r = (r + direction) % max(1, self.list.count())
        self.list.setCurrentRow(r)

    def _execute(self, index):
        item = self.list.currentItem()
        if item:
            cb = item.data(Qt.UserRole)
            if cb:
                self.accept()
                cb()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return and self.list.currentItem():
            self._execute(None)
            return
        super().keyPressEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        self.search.setFocus()
        self.search.selectAll()
