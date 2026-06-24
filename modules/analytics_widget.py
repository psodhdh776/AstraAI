from collections import Counter
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout,
    QScrollArea,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QColor, QPen, QLinearGradient, QFont

from modules.theme import (
    C_BG, C_SURFACE, C_SURFACE2, C_SURFACE3,
    C_ACCENT, C_ACCENT2, C_SECONDARY,
    C_TEXT, C_TEXT2, C_TEXT3, C_BORDER,
    C_GLASS, C_GLASS2,
    C_GRADIENT_1, C_GRADIENT_2, C_SUCCESS, C_ERROR, C_WARNING, C_INFO,
)
from modules.ui_common import GlassCard


class MiniChart(QWidget):
    def __init__(self, data, color=C_ACCENT, height=60):
        super().__init__()
        self._data = data
        self._color = QColor(color)
        self.setMinimumHeight(height)
        self.setMaximumHeight(height)

    def update_data(self, data):
        self._data = data
        self.update()

    def paintEvent(self, e):
        if not self._data:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w = self.width() - 16
        h = self.height() - 24
        if w <= 0 or h <= 0:
            p.end()
            return
        max_val = max(self._data) or 1
        step = w / max(1, len(self._data) - 1)

        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0, self._color)
        grad.setColorAt(1, QColor(self._color.red(), self._color.green(), self._color.blue(), 20))
        p.setBrush(grad)
        p.setPen(QPen(self._color.lighter(130), 2))

        pts = []
        for i, val in enumerate(self._data):
            x = 8 + i * step if step > 0 else 8 + i
            y = 12 + h - (val / max_val * h)
            pts.append((x, y))

        if len(pts) >= 2:
            for i in range(1, len(pts)):
                p.drawLine(int(pts[i-1][0]), int(pts[i-1][1]),
                           int(pts[i][0]), int(pts[i][1]))
            p.setBrush(self._color)
            for x, y in pts:
                p.drawEllipse(int(x)-3, int(y)-3, 6, 6)
        p.end()


class StatCard(QFrame):
    def __init__(self, title, value, subtitle="", color=C_TEXT):
        super().__init__()
        self.setObjectName("card")
        self.setStyleSheet(f"""
            QFrame#card {{
                background: {C_GLASS};
                border: 1px solid {C_BORDER};
                border-radius: 12px;
                padding: 12px;
            }}
        """)
        l = QVBoxLayout(self)
        l.setContentsMargins(14, 12, 14, 12)
        l.setSpacing(2)

        tl = QLabel(title)
        tl.setStyleSheet(f"color:{C_TEXT3};font-size:9px;font-weight:600;letter-spacing:1.5px;background:transparent;")
        l.addWidget(tl)

        self._val = QLabel(str(value))
        self._val.setStyleSheet(f"color:{color};font-size:26px;font-weight:800;background:transparent;")
        l.addWidget(self._val)

        if subtitle:
            sl = QLabel(subtitle)
            sl.setStyleSheet(f"color:{C_TEXT3};font-size:9px;background:transparent;")
            l.addWidget(sl)

    def set_val(self, v):
        self._val.setText(str(v))


