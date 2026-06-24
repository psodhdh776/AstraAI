"""
Multi-theme support for Astra AI.
Usage: from modules.theme import C; bg = C.BG; accent = C.ACCENT
Call C.set_theme(name) to switch.
"""

import logging

logger = logging.getLogger("Astra.Theme")


class _ThemeState:
    """Mutable container storing current theme colors."""

    def __init__(self):
        self._themes = {}
        self._current = "indigo"
        self._callbacks = []
        self._define_themes()

    def _define_themes(self):
        # ── Indigo (default dark) ──
        self._themes["indigo"] = {
            "BG": "#0a0a14",
            "SURFACE": "rgba(16, 16, 32, 0.85)",
            "SURFACE2": "rgba(24, 24, 48, 0.75)",
            "SURFACE3": "rgba(32, 32, 56, 0.65)",
            "ACCENT": "#6366f1",
            "ACCENT2": "#8b5cf6",
            "ACCENT_GLOW": "rgba(99, 102, 241, 0.3)",
            "SECONDARY": "#14b8a6",
            "SUCCESS": "#22c55e",
            "WARNING": "#eab308",
            "ERROR": "#ef4444",
            "INFO": "#3b82f6",
            "TEXT": "#f8fafc",
            "TEXT2": "#cbd5e1",
            "TEXT3": "#64748b",
            "BORDER": "rgba(99, 102, 241, 0.15)",
            "BORDER2": "rgba(99, 102, 241, 0.08)",
            "GRADIENT_1": "#6366f1",
            "GRADIENT_2": "#8b5cf6",
            "GRADIENT_3": "#a855f7",
            "GLASS": "rgba(16, 16, 32, 0.82)",
            "GLASS2": "rgba(24, 24, 48, 0.72)",
            "GLASS_HOVER": "rgba(24, 24, 52, 0.9)",
        }
        # ── Cyberpunk ──
        self._themes["cyberpunk"] = {
            "BG": "#0a0015",
            "SURFACE": "rgba(16, 0, 32, 0.85)",
            "SURFACE2": "rgba(24, 0, 48, 0.75)",
            "SURFACE3": "rgba(32, 0, 56, 0.65)",
            "ACCENT": "#00ff88",
            "ACCENT2": "#ff00ff",
            "ACCENT_GLOW": "rgba(0, 255, 136, 0.3)",
            "SECONDARY": "#ff6600",
            "SUCCESS": "#00ff88",
            "WARNING": "#ffff00",
            "ERROR": "#ff0033",
            "INFO": "#00ccff",
            "TEXT": "#00ffcc",
            "TEXT2": "#ff00ff",
            "TEXT3": "#8866aa",
            "BORDER": "rgba(0, 255, 136, 0.15)",
            "BORDER2": "rgba(255, 0, 255, 0.08)",
            "GRADIENT_1": "#00ff88",
            "GRADIENT_2": "#ff00ff",
            "GRADIENT_3": "#ff6600",
            "GLASS": "rgba(10, 0, 21, 0.82)",
            "GLASS2": "rgba(16, 0, 32, 0.72)",
            "GLASS_HOVER": "rgba(24, 0, 48, 0.9)",
        }
        # ── Light ──
        self._themes["light"] = {
            "BG": "#f5f5f9",
            "SURFACE": "rgba(255, 255, 255, 0.95)",
            "SURFACE2": "rgba(240, 240, 248, 0.9)",
            "SURFACE3": "rgba(230, 230, 240, 0.85)",
            "ACCENT": "#4f46e5",
            "ACCENT2": "#7c3aed",
            "ACCENT_GLOW": "rgba(79, 70, 229, 0.15)",
            "SECONDARY": "#0d9488",
            "SUCCESS": "#16a34a",
            "WARNING": "#ca8a04",
            "ERROR": "#dc2626",
            "INFO": "#2563eb",
            "TEXT": "#1e293b",
            "TEXT2": "#475569",
            "TEXT3": "#94a3b8",
            "BORDER": "rgba(79, 70, 229, 0.12)",
            "BORDER2": "rgba(79, 70, 229, 0.06)",
            "GRADIENT_1": "#4f46e5",
            "GRADIENT_2": "#7c3aed",
            "GRADIENT_3": "#a855f7",
            "GLASS": "rgba(255, 255, 255, 0.9)",
            "GLASS2": "rgba(248, 248, 252, 0.85)",
            "GLASS_HOVER": "rgba(255, 255, 255, 0.95)",
        }
        # ── Forest (dark green) ──
        self._themes["forest"] = {
            "BG": "#0a140a",
            "SURFACE": "rgba(12, 24, 12, 0.85)",
            "SURFACE2": "rgba(18, 32, 18, 0.75)",
            "SURFACE3": "rgba(24, 40, 24, 0.65)",
            "ACCENT": "#22c55e",
            "ACCENT2": "#16a34a",
            "ACCENT_GLOW": "rgba(34, 197, 94, 0.3)",
            "SECONDARY": "#14b8a6",
            "SUCCESS": "#4ade80",
            "WARNING": "#facc15",
            "ERROR": "#ef4444",
            "INFO": "#38bdf8",
            "TEXT": "#ecfdf5",
            "TEXT2": "#a7f3d0",
            "TEXT3": "#6b7280",
            "BORDER": "rgba(34, 197, 94, 0.15)",
            "BORDER2": "rgba(34, 197, 94, 0.08)",
            "GRADIENT_1": "#22c55e",
            "GRADIENT_2": "#16a34a",
            "GRADIENT_3": "#15803d",
            "GLASS": "rgba(12, 24, 12, 0.82)",
            "GLASS2": "rgba(18, 32, 18, 0.72)",
            "GLASS_HOVER": "rgba(18, 36, 18, 0.9)",
        }
        self._apply("indigo")

    def _apply(self, name):
        t = self._themes.get(name, self._themes["indigo"])
        for k, v in t.items():
            setattr(self, k, v)
        self._current = name

    @property
    def current(self):
        return self._current

    def theme_names(self):
        return list(self._themes.keys())

    def set_theme(self, name, notify=True):
        if name not in self._themes:
            logger.warning("Unknown theme: %s", name)
            return
        self._apply(name)
        self._update_globals()
        if notify:
            for cb in self._callbacks:
                try:
                    cb(name)
                except Exception as e:
                    logger.warning("Theme callback: %s", e)

    @staticmethod
    def _update_globals():
        import sys
        this = sys.modules[__name__]
        for k in ("BG", "SURFACE", "SURFACE2", "SURFACE3",
                  "ACCENT", "ACCENT2", "ACCENT_GLOW", "SECONDARY",
                  "SUCCESS", "WARNING", "ERROR", "INFO",
                  "TEXT", "TEXT2", "TEXT3",
                  "BORDER", "BORDER2",
                  "GRADIENT_1", "GRADIENT_2", "GRADIENT_3",
                  "GLASS", "GLASS2", "GLASS_HOVER"):
            setattr(this, f"C_{k}", getattr(C, k))

    def on_change(self, callback):
        self._callbacks.append(callback)

    def build_qss(self):
        """Build full QSS stylesheet for current theme."""
        return f"""
QWidget {{ background: {self.BG}; color: {self.TEXT}; font-family: Segoe UI, sans-serif; }}
QLabel {{ background: transparent; }}
QPushButton {{ background: {self.SURFACE2}; border: 1px solid {self.BORDER}; border-radius: 8px; padding: 6px 16px; color: {self.TEXT}; font-size: 12px; }}
QPushButton:hover {{ border-color: {self.ACCENT}; }}
QPushButton:pressed {{ background: {self.ACCENT}15; }}
QPushButton:checked {{ background: {self.ACCENT}20; border-color: {self.ACCENT}; }}
QPushButton#navBtn {{ background: transparent; border: none; border-radius: 8px; padding: 6px 16px; color: {self.TEXT3}; font-size: 12px; font-weight: 600; }}
QPushButton#navBtn:hover {{ background: {self.ACCENT}12; color: {self.TEXT2}; }}
QPushButton#navBtn:checked {{ background: {self.ACCENT}20; color: {self.ACCENT}; }}
QPushButton#voiceBtn {{ background: {self.SURFACE2}; border: 1px solid {self.BORDER}; border-radius: 8px; font-size: 14px; color: {self.TEXT3}; }}
QPushButton#voiceBtn:hover {{ border-color: {self.ACCENT}; }}
QPushButton#voiceBtn:checked {{ border-color: {self.SUCCESS}; background: {self.SUCCESS}12; }}
QPushButton#sendBtn {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 {self.GRADIENT_1}, stop:1 {self.GRADIENT_2}); border: none; border-radius: 8px; font-size: 16px; color: white; font-weight: 700; }}
QPushButton#sendBtn:hover {{ opacity: 0.9; }}
QLineEdit {{ background: {self.SURFACE2}; border: 1px solid {self.BORDER}; border-radius: 8px; padding: 6px 12px; color: {self.TEXT}; font-size: 13px; }}
QLineEdit:focus {{ border: 1px solid {self.ACCENT}; }}
QScrollBar:vertical {{ background: transparent; width: 6px; }}
QScrollBar::handle:vertical {{ background: {self.ACCENT}40; border-radius: 3px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {self.ACCENT}80; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QScrollArea {{ border: none; background: transparent; }}
QFrame#card {{ background: {self.SURFACE}; border: 1px solid {self.BORDER}; border-radius: 12px; }}
QTextEdit {{ background: {self.SURFACE2}; border: 1px solid {self.BORDER}; border-radius: 8px; padding: 8px; color: {self.TEXT}; font-size: 13px; }}
QComboBox {{ background: {self.SURFACE2}; border: 1px solid {self.BORDER}; border-radius: 8px; padding: 6px 12px; color: {self.TEXT}; }}
QCheckBox {{ color: {self.TEXT2}; spacing: 6px; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 4px; border: 1px solid {self.BORDER}; }}
QCheckBox::indicator:checked {{ background: {self.ACCENT}; border-color: {self.ACCENT}; }}
QSlider::groove:horizontal {{ height: 4px; background: {self.BORDER}; border-radius: 2px; }}
QSlider::handle:horizontal {{ background: {self.ACCENT}; width: 14px; height: 14px; margin: -5px 0; border-radius: 7px; }}
QSlider::sub-page:horizontal {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {self.GRADIENT_1}, stop:1 {self.GRADIENT_2}); border-radius: 2px; }}
QProgressBar {{ background: {self.SURFACE2}; border: 1px solid {self.BORDER}; border-radius: 6px; text-align: center; color: {self.TEXT2}; font-size: 10px; }}
QProgressBar::chunk {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {self.GRADIENT_1}, stop:1 {self.GRADIENT_2}); border-radius: 6px; }}
QMenu {{ background: {self.SURFACE}; border: 1px solid {self.BORDER}; border-radius: 8px; padding: 4px; }}
QMenu::item {{ padding: 6px 24px; border-radius: 4px; }}
QMenu::item:selected {{ background: {self.ACCENT}20; }}
"""


# Singleton
C = _ThemeState()

# Backward-compat aliases (deprecated — use C.BG etc.)
C_BG = C.BG
C_SURFACE = C.SURFACE
C_SURFACE2 = C.SURFACE2
C_SURFACE3 = C.SURFACE3
C_ACCENT = C.ACCENT
C_ACCENT2 = C.ACCENT2
C_ACCENT_GLOW = C.ACCENT_GLOW
C_SECONDARY = C.SECONDARY
C_SUCCESS = C.SUCCESS
C_WARNING = C.WARNING
C_ERROR = C.ERROR
C_INFO = C.INFO
C_TEXT = C.TEXT
C_TEXT2 = C.TEXT2
C_TEXT3 = C.TEXT3
C_BORDER = C.BORDER
C_BORDER2 = C.BORDER2
C_GRADIENT_1 = C.GRADIENT_1
C_GRADIENT_2 = C.GRADIENT_2
C_GRADIENT_3 = C.GRADIENT_3
C_GLASS = C.GLASS
C_GLASS2 = C.GLASS2
C_GLASS_HOVER = C.GLASS_HOVER
