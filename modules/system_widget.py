from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QScrollArea, QMessageBox, QSystemTrayIcon, QProgressBar,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor

from modules.theme import (
    C_BG, C_SURFACE, C_SURFACE2, C_SURFACE3,
    C_ACCENT, C_ACCENT2, C_ACCENT_GLOW, C_SECONDARY,
    C_TEXT, C_TEXT2, C_TEXT3, C_BORDER, C_BORDER2,
    C_GLASS, C_GLASS2, C_GLASS_HOVER,
    C_GRADIENT_1, C_GRADIENT_2, C_SUCCESS, C_ERROR, C_WARNING, C_INFO,
)
from modules.ui_common import GlassCard


class SysCard(QFrame):
    def __init__(self, icon, label, value, progress=None, color=C_SUCCESS):
        super().__init__()
        self.setObjectName("card")
        self.setStyleSheet(f"""
            QFrame#card {{
                background: {C_GLASS};
                border: 1px solid {C_BORDER};
                border-radius: 12px;
            }}
            QFrame#card:hover {{
                border-color: {color};
            }}
        """)

        l = QVBoxLayout(self)
        l.setContentsMargins(16, 12, 16, 12)
        l.setSpacing(4)

        rh = QHBoxLayout()
        icon_l = QLabel(icon)
        icon_l.setStyleSheet("font-size:18px;background:transparent;")
        rh.addWidget(icon_l)

        label_l = QLabel(label)
        label_l.setStyleSheet(f"font-size:10px;color:{C_TEXT3};font-weight:600;background:transparent;letter-spacing:1px;")
        rh.addWidget(label_l)
        rh.addStretch()
        l.addLayout(rh)

        self._value = QLabel(value)
        self._value.setStyleSheet(f"font-size:22px;font-weight:800;color:{color};background:transparent;letter-spacing:-0.3px;")
        l.addWidget(self._value)

        if progress is not None:
            self._prog = QProgressBar()
            self._prog.setTextVisible(False)
            self._prog.setFixedHeight(3)
            self._prog.setValue(int(progress))
            l.addWidget(self._prog)
        else:
            self._prog = None