class AnalyticsWidget(QWidget):
    def __init__(self, assistant):
        super().__init__()
        self.assistant = assistant
        self.emotion = getattr(assistant, "emotion", None)
        self.setStyleSheet("background:transparent;")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")

        container = QWidget()
        container.setStyleSheet("background:transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(10)

        header = QLabel("📊 Аналитика")
        header.setStyleSheet(f"font-size:18px;font-weight:700;color:#ffffff;background:transparent;")
        layout.addWidget(header)

        sub = QLabel("Статистика использования и инсайты")
        sub.setStyleSheet(f"font-size:12px;color:{C_TEXT3};background:transparent;")
        layout.addWidget(sub)

        grid = QGridLayout()
        grid.setSpacing(6)

        self._cards = {}
        stats = [
            ("total_msgs", "Сообщений", "0", "", C_ACCENT),
            ("today_msgs", "Сегодня", "0", "", C_SUCCESS),
            ("commands", "Команд", "0", "", C_INFO),
            ("accuracy", "Точность", "0%", "", C_SECONDARY),
            ("emotion", "Настроение", "⚡", "", C_WARNING),
            ("memory", "Воспоминаний", "0", "", C_ACCENT2),
            ("intents", "Интентов", "0", "", C_SUCCESS),
            ("uptime", "Сессий", "0", "", C_INFO),
        ]
        for i, (key, title, val, sub, color) in enumerate(stats):
            card = StatCard(title, val, sub, color)
            self._cards[key] = card
            grid.addWidget(card, i // 4, i % 4)

        layout.addLayout(grid)

        cl = QLabel("Активность (последние дни)")
        cl.setStyleSheet(f"color:{C_TEXT3};font-size:12px;font-weight:600;padding:4px 0;background:transparent;")
        layout.addWidget(cl)

        self._chart = MiniChart([2, 5, 3, 7, 4, 6, 8], C_ACCENT)
        layout.addWidget(self._chart)

        ml = QLabel("Динамика взаимодействия")
        ml.setStyleSheet(f"color:{C_TEXT3};font-size:12px;font-weight:600;padding:4px 0;background:transparent;")
        layout.addWidget(ml)

        self._mood_chart = MiniChart([0.4, 0.6, 0.5, 0.7, 0.55, 0.75, 0.6], C_SECONDARY)
        layout.addWidget(self._mood_chart)

        insights_card = GlassCard()
        il = QVBoxLayout(insights_card)
        il.setContentsMargins(16, 14, 16, 14)
        ih = QLabel("💡 Инсайты")
        ih.setStyleSheet(f"font-size:13px;font-weight:700;color:{C_TEXT2};background:transparent;")
        il.addWidget(ih)

        self._insights = QLabel("Собираю данные...")
        self._insights.setWordWrap(True)
        self._insights.setStyleSheet(f"color:{C_TEXT3};font-size:11px;padding:4px 0;background:transparent;line-height:1.6;")
        il.addWidget(self._insights)
        layout.addWidget(insights_card)

        layout.addStretch()

        scroll.setWidget(container)
        ml2 = QVBoxLayout(self)
        ml2.setContentsMargins(0, 0, 0, 0)
        ml2.addWidget(scroll)

        self._timer = QTimer()
        self._timer.timeout.connect(self._refresh)
        self._timer.start(10000)
        self._refresh()

    def _refresh(self):
        try:
            hist = getattr(self.assistant, "history", [])
            today = datetime.now().strftime("%Y-%m-%d")
            today_msgs = sum(1 for h in hist if h.get("time", "").startswith(today))
            total = len(hist)
            user_msgs = sum(1 for h in hist if h.get("role") == "user")

            self._cards["total_msgs"].set_val(str(total))
            self._cards["today_msgs"].set_val(str(today_msgs))
            self._cards["commands"].set_val(str(user_msgs))

            intents = Counter()
            for h in hist:
                if h.get("role") == "user":
                    intents[h.get("intent", "unknown")] += 1
            self._cards["intents"].set_val(str(len(intents)))

            unique_dates = set()
            for h in hist:
                t = h.get("time", "")
                if t:
                    unique_dates.add(t[:10])
            self._cards["uptime"].set_val(str(len(unique_dates)))

            if total > 0:
                acc = (user_msgs / total) * 100
                self._cards["accuracy"].set_val(f"{acc:.0f}%")

            if self.emotion:
                mood = getattr(self.emotion, "user_mood", 0.5)
                icons = ["😢", "😐", "😊", "😄"]
                idx = min(3, max(0, int(mood * 3)))
                self._cards["emotion"].set_val(icons[idx])

            core = getattr(self.assistant, "core", None)
            mem_count = 0
            if core:
                mem = getattr(core, "memory", None)
                if mem and hasattr(mem, "episodes"):
                    mem_count = len(mem.episodes) + len(getattr(mem, "consolidated", []))
                self._cards["memory"].set_val(str(mem_count))

            # Chart: activity per day (last 7)
            day_counts = []
            for d in range(6, -1, -1):
                from datetime import timedelta
                day = (datetime.now() - timedelta(days=d)).strftime("%Y-%m-%d")
                cnt = sum(1 for h in hist if h.get("time", "").startswith(day))
                day_counts.append(cnt)
            self._chart.update_data(day_counts if any(day_counts) else [1, 2, 3, 2, 4, 3, 5])

            # Mood chart: last 10 interactions
            if self.emotion:
                timeline = getattr(self.emotion, "mood_timeline", [])
                if len(timeline) >= 2:
                    self._mood_chart.update_data(timeline[-15:])

            insights = []
            if core:
                personality = getattr(core, "personality", None)
                if personality:
                    top = sorted(personality.traits.items(), key=lambda x: -x[1])[:3]
                    ins = ", ".join(f"{t}: {v:.2f}" for t, v in top)
                    insights.append(f"🧠 Личность: {ins}")
                    insights.append(f"🎭 Настроение: {getattr(personality, 'mood', 'нейтральное')}")
                mem = getattr(core, "memory", None)
                if mem:
                    eps = len(getattr(mem, "episodes", []))
                    cons = len(getattr(mem, "consolidated", []))
                    insights.append(f"💾 Эпизодов: {eps}, Закреплено: {cons}")

            if intents:
                top3 = intents.most_common(3)
                ins = ", ".join(f"{i} ({c})" for i, c in top3)
                insights.append(f"🎯 Топ интенты: {ins}")

            if insights:
                self._insights.setText("<br>".join(insights))
            else:
                self._insights.setText("Продолжайте общаться —数据 будет собираться!")
        except Exception:
            pass
