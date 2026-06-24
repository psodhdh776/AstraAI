import re, threading, json, math, random, logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("Astra.ChatWidget")

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QScrollArea, QLineEdit, QApplication, QMenu, QGraphicsDropShadowEffect,
)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPixmap, QColor, QKeySequence, QShortcut, QAction

from modules.theme import (
    C_BG, C_SURFACE, C_SURFACE2, C_SURFACE3,
    C_ACCENT, C_ACCENT2, C_ACCENT_GLOW, C_SECONDARY,
    C_TEXT, C_TEXT2, C_TEXT3, C_BORDER, C_BORDER2,
    C_GLASS, C_GLASS2, C_GLASS_HOVER,
    C_GRADIENT_1, C_GRADIENT_2, C_SUCCESS, C_ERROR, C_WARNING, C_INFO,
)
from modules.dialogs import SettingsDialog


# ── Markdown → HTML ──
def _md_to_html(text):
    if re.search(r'<[a-z][\s>]', text):
        return text.replace("\n", "<br>")
    text = re.sub(r"&", "&amp;", text)
    text = re.sub(r"<", "&lt;", text)
    text = re.sub(r">", "&gt;", text)
    text = re.sub(
        r'```(\w*)\n(.*?)```',
        r'<div style="background:#0d0d1a;border:1px solid #2a2a4a;border-radius:8px;margin:4px 0;overflow:hidden;">'
        r'<div style="background:#12122a;padding:3px 10px;font-size:10px;color:#5858aa;">\1</div>'
        r'<pre style="padding:8px;margin:0;overflow-x:auto;font-size:12px;color:#d0d0f0;"><code>\2</code></pre></div>',
        text, flags=re.DOTALL
    )
    text = re.sub(r'`([^`]+)`', r'<code style="background:#1a1a34;padding:1px 5px;border-radius:3px;font-size:12px;color:#c8c8ff;">\1</code>', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<b style="color:#ffffff;">\1</b>', text)
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
    text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2" style="color:#6366f1;text-decoration:none;">\1</a>', text)
    text = re.sub(r'^- (.+)', r'<li style="margin-left:14px;color:#c0c0e0;">\1</li>', text, flags=re.MULTILINE)
    text = re.sub(r'^\d+\. (.+)', r'<li style="margin-left:14px;color:#c0c0e0;">\1</li>', text, flags=re.MULTILINE)
    text = text.replace("\n", "<br>")
    return text


# ── Chat Bubble ──
class ChatBubble(QFrame):
    def __init__(self, sender, text, time):
        super().__init__()
        self.sender = sender
        self.raw_text = text
        self.setObjectName("bubble")
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_menu)

        is_user = sender == "user"
        is_sys = sender == "system"

        if is_sys:
            accent = C_WARNING
            icon = "◆"
            name = "СИСТЕМА"
            bg = "#0f0f1e"
        elif is_user:
            accent = C_ACCENT
            icon = "▶"
            name = "ВЫ"
            bg = "#0e0e22"
        else:
            accent = C_SUCCESS
            icon = "✦"
            name = "ASTRA"
            bg = "#0c0c1a"

        glow = QGraphicsDropShadowEffect()
        glow.setBlurRadius(16)
        glow.setColor(QColor(accent).darker(180))
        glow.setOffset(0, 2)
        self.setGraphicsEffect(glow)

        self.setStyleSheet(f"""
            QFrame#bubble {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 {bg}, stop:1 {bg}dd);
                border: 1px solid {accent}22;
                border-radius: 12px;
                padding: 0px;
                margin: 1px 0px;
            }}
        """)

        l = QVBoxLayout(self)
        l.setContentsMargins(14, 8, 14, 8)
        l.setSpacing(4)

        hdr = QHBoxLayout()
        hdr.setSpacing(6)
        ico = QLabel(icon)
        ico.setStyleSheet(f"font-size:11px;color:{accent};background:transparent;")
        hdr.addWidget(ico)
        nm = QLabel(name)
        nm.setStyleSheet(f"font-size:9px;font-weight:700;color:{accent};background:transparent;letter-spacing:1px;")
        hdr.addWidget(nm)
        hdr.addStretch()
        tm = QLabel(time)
        tm.setStyleSheet(f"font-size:9px;color:{C_TEXT3};background:transparent;")
        hdr.addWidget(tm)

        cp = QPushButton("📋")
        cp.setFixedSize(20, 20)
        cp.setToolTip("Копировать")
        cp.setStyleSheet(f"QPushButton{{background:transparent;border:none;font-size:10px;color:{C_TEXT3};}} QPushButton:hover{{color:{C_ACCENT};}}")
        cp.clicked.connect(lambda: QApplication.clipboard().setText(self.raw_text))
        hdr.addWidget(cp)

        l.addLayout(hdr)

        html = _md_to_html(text)
        self.text_label = QLabel(html)
        self.text_label.setWordWrap(True)
        self.text_label.setTextFormat(Qt.RichText)
        self.text_label.setOpenExternalLinks(True)
        self.text_label.setStyleSheet(f"font-size:13px;color:{C_TEXT};line-height:1.6;background:transparent;padding:0;")
        l.addWidget(self.text_label)

        img_path = self._find_image(text)
        if img_path:
            pix = QPixmap(img_path)
            if not pix.isNull():
                if pix.width() > 280:
                    pix = pix.scaledToWidth(280, Qt.SmoothTransformation)
                il = QLabel()
                il.setPixmap(pix)
                il.setStyleSheet("background:transparent;border:none;border-radius:8px;")
                il.setAlignment(Qt.AlignCenter)
                l.addWidget(il)

    def _show_menu(self, pos):
        m = QMenu(self)
        m.addAction("📋 Копировать", lambda: QApplication.clipboard().setText(self.raw_text))
        m.exec(self.mapToGlobal(pos))

    def _find_image(self, text):
        for line in text.split("\n"):
            line = line.strip()
            m = re.match(r'([A-Za-z]:\\[^\s<>:"|?*]*\.(?:png|jpg|jpeg))', line)
            if m and Path(m.group(1)).exists():
                return m.group(1)
            if line.startswith("\\\\") and any(ext in line for ext in (".png", ".jpg")):
                p = Path(line)
                if p.exists():
                    return str(p)
        return None


