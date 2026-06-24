"""
First-run wizard — guides user through initial setup.
"""
import logging
from pathlib import Path

logger = logging.getLogger("Astra.Wizard")

try:
    from PySide6.QtWidgets import (
        QWizard, QWizardPage, QLabel, QVBoxLayout, QRadioButton,
        QCheckBox, QLineEdit, QComboBox, QPushButton,
    )
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFont, QPixmap
    HAS_QT = True
except ImportError:
    HAS_QT = False

_FLAG_PATH = Path(__file__).parent.parent / "data" / ".first_run_done"


def is_first_run():
    return not _FLAG_PATH.exists()


def mark_done():
    _FLAG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _FLAG_PATH.touch()


if HAS_QT:

    class WelcomePage(QWizardPage):
        def __init__(self):
            super().__init__()
            self.setTitle("Добро пожаловать в Astra AI!")
            layout = QVBoxLayout()
            lbl = QLabel(
                "Astra AI — ваш персональный голосовой ассистент.\n\n"
                "Давайте настроим его вместе. Это займёт минуту."
            )
            lbl.setWordWrap(True)
            lbl.setStyleSheet("font-size: 14px; color: #e2e8f0;")
            layout.addWidget(lbl)
            self.setLayout(layout)

    class VoicePage(QWizardPage):
        def __init__(self):
            super().__init__()
            self.setTitle("Голосовой ввод")
            layout = QVBoxLayout()
            self.use_voice = QCheckBox("Включить голосовой ввод (микрофон)")
            self.use_voice.setChecked(True)
            self.use_wake = QCheckBox("Всегда слушать фоново (wake-word 'Астра')")
            self.use_wake.setChecked(False)
            layout.addWidget(self.use_voice)
            layout.addWidget(self.use_wake)
            self.setLayout(layout)

    class ThemePage(QWizardPage):
        def __init__(self):
            super().__init__()
            self.setTitle("Тема оформления")
            layout = QVBoxLayout()
            self.combo = QComboBox()
            self.combo.addItems(["Тёмная (Indigo)", "Киберпанк", "Светлая", "Лесная"])
            layout.addWidget(QLabel("Выберите тему:"))
            layout.addWidget(self.combo)
            self.setLayout(layout)

    class DonePage(QWizardPage):
        def __init__(self):
            super().__init__()
            self.setTitle("Готово!")
            layout = QVBoxLayout()
            lbl = QLabel("Настройка завершена. Нажмите 'Готово' для запуска.")
            lbl.setStyleSheet("font-size: 14px; color: #94a3b8;")
            lbl.setWordWrap(True)
            layout.addWidget(lbl)
            self.setLayout(layout)

    class FirstRunWizard(QWizard):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setWindowTitle("Astra AI — Первый запуск")
            self.setWizardStyle(QWizard.ModernStyle)
            self.setMinimumSize(500, 400)
            self.setStyleSheet("""
                QWizard { background: #0f0f23; }
                QWizardPage { background: transparent; }
                QLabel { color: #e2e8f0; }
                QCheckBox { color: #cbd5e1; font-size: 13px; spacing: 8px; }
                QComboBox { background: #1e1e3f; color: #e2e8f0; border: 1px solid #334155; border-radius: 6px; padding: 6px 12px; }
            """)
            self.addPage(WelcomePage())
            self.voice_page = VoicePage()
            self.addPage(self.voice_page)
            self.theme_page = ThemePage()
            self.addPage(self.theme_page)
            self.addPage(DonePage())

        def get_config(self):
            return {
                "voice_enabled": self.voice_page.use_voice.isChecked(),
                "voice_24": self.voice_page.use_wake.isChecked(),
                "theme_index": self.theme_page.combo.currentIndex(),
            }
else:

    class FirstRunWizard:
        def __init__(self, parent=None):
            pass

        def exec_(self):
            mark_done()
            return True