class SystemWidget(QWidget):
    def __init__(self, assistant):
        super().__init__()
        self.assistant = assistant
        self.setStyleSheet("background:transparent;")

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")

        content = QWidget()
        content.setStyleSheet("background:transparent;")
        l = QVBoxLayout(content)
        l.setContentsMargins(24, 16, 24, 16)
        l.setSpacing(10)

        header = QLabel("🖥 Монитор Системы")
        header.setStyleSheet(f"font-size:18px;font-weight:700;color:#ffffff;background:transparent;")
        l.addWidget(header)

        sub = QLabel("Мониторинг оборудования в реальном времени")
        sub.setStyleSheet(f"font-size:12px;color:{C_TEXT3};background:transparent;")
        l.addWidget(sub)

        grid = QVBoxLayout()
        grid.setSpacing(6)
        grid.setContentsMargins(0, 0, 0, 0)

        self.cpu_card = SysCard("⚡", "ЦП", "0%", 0, C_ACCENT)
        grid.addWidget(self.cpu_card)

        self.mem_card = SysCard("🧠", "ОЗУ", "0%", 0, C_SUCCESS)
        grid.addWidget(self.mem_card)

        self.disk_card = SysCard("💾", "Диск", "0%", 0, C_INFO)
        grid.addWidget(self.disk_card)

        self.bat_card = SysCard("🔋", "Батарея", "Н/Д", None, C_WARNING)
        grid.addWidget(self.bat_card)

        uptime_card = GlassCard()
        ul = QHBoxLayout(uptime_card)
        ul.setContentsMargins(16, 12, 16, 12)
        uicon = QLabel("⏱")
        uicon.setStyleSheet("font-size:16px;background:transparent;")
        ul.addWidget(uicon)
        self.uptime_label = QLabel("Время работы: загрузка...")
        self.uptime_label.setStyleSheet(f"font-size:12px;color:{C_TEXT3};background:transparent;")
        ul.addWidget(self.uptime_label)
        ul.addStretch()
        grid.addWidget(uptime_card)

        l.addLayout(grid)

        timer_card = GlassCard()
        tl = QVBoxLayout(timer_card)
        tl.setContentsMargins(16, 12, 16, 12)
        tl.setSpacing(6)

        th = QHBoxLayout()
        ti = QLabel("🍅")
        ti.setStyleSheet("font-size:16px;background:transparent;")
        th.addWidget(ti)
        tt = QLabel("Фокус-таймер")
        tt.setStyleSheet(f"font-size:13px;font-weight:700;color:{C_TEXT};background:transparent;")
        th.addWidget(tt)
        th.addStretch()
        self.timer_status = QLabel("Готов")
        self.timer_status.setStyleSheet(f"font-size:10px;color:{C_TEXT3};background:transparent;")
        th.addWidget(self.timer_status)
        tl.addLayout(th)

        ttr = QHBoxLayout()
        self.timer_display = QLabel("25:00")
        self.timer_display.setStyleSheet(f"font-size:34px;font-weight:800;color:{C_SUCCESS};background:transparent;letter-spacing:2px;")
        ttr.addWidget(self.timer_display)
        ttr.addStretch()
        tl.addLayout(ttr)

        self.timer_progress = QProgressBar()
        self.timer_progress.setFixedHeight(3)
        self.timer_progress.setTextVisible(False)
        tl.addWidget(self.timer_progress)

        tbr = QHBoxLayout()
        tbr.setSpacing(4)
        self.timer_start = QPushButton("▶ 25мин")
        self.timer_start.setStyleSheet(f"QPushButton{{background:{C_SUCCESS}15;border:1px solid {C_SUCCESS};border-radius:6px;padding:5px 12px;font-size:11px;color:{C_SUCCESS};font-weight:700;}} QPushButton:hover{{background:{C_SUCCESS}30;}}")
        self.timer_start.clicked.connect(lambda: self._start_pomo(25))
        tbr.addWidget(self.timer_start)

        self.timer_short = QPushButton("☕ 5мин")
        self.timer_short.setStyleSheet(f"QPushButton{{background:{C_WARNING}15;border:1px solid {C_WARNING};border-radius:6px;padding:5px 12px;font-size:11px;color:{C_WARNING};font-weight:700;}} QPushButton:hover{{background:{C_WARNING}30;}}")
        self.timer_short.clicked.connect(lambda: self._start_pomo(5))
        tbr.addWidget(self.timer_short)

        self.timer_stop = QPushButton("⏹")
        self.timer_stop.setStyleSheet(f"QPushButton{{background:{C_ERROR}15;border:1px solid {C_ERROR};border-radius:6px;padding:5px 12px;font-size:11px;color:{C_ERROR};font-weight:700;}} QPushButton:hover{{background:{C_ERROR}30;}}")
        self.timer_stop.clicked.connect(self._stop_pomo)
        tbr.addWidget(self.timer_stop)
        tbr.addStretch()
        tl.addLayout(tbr)

        grid.addWidget(timer_card)

        br = QHBoxLayout()
        ref = QPushButton("🔄 Обновить")
        ref.setStyleSheet(f"QPushButton{{background:{C_SURFACE2};border:1px solid {C_BORDER};border-radius:8px;padding:6px 14px;font-size:11px;color:{C_TEXT2};}} QPushButton:hover{{border-color:{C_ACCENT};}}")
        ref.clicked.connect(self._update)
        br.addWidget(ref)

        ss = QPushButton("📷 Снимок")
        ss.setStyleSheet(f"QPushButton{{background:{C_SURFACE2};border:1px solid {C_BORDER};border-radius:8px;padding:6px 14px;font-size:11px;color:{C_TEXT2};}} QPushButton:hover{{border-color:{C_ACCENT};}}")
        ss.clicked.connect(self._screenshot)
        br.addWidget(ss)
        br.addStretch()
        l.addLayout(br)

        l.addStretch()

        self.scroll.setWidget(content)

        ml = QVBoxLayout(self)
        ml.setContentsMargins(0, 0, 0, 0)
        ml.addWidget(self.scroll)

        self.pomo_running = False

        self._update()
        self.timer = QTimer()
        self.timer.timeout.connect(self._update)
        self.timer.start(3000)

    def _update(self):
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            boot = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot

            self.cpu_card._value.setText(f"{cpu}%")
            if self.cpu_card._prog:
                self.cpu_card._prog.setValue(int(cpu))

            ms = f"{mem.percent}% ({mem.used//1024**3}/{mem.total//1024**3} GB)"
            self.mem_card._value.setText(ms)
            if self.mem_card._prog:
                self.mem_card._prog.setValue(int(mem.percent))

            ds = f"{disk.percent}% ({disk.used//1024**3}/{disk.total//1024**3} GB)"
            self.disk_card._value.setText(ds)
            if self.disk_card._prog:
                self.disk_card._prog.setValue(int(disk.percent))

            bat = psutil.sensors_battery()
            if bat:
                plug = "🔌" if bat.power_plugged else "🔋"
                self.bat_card._value.setText(f"{bat.percent}% {plug}")
                if self.bat_card._prog:
                    self.bat_card._prog.setValue(int(bat.percent))
            else:
                self.bat_card._value.setText("Н/Д")

            ut = f"{uptime.days}д {uptime.seconds//3600}ч {(uptime.seconds%3600)//60}мин"
            self.uptime_label.setText(f"⏱ Время работы: {ut}")
        except Exception:
            pass

    def _start_pomo(self, minutes):
        self.pomo_minutes = minutes
        self.pomo_remaining = minutes * 60
        self.pomo_running = True
        self.pomo_type = "focus" if minutes >= 25 else "break"
        self.timer_status.setText("Работа 🍅" if self.pomo_type == "focus" else "Отдых ☕")
        self.timer_display.setStyleSheet(f"font-size:34px;font-weight:800;color:{C_SUCCESS};background:transparent;letter-spacing:2px;")
        if not hasattr(self, 'pomo_timer'):
            self.pomo_timer = QTimer()
            self.pomo_timer.timeout.connect(self._pomo_tick)
        self.pomo_timer.start(1000)
        self._pomo_tick()

    def _stop_pomo(self):
        self.pomo_running = False
        if hasattr(self, 'pomo_timer'):
            self.pomo_timer.stop()
        self.timer_display.setText("25:00")
        self.timer_progress.setValue(0)
        self.timer_status.setText("Готов")

    def _pomo_tick(self):
        if not self.pomo_running:
            return
        self.pomo_remaining -= 1
        if self.pomo_remaining <= 0:
            self.pomo_running = False
            self.pomo_timer.stop()
            self.timer_display.setText("00:00")
            self.timer_progress.setValue(100)
            label = "Фокус завершён! 🎉" if self.pomo_type == "focus" else "Перерыв окончен! ☕"
            self.timer_status.setText(label)
            return
        mins = self.pomo_remaining // 60
        secs = self.pomo_remaining % 60
        self.timer_display.setText(f"{mins:02d}:{secs:02d}")
        total = self.pomo_minutes * 60
        self.timer_progress.setValue(int((1 - self.pomo_remaining / total) * 100))

    def _screenshot(self):
        res = self.assistant.process("screenshot")
        QMessageBox.information(self, "Снимок экрана", res)