# ── Typing Indicator ──
class TypingIndicator(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("typing")
        self.setStyleSheet(f"""
            QFrame#typing {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 #0c0c1a, stop:1 #080818dd);
                border: 1px solid {C_SUCCESS}18;
                border-radius: 12px;
                padding: 8px 14px;
                margin: 1px 0px;
            }}
        """)
        l = QHBoxLayout(self)
        l.setContentsMargins(6, 4, 6, 4)
        l.setSpacing(4)

        lbl = QLabel("✦")
        lbl.setStyleSheet(f"font-size:11px;color:{C_SUCCESS};background:transparent;")
        l.addWidget(lbl)

        lbl2 = QLabel("ASTRA печатает")
        lbl2.setStyleSheet(f"font-size:9px;font-weight:700;color:{C_SUCCESS};background:transparent;letter-spacing:1px;")
        l.addWidget(lbl2)

        self._dots = QLabel()
        self._dots.setStyleSheet(f"font-size:14px;color:{C_SUCCESS};background:transparent;")
        self._dots.setText("  •  •  •")
        l.addWidget(self._dots)
        l.addStretch()

        self._timer = QTimer()
        self._timer.timeout.connect(self._animate)
        self._dot_state = 0
        self._running = False

    def start(self):
        self._running = True
        self._dot_state = 0
        self._timer.start(350)

    def stop(self):
        self._running = False
        self._timer.stop()
        self._dots.setText("  •  •  •")

    def _animate(self):
        if not self._running:
            return
        self._dot_state = (self._dot_state + 1) % 4
        patterns = ["  •      ", "  ••    ", "  •••  ", "  ••    "]
        self._dots.setText(patterns[self._dot_state])


# ── Thinking Bubble ──
class ThinkingBubble(QFrame):
    _MAX_LINES = 8

    def __init__(self):
        super().__init__()
        self.setObjectName("thinkB")
        self.setStyleSheet(f"""
            QFrame#thinkB {{
                background: #0f0f22;
                border: 1px solid {C_ACCENT}18;
                border-radius: 10px;
                padding: 0px;
                margin: 2px 0px;
            }}
        """)
        l = QVBoxLayout(self)
        l.setContentsMargins(14, 8, 14, 8)
        l.setSpacing(3)
        hdr = QLabel("🧠  РАЗМЫШЛЕНИЕ")
        hdr.setStyleSheet(f"font-size:8px;font-weight:700;color:{C_ACCENT}70;background:transparent;letter-spacing:1px;")
        l.addWidget(hdr)
        self._label = QLabel("▎")
        self._label.setWordWrap(True)
        self._label.setTextFormat(Qt.RichText)
        self._label.setStyleSheet(f"font-size:11px;color:#8888bb;background:transparent;line-height:1.5;")
        l.addWidget(self._label)
        self._lines = []
        self._finished = False

    def add_thought(self, text):
        self._lines.append(text)
        if len(self._lines) > self._MAX_LINES:
            self._lines.pop(0)
        self._render()

    def _render(self):
        html = []
        for i, line in enumerate(self._lines):
            last = (i == len(self._lines) - 1) and not self._finished
            prefix = "▸" if last else "·"
            color = C_ACCENT if last else "#8888bb"
            html.append(f'<span style="color:{color}">{prefix}</span> {line}')
        full = "<br>".join(html)
        if not self._finished:
            full += f'<br><span style="color:{C_ACCENT}">▎</span>'
        self._label.setText(full)

    def finish(self):
        self._finished = True
        self._render()


# ── Main Chat Widget ──
class ChatWidget(QWidget):
    def __init__(self, assistant):
        super().__init__()
        self.assistant = assistant
        self.setAcceptDrops(True)
        self.setStyleSheet("background:transparent;")

        self._think_bubble = None
        self._pending_files = []

        l = QVBoxLayout(self)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(0)

        # Header
        header = QWidget()
        header.setStyleSheet(f"background:{C_GLASS};border-bottom:1px solid {C_BORDER};")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(18, 8, 18, 8)

        title = QLabel("💬 Чат")
        title.setStyleSheet("font-size:14px;font-weight:700;color:#ffffff;background:transparent;")
        hl.addWidget(title)
        hl.addStretch()

        self.srch_btn = QPushButton("🔍")
        self.srch_btn.setToolTip("Поиск")
        self.srch_btn.setCheckable(True)
        self.srch_btn.setFixedHeight(28)
        self.srch_btn.setStyleSheet(f"""
            QPushButton{{background:transparent;border:1px solid {C_BORDER};border-radius:5px;padding:2px 8px;font-size:11px;color:{C_TEXT3};}}
            QPushButton:hover{{border-color:{C_ACCENT};color:{C_ACCENT};background:{C_ACCENT}08;}}
            QPushButton:checked{{border-color:{C_ACCENT};background:{C_ACCENT}14;}}
        """)
        self.srch_btn.clicked.connect(self._toggle_search)
        hl.addWidget(self.srch_btn)

        clr = QPushButton("✕")
        clr.setToolTip("Очистить")
        clr.setFixedHeight(28)
        clr.setStyleSheet(f"""
            QPushButton{{background:transparent;border:1px solid {C_BORDER};border-radius:5px;padding:2px 8px;font-size:11px;color:{C_TEXT3};}}
            QPushButton:hover{{border-color:{C_ERROR};color:{C_ERROR};}}
        """)
        clr.clicked.connect(self._clear)
        hl.addWidget(clr)

        stg = QPushButton("⚙")
        stg.setToolTip("Настройки")
        stg.setFixedHeight(28)
        stg.setStyleSheet(f"""
            QPushButton{{background:transparent;border:1px solid {C_BORDER};border-radius:5px;padding:2px 8px;font-size:11px;color:{C_TEXT3};}}
            QPushButton:hover{{border-color:{C_ACCENT};color:{C_ACCENT};}}
        """)
        stg.clicked.connect(lambda: SettingsDialog(self.assistant).exec())
        hl.addWidget(stg)

        l.addWidget(header)

        # Search bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Поиск по истории... (Enter)")
        self.search_bar.setStyleSheet(f"QLineEdit{{background:{C_SURFACE2};border:none;border-bottom:1px solid {C_ACCENT};padding:8px 18px;font-size:12px;color:{C_TEXT};}}")
        self.search_bar.hide()
        self.search_bar.returnPressed.connect(self._do_search)
        l.addWidget(self.search_bar)

        # Scroll area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet(f"""
            QScrollArea{{border:none;background:transparent;}}
            QWidget#sc{{background:transparent;}}
        """)

        sc = QWidget()
        sc.setObjectName("sc")
        self.chat_layout = QVBoxLayout(sc)
        self.chat_layout.setContentsMargins(20, 12, 20, 12)
        self.chat_layout.setSpacing(6)
        self.chat_layout.addStretch()

        self.scroll.setWidget(sc)
        l.addWidget(self.scroll)

        self.typing = TypingIndicator()
        self.typing.hide()
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, self.typing)

        self.add_msg("system", "✨ Добро пожаловать в <b>Astra AI</b>!")

        # Input
        inp_container = QWidget()
        inp_container.setStyleSheet(f"background:{C_GLASS};border-top:1px solid {C_BORDER};")
        il = QVBoxLayout(inp_container)
        il.setContentsMargins(18, 8, 18, 12)
        il.setSpacing(6)

        row = QHBoxLayout()
        row.setSpacing(6)

        self.attach_btn = QPushButton("📎")
        self.attach_btn.setFixedSize(38, 40)
        self.attach_btn.setToolTip("Прикрепить файл")
        self.attach_btn.setStyleSheet(f"QPushButton{{background:{C_SURFACE2};border:1px solid {C_BORDER};border-radius:8px;font-size:14px;color:{C_TEXT3};}} QPushButton:hover{{border-color:{C_ACCENT};background:{C_ACCENT}10;}}")
        self.attach_btn.clicked.connect(self._attach)
        row.addWidget(self.attach_btn)

        self.input = QLineEdit()
        self.input.setPlaceholderText("Сообщение... (Enter — отправить)")
        self.input.setMinimumHeight(40)
        self.input.returnPressed.connect(self._send)
        self.input.setStyleSheet(f"QLineEdit{{background:{C_SURFACE2};border:1px solid {C_BORDER};border-radius:8px;padding:0 14px;font-size:13px;color:{C_TEXT};}} QLineEdit:focus{{border:1px solid {C_ACCENT};}}")
        row.addWidget(self.input)

        self.voice_btn = QPushButton("🎤")
        self.voice_btn.setObjectName("voiceBtn")
        self.voice_btn.setCheckable(True)
        self.voice_btn.setFixedSize(40, 40)
        self.voice_btn.setToolTip("Голосовой ввод (нажми — говори — ещё раз отключить)")
        self.voice_btn.setStyleSheet(f"QPushButton{{background:{C_SURFACE2};border:1px solid {C_BORDER};border-radius:8px;font-size:14px;color:{C_TEXT3};}} QPushButton:hover{{border-color:{C_ACCENT};}} QPushButton:checked{{border-color:{C_SUCCESS};background:{C_SUCCESS}12;}}")
        self.voice_btn.clicked.connect(self._toggle_voice)
        row.addWidget(self.voice_btn)

        self.ptt_btn = QPushButton("🎙")
        self.ptt_btn.setObjectName("pttBtn")
        self.ptt_btn.setFixedSize(40, 40)
        self.ptt_btn.setToolTip("Push-to-Talk: зажми и говори")
        self.ptt_btn.setStyleSheet(f"QPushButton{{background:{C_SURFACE2};border:1px solid {C_BORDER};border-radius:8px;font-size:14px;color:{C_TEXT3};}} QPushButton:hover{{border-color:{C_ACCENT};}} QPushButton:pressed{{border-color:{C_ERROR};background:{C_ERROR}18;color:{C_ERROR};}}")
        self.ptt_btn.pressed.connect(self._ptt_start)
        self.ptt_btn.released.connect(self._ptt_stop)
        row.addWidget(self.ptt_btn)

        self.tts_btn = QPushButton("🔊")
        self.tts_btn.setObjectName("ttsBtn")
        self.tts_btn.setCheckable(True)
        self.tts_btn.setChecked(self.assistant.voice_enabled)
        self.tts_btn.setFixedSize(36, 36)
        self.tts_btn.setToolTip("Озвучивание ответов")
        self.tts_btn.setStyleSheet(f"QPushButton{{background:transparent;border:1px solid {C_BORDER};border-radius:8px;font-size:12px;color:{C_TEXT3};}} QPushButton:hover{{border-color:{C_ACCENT};}} QPushButton:checked{{border-color:{C_SUCCESS};color:{C_SUCCESS};}}")
        self.tts_btn.toggled.connect(lambda v: setattr(self.assistant, "voice_enabled", v))
        row.addWidget(self.tts_btn)

        self.send_btn = QPushButton("➤")
        self.send_btn.setObjectName("sendBtn")
        self.send_btn.setFixedSize(50, 40)
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.setToolTip("Отправить")
        self.send_btn.setStyleSheet(f"""
            QPushButton{{
                background:qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 {C_GRADIENT_1}, stop:1 {C_GRADIENT_2});
                border:none;border-radius:8px;font-size:16px;color:white;font-weight:700;
            }}
            QPushButton:hover{{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 #4f46e5, stop:1 #7c3aed);}}
        """)
        self.send_btn.clicked.connect(self._send)
        row.addWidget(self.send_btn)

        il.addLayout(row)

        self.drop_hint = QLabel("📎  Перетащите файл сюда")
        self.drop_hint.setAlignment(Qt.AlignCenter)
        self.drop_hint.setStyleSheet(f"background:{C_ACCENT}08;border:2px dashed {C_ACCENT}40;border-radius:12px;padding:20px;font-size:13px;color:{C_ACCENT};")
        self.drop_hint.hide()
        il.addWidget(self.drop_hint)

        l.addWidget(inp_container)

        QShortcut(QKeySequence("Ctrl+L"), self).activated.connect(self._clear)

    # ── Drag & Drop ──
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
            self.drop_hint.show()

    def dragLeaveEvent(self, e):
        self.drop_hint.hide()

    def dropEvent(self, e):
        self.drop_hint.hide()
        for url in e.mimeData().urls():
            p = url.toLocalFile()
            if not p:
                continue
            ext = Path(p).suffix.lower()
            if ext in (".txt", ".md", ".py", ".js", ".html", ".css", ".json", ".xml", ".csv", ".log", ".ini", ".cfg", ".yaml", ".yml", ".toml"):
                try:
                    content = Path(p).read_text("utf-8", errors="replace")
                    if len(content) > 10000:
                        content = content[:10000] + "\n... [truncated]"
                    self.input.setText(f"[Файл: {Path(p).name}]\n{content}")
                    self.add_msg("system", f"📖 Содержимое <b>{Path(p).name}</b> загружено в поле ввода")
                except Exception as exc:
                    self.add_msg("system", f"❌ Не удалось прочитать {Path(p).name}: {exc}")
            elif ext == ".pdf":
                try:
                    import PyPDF2
                    reader = PyPDF2.PdfReader(p)
                    text = "".join(page.extract_text() or "" for page in reader.pages)
                    if len(text) > 10000:
                        text = text[:10000] + "\n... [truncated]"
                    self.input.setText(f"[PDF: {Path(p).name}]\n{text}")
                    self.add_msg("system", f"📖 PDF <b>{Path(p).name}</b> ({len(reader.pages)} стр.) загружен")
                except ImportError:
                    self._pending_files.append(p)
                    self.add_msg("system", f"📎 <b>{Path(p).name}</b> добавлен (установите PyPDF2 для чтения)")
                except Exception as exc:
                    self.add_msg("system", f"❌ Ошибка PDF {Path(p).name}: {exc}")
            elif ext == ".docx":
                try:
                    from docx import Document
                    doc = Document(p)
                    text = "\n".join(p.text for p in doc.paragraphs)
                    if len(text) > 10000:
                        text = text[:10000] + "\n... [truncated]"
                    self.input.setText(f"[DOCX: {Path(p).name}]\n{text}")
                    self.add_msg("system", f"📖 DOCX <b>{Path(p).name}</b> загружен")
                except ImportError:
                    self._pending_files.append(p)
                    self.add_msg("system", f"📎 <b>{Path(p).name}</b> добавлен (установите python-docx для чтения)")
                except Exception as exc:
                    self.add_msg("system", f"❌ Ошибка DOCX {Path(p).name}: {exc}")
            else:
                self._pending_files.append(p)
                self.add_msg("system", f"📎 <b>{Path(p).name}</b> добавлен")

    def _attach(self):
        from PySide6.QtWidgets import QFileDialog
        files, _ = QFileDialog.getOpenFileNames(self, "Выберите файлы", "", "Все файлы (*)")
        for f in files:
            self._pending_files.append(f)
            self.add_msg("system", f"📎 Файл: <b>{Path(f).name}</b> добавлен")
        if self._pending_files:
            self.input.setPlaceholderText(f"📎 {len(self._pending_files)} файл(ов) — напишите сообщение...")

    def show_typing(self):
        if self.typing:
            self.typing.show()
            self.typing.start()
            self.chat_layout.insertWidget(self.chat_layout.count() - 1, self.typing)
            QTimer.singleShot(50, self._scroll_bottom)

    def hide_typing(self):
        if self.typing:
            self.typing.stop()
            self.typing.hide()

    def add_msg(self, sender, text):
        self.hide_typing()
        b = ChatBubble(sender, text, datetime.now().strftime("%H:%M"))
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, b)
        anim = QPropertyAnimation(b, b"maximumHeight")
        anim.setDuration(250)
        anim.setStartValue(0)
        anim.setEndValue(b.sizeHint().height() + 30)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start()
        QTimer.singleShot(50, self._scroll_bottom)

    def add_stream(self, sender):
        self.hide_typing()
        b = ChatBubble(sender, "▎", datetime.now().strftime("%H:%M"))
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, b)
        QTimer.singleShot(50, self._scroll_bottom)
        return b.text_label

    def show_think(self):
        if self._think_bubble:
            self._think_bubble.deleteLater()
        self._think_bubble = ThinkingBubble()
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, self._think_bubble)
        QTimer.singleShot(50, self._scroll_bottom)

    def add_thought(self, text):
        if self._think_bubble and not self._think_bubble._finished:
            self._think_bubble.add_thought(text)

    def hide_think(self):
        if self._think_bubble:
            self._think_bubble.finish()
            self._think_bubble = None

    def _process_response(self, text):
        tk = getattr(self.assistant, 'thinker', None)
        if tk and hasattr(tk, 'reason_deep'):
            self.show_think()
            def tw():
                try:
                    steps = tk.reason_deep(text)
                    for d, (stage, msg) in enumerate(steps):
                        QTimer.singleShot(d * 200, lambda m=msg: self.add_thought(m))
                except Exception as e:
                    logger.warning("Think: %s", e)
            threading.Thread(target=tw, daemon=True).start()

        done = threading.Event()

        def run():
            resp = ""
            try:
                resp = self.assistant.process(text)
            except Exception as e:
                logger.error("Process error: %s", e)
                resp = f"⚠ Ошибка: {e}"
            finally:
                done.set()

            def ui():
                self.hide_typing()
                self.hide_think()
                if not resp or resp == "__EXIT__":
                    return
                lbl = self.add_stream("assistant")
                if lbl:
                    html = _md_to_html(resp)
                    words = html.split()
                    self._stream(lbl, html, words, 0)
                    self._pending_files = []
                    if self.assistant.voice_enabled:
                        QTimer.singleShot(500, lambda: self.assistant._speak(resp))

            QTimer.singleShot(0, ui)

        threading.Thread(target=run, daemon=True).start()

        def to():
            if not done.wait(20):
                logger.error("Timeout: %r", text[:80])
                QTimer.singleShot(0, lambda: self.add_msg("system", "⏱ Превышено время ожидания."))
        threading.Thread(target=to, daemon=True).start()

    def _stream(self, lbl, html, words, idx):
        if idx >= len(words):
            lbl.setText(html)
            QTimer.singleShot(50, self._scroll_bottom)
            return
        shown = " ".join(words[:idx + 1])
        shown += " ▎" if idx < len(words) - 1 else ""
        lbl.setText(shown)
        if idx % 2 == 0:
            QTimer.singleShot(50, self._scroll_bottom)
        speed = max(10, min(35, 180 // max(1, len(words))))
        QTimer.singleShot(speed, lambda: self._stream(lbl, html, words, idx + 1))

    def _scroll_bottom(self):
        sb = self.scroll.verticalScrollBar()
        if sb:
            sb.setValue(sb.maximum())

    def _send(self):
        try:
            text = self.input.text().strip()
            if not text:
                return
            logger.debug("_send: %r", text[:80])
            self.add_msg("user", text)
            self.input.clear()

            if self._pending_files:
                fc = "\n".join(f"[Файл: {f}]" for f in self._pending_files)
                text = f"{text}\n{fc}"
                self._pending_files = []

            if text.lower() in ("пока", "до свидания", "выйти", "exit", "quit"):
                self.add_msg("assistant", "До свидания! Я буду здесь. 👋")
                QTimer.singleShot(1500, QApplication.quit)
                return

            self.show_typing()
            QTimer.singleShot(100, lambda: self._process_response(text))
        except Exception as e:
            logger.error("_send: %s", e, exc_info=True)
            self.add_msg("system", f"⚠ Ошибка: {e}")

    def _ptt_start(self):
        self._ptt_recording = True
        self._ptt_frames = []
        self.ptt_btn.setStyleSheet(f"QPushButton{{background:{C_ERROR}18;border:1px solid {C_ERROR};border-radius:8px;font-size:14px;color:{C_ERROR};}}")
        self.ptt_btn.setToolTip("Отпусти — распознаю...")
        self.add_msg("system", "🎙 Зажми и говори...")
        self._ptt_thread = threading.Thread(target=self._ptt_record, daemon=True)
        self._ptt_thread.start()

    def _ptt_record(self):
        import sounddevice as sd
        import numpy as np
        samplerate = 16000
        try:
            def callback(indata, frames, time_info, status):
                if not self._ptt_recording:
                    raise sd.CallbackStop
                self._ptt_frames.append(indata.copy())
            with sd.InputStream(samplerate=samplerate, channels=1,
                                dtype='int16', callback=callback):
                while self._ptt_recording:
                    sd.sleep(100)
        except Exception as e:
            logger.warning("PTT record: %s", e)

    def _ptt_stop(self):
        self._ptt_recording = False
        if self._ptt_thread:
            self._ptt_thread.join(timeout=2)
            self._ptt_thread = None
        self.ptt_btn.setStyleSheet(f"QPushButton{{background:{C_SURFACE2};border:1px solid {C_BORDER};border-radius:8px;font-size:14px;color:{C_TEXT3};}} QPushButton:hover{{border-color:{C_ACCENT};}} QPushButton:pressed{{border-color:{C_ERROR};background:{C_ERROR}18;color:{C_ERROR};}}")
        self.ptt_btn.setToolTip("Push-to-Talk: зажми и говори")

        if not self._ptt_frames or len(self._ptt_frames) < 5:
            self.add_msg("system", "⏱ Слишком коротко")
            return

        import numpy as np
        import sounddevice as sd
        import speech_recognition as sr
        import io
        import wave

        audio_data = np.concatenate(self._ptt_frames, axis=0)
        buf = io.BytesIO()
        wf = wave.open(buf, 'wb')
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(audio_data.tobytes())
        wf.close()
        buf.seek(0)

        try:
            r = sr.Recognizer()
            with sr.AudioFile(buf) as source:
                audio = r.record(source)
            text = r.recognize_google(audio, language="ru-RU")
            if text:
                self._handle_voice_result(text)
            else:
                self.add_msg("system", "🤔 Не удалось распознать")
        except sr.UnknownValueError:
            self.add_msg("system", "🤔 Не удалось распознать")
        except Exception as e:
            self.add_msg("system", f"❌ Ошибка: {e}")

    def _toggle_voice(self):
        if self.assistant.listening:
            self.assistant.stop_listening()
            self.voice_btn.setChecked(False)
            self.voice_btn.setToolTip("Голосовой ввод")
        else:
            def cb(text):
                self.voice_btn.setChecked(False)
                self._handle_voice_result(text)

            ok = self.assistant.start_listening(cb)
            if ok:
                self.voice_btn.setChecked(True)
                self.voice_btn.setToolTip("Остановить запись")
                self.add_msg("system", "🎤 Слушаю... говорите!")
            else:
                self.add_msg("system", "❌ Микрофон недоступен")

    def _handle_voice_result(self, text):
        if text is None:
            self.add_msg("system", "⏱ Речь не обнаружена")
            return
        if text == "":
            self.add_msg("system", "🤔 Не удалось распознать")
            return
        if text.startswith("[error:"):
            self.add_msg("system", f"❌ {text}")
            return

        tl = text.lower().strip()
        from modules.voice_engine import VOICE_COMMANDS
        for pattern, (action, tab_idx) in VOICE_COMMANDS.items():
            if pattern in tl:
                if tab_idx is not None:
                    w = self.window()
                    if w and hasattr(w, 'nav_bar'):
                        w.nav_bar.set_current(tab_idx)
                        self.add_msg("system", f"👉 Открываю «{pattern}»")
                        return
                elif action == "screenshot":
                    res = self.assistant._do_screenshot()
                    self.add_msg("system", res or "📸 Скриншот сделан")
                    return
                elif action == "help":
                    self.add_msg("assistant", "Я понимаю команды: чат, заметки, система, аналитика, главная, скриншот, настройки, стоп, тихо, выход.")
                    return
                elif action == "quit":
                    QApplication.quit()
                    return
                elif action == "silent":
                    self.assistant.voice_enabled = False
                    self.tts_btn.setChecked(False)
                    self.add_msg("system", "🔇 Звук выключен")
                    return
                elif action == "stop":
                    self.add_msg("system", "⏹ Остановлено")
                    return

        self.add_msg("user", f"[voice] {text[:120]}")
        self.assistant.add_history("user", text)
        self.show_typing()
        resp = self.assistant.process(text)
        self.hide_typing()
        if resp and resp != "__EXIT__":
            self.add_msg("assistant", resp)
            if self.assistant.voice_enabled:
                try:
                    self.assistant._speak(resp)
                except Exception:
                    pass

    def _toggle_search(self):
        v = not self.search_bar.isVisible()
        self.search_bar.setVisible(v)
        self.srch_btn.setChecked(v)
        if v:
            self.search_bar.setFocus()
        else:
            self.search_bar.clear()

    def _do_search(self):
        q = self.search_bar.text().strip()
        if not q:
            return
        results = self.assistant.search_history(q)
        self.search_bar.clear()
        self.search_bar.hide()
        self.srch_btn.setChecked(False)
        if not results:
            self.add_msg("system", f"🔍 Ничего не найдено: <b>{q}</b>")
            return
        msg = f"🔍 <b>Результаты:</b> «{q}»<br><br>"
        for r in results[:10]:
            t = r.get("text", "")[:200]
            tm = r.get("time", "")[:16].replace("T", " ")
            role = "👤" if r["role"] == "user" else "✨"
            msg += f"{role} <i>{tm}</i> — {t}<br><br>"
        if len(results) > 10:
            msg += f"... и ещё {len(results) - 10}"
        self.add_msg("system", msg)

    def _clear(self):
        while self.chat_layout.count() > 1:
            item = self.chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.add_msg("system", "💬 Чат очищен")
