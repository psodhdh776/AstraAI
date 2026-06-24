"""
AbsoluteAssistant — main entry point.
Все Gemini-зависимости удалены. Используются только локальные движки.
"""

import re, html, json, subprocess, datetime, time, random, webbrowser, os, hashlib, base64, struct, sys, shutil, threading, logging
from pathlib import Path
from collections import defaultdict

logger = logging.getLogger("Astra.Assistant")
from modules.voice_engine import VoiceEngine
from modules.memory_system import MemorySystem

__version__ = "2.2"

# ── КРИПТО (без внешних зависимостей) ──
_KEY: bytes | None = None

def _get_key() -> bytes:
    global _KEY
    if _KEY is None:
        raw = (__file__ + "astra::v2::crypto::2025").encode()
        _KEY = hashlib.sha256(raw).digest()
    return _KEY

def _xor(data: bytes, key: bytes) -> bytes:
    return bytes(d ^ key[i % len(key)] for i, d in enumerate(data))

def encrypt_plaintext(plain: str) -> str:
    if not plain:
        return ""
    try:
        payload = _xor(plain.encode(), _get_key())
        return base64.urlsafe_b64encode(payload).decode()
    except Exception:
        return plain

def decrypt_plaintext(token: str) -> str:
    if not token:
        return ""
    try:
        payload = base64.urlsafe_b64decode(token.encode())
        return _xor(payload, _get_key()).decode()
    except Exception:
        return token

# ── ПРИЛОЖЕНИЯ ──
APPS = {
    "браузер": "start msedge",
    "edge": "start msedge",
    "chrome": "start chrome",
    "калькулятор": "calc",
    "блокнот": "notepad",
    "проводник": "explorer",
    "cmd": "cmd",
    "терминал": "wt",
    "диспетчер": "taskmgr",
    "настройки": "start ms-settings:",
    "почта": "outlook",
    "excel": "excel",
    "word": "winword",
    "powerpoint": "powerpnt",
    "skype": "skype",
    "telegram": "telegram",
    "discord": "discord",
    "steam": "steam",
    "spotify": "spotify",
    "vscode": "code",
    "pycharm": "pycharm",
    "sublime": "sublime_text",
    "slack": "slack",
}

# ── DATA DIR ──
if getattr(sys, "frozen", False) or hasattr(sys, "_MEIPASS"):
    _appdata = Path(os.environ.get("APPDATA", str(Path.home() / ".astra"))) / "AstraAI"
    DATA_DIR = _appdata / "data"
else:
    DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ═══════════════════════════════════════════════════════════════
#  ASSISTANT
# ═══════════════════════════════════════════════════════════════

class Assistant:
    """Главный класс ассистента (без Gemini)."""

    def __init__(self):
        self._started = time.time()
        self.db = None
        self.dialogue = None
        self.emotion = None
        self.core = None
        self.thinker = None
        self.fractal = None
        self.caps = None
        self.knowledge = None
        self.plugins = None
        self._names = {}
        self._thinking_ctx = {}
        self._auto_start = False
        self.tts_engine = None
        self.recognizer = None
        self.microphone = None
        self.listening = False
        self._listen_thread = None
        self._web_engine = None

        # Config defaults
        self.api_key = ""
        self.voice_enabled = True
        self.text_model = "local"
        self.image_model = "local"

        self.history: list[dict] = []
        self.notes: list[dict] = []
        self.reminders: list[dict] = []
        self.theme_mode = "dark"

        self._load_all()

        # Dialogue engine
        try:
            from modules.dialogue_engine import DialogueEngine
            self.dialogue = DialogueEngine()
            if self.db:
                self.dialogue.load_state(self.db)
        except Exception as e:
            logger.warning("DialogueEngine init: %s", e)

        # Emotion engine
        try:
            from modules.emotion_engine import EmotionEngine
            self.emotion = EmotionEngine()
        except Exception as e:
            logger.warning("EmotionEngine init: %s", e)

        # Memory system (единая память)
        self.memory = MemorySystem()

        # FractalProcessor (многомерный фрактальный анализ)
        try:
            from modules.fractal_processor import FractalProcessor
            self.fractal = FractalProcessor()
            logger.info("FractalProcessor инициализирован")
        except Exception as e:
            logger.warning("FractalProcessor init: %s", e)
            self.fractal = None

        # Thinking engine v2 (многошаговое мышление + обучение)
        try:
            from modules.thinking_engine import ThinkingEngineV2
            self.thinker = ThinkingEngineV2()
            logger.info("ThinkingEngineV2 инициализирован")
            # Передаём имя пользователя из долговременной памяти
            name = self.memory.long.profile.get("name")
            if name:
                self.thinker.context["user_name"] = name
                self.thinker.learn_fact("user_name", name)
        except Exception as e:
            logger.warning("ThinkingEngineV2 init: %s", e)
            try:
                from modules.thinking_engine import ThinkingEngine
                self.thinker = ThinkingEngine()
            except Exception:
                pass

        # Voice engine
        self._init_voice()

        # Plugin system
        try:
            from modules.plugin_base import PluginManager
            self.plugins = PluginManager()
            self.plugins.load_builtins(self)
            ext_dir = Path(__file__).parent.parent / "plugins"
            if ext_dir.exists():
                self.plugins.load_directory(str(ext_dir))
            logger.info("Plugins loaded: %d", len(self.plugins.plugins))
        except Exception as e:
            logger.warning("Plugin init: %s", e)

        # CoreModel (main engine dispatcher)
        try:
            from modules.core_model import CoreModel
            self.core = CoreModel(assistant=self)
            self.core.init_from_assistant(self)
            logger.info("CoreModel initialized")
        except Exception as e:
            logger.warning("CoreModel init: %s", e)
            self.core = None

        # CAPS
        try:
            from modules.cognitive_pipeline import CapsLearner, CapsProactive
            self.caps_learner = CapsLearner(self)
            self.caps_proactive = CapsProactive(self)
        except Exception as e:
            logger.warning("CAPS init: %s", e)
            self.caps_learner = self.caps_proactive = None

        # MCP server
        self._mcp_thread = None
        self._auto_start_mcp()

        logger.info("Assistant initialized in %.2fs", time.time() - self._started)

    # ── properties ──

    @property
    def gemini_ready(self):
        return False

    # ── persistence ──

    def _load_all(self):
        self._init_storage()
        self.load_config()
        self._load_history()
        self._load_notes()
        self._load_reminders()

    def _init_storage(self):
        try:
            from modules.storage import Storage
            self.db = Storage(str(DATA_DIR / "assistant.db"))
            logger.info("DB: %s", self.db.db_path)
        except Exception as e:
            logger.error("Storage init failed: %s", e)
            self.db = None

    def load_config(self):
        if not self.db:
            return
        try:
            data = self.db.get_all_config()
            raw = data.get("api_key", "")
            self.api_key = decrypt_plaintext(raw) if raw else ""
            self.voice_enabled = data.get("voice_enabled", "1") == "1"
            self.text_model = data.get("text_model", "local")
            self.image_model = data.get("image_model", "local")
            self.theme_mode = data.get("theme_mode", "dark")
        except Exception as e:
            logger.warning("Config load: %s", e)

    def save_config(self, **kwargs):
        for k, v in kwargs.items():
            if k == "api_key":
                v = encrypt_plaintext(v) if v else ""
            setattr(self, k, v)
        if self.db:
            try:
                stored_key = encrypt_plaintext(self.api_key) if self.api_key else ""
                self.db.set_config("api_key", stored_key)
                self.db.set_config("voice_enabled", "1" if self.voice_enabled else "0")
                self.db.set_config("text_model", self.text_model)
                self.db.set_config("image_model", self.image_model)
                self.db.set_config("theme_mode", self.theme_mode)
            except Exception as e:
                logger.warning("Config save: %s", e)

    def get_auto_start(self) -> bool:
        return self._auto_start

    def set_auto_start(self, enable: bool):
        self._auto_start = enable
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE)
            if enable:
                exe = sys.executable
                winreg.SetValueEx(key, "AstraAI", 0, winreg.REG_SZ, f'"{exe}"')
            else:
                try:
                    winreg.DeleteValue(key, "AstraAI")
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception as e:
            logger.warning("Auto-start: %s", e)

    # ── history ──

    def _load_history(self):
        if not self.db:
            return
        try:
            self.history = self.db.get_history(limit=200) or []
        except Exception as e:
            logger.warning("Load history: %s", e)
            self.history = []

    def _save_history(self):
        if not self.db:
            return
        try:
            for h in self.history[-5:]:
                self.db.add_history(h.get("role", "user"), h.get("content", ""))
        except Exception as e:
            logger.warning("Save history: %s", e)

    def add_history(self, role: str, content: str):
        if not content:
            return
        self.history.append({"role": role, "content": content, "time": datetime.datetime.now().isoformat()})
        if len(self.history) > 200:
            self.history = self.history[-200:]
        if self.db:
            try:
                self.db.add_history(role, content)
            except Exception as e:
                logger.warning("DB add_history: %s", e)
        # Memory system — наблюдаем каждое событие
        if hasattr(self, "memory"):
            intent = getattr(self, "_thinking_ctx", {}).get("intent", "chat")
            self.memory.observe(role, content, intent)

    def search_history(self, query: str) -> list[dict]:
        q = query.lower()
        return [h for h in self.history if q in h.get("content", "").lower()]

    # ── notes ──

    def _load_notes(self):
        if not self.db:
            return
        try:
            self.notes = self.db.get_notes() or []
        except Exception as e:
            logger.warning("Load notes: %s", e)
            self.notes = []

    def _save_notes(self):
        if not self.db:
            return
        try:
            self.db.save_notes(self.notes)
        except Exception as e:
            logger.warning("Save notes: %s", e)

    # ── reminders ──

    def _load_reminders(self):
        if not self.db:
            return
        try:
            self.reminders = self.db.get_reminders() or []
        except Exception as e:
            logger.warning("Load reminders: %s", e)
            self.reminders = []

    def add_reminder(self, text: str, minutes: int):
        due = (datetime.datetime.now() + datetime.timedelta(minutes=minutes)).isoformat()
        r = {"text": text, "due": due, "created": datetime.datetime.now().isoformat()}
        self.reminders.append(r)
        if self.db:
            try:
                self.db.add_reminder(text, minutes)
            except Exception as e:
                logger.warning("DB add_reminder: %s", e)

    def get_due_reminders(self) -> list[dict]:
        now = datetime.datetime.now()
        due = []
        keep = []
        for r in self.reminders:
            try:
                dt = datetime.datetime.fromisoformat(r["due"])
                if dt <= now:
                    due.append(r)
                else:
                    keep.append(r)
            except Exception:
                keep.append(r)
        self.reminders = keep
        return due

    def play_notification(self):
        try:
            import winsound
            winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS)
        except Exception:
            pass

    # ── voice ──

    def _init_voice(self):
        try:
            from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
            self._voice_player = QMediaPlayer()
            self._voice_output = QAudioOutput()
            self._voice_player.setAudioOutput(self._voice_output)
        except Exception:
            self._voice_player = None
            self._voice_output = None

        try:
            import speech_recognition as sr
            self.recognizer = sr.Recognizer()
            self.microphone = sr.Microphone()
        except Exception:
            self.recognizer = None
            self.microphone = None

    def _speak(self, text: str):
        if not self.voice_enabled or not text:
            return
        if hasattr(self, '_status_bar') and self._status_bar:
            try:
                self._status_bar.set_speaking(True)
            except Exception:
                pass
        try:
            import pyttsx3
            if self.tts_engine is None:
                self.tts_engine = pyttsx3.init()
                self.tts_engine.setProperty("rate", 160)
                self.tts_engine.setProperty("volume", 0.9)
                voices = self.tts_engine.getProperty("voices")
                for v in voices:
                    if "russian" in v.name.lower() or (hasattr(v, "languages") and v.languages and "russian" in v.languages[0].lower()):
                        self.tts_engine.setProperty("voice", v.id)
                        break
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
        except Exception:
            pass
        if hasattr(self, '_status_bar') and self._status_bar:
            try:
                self._status_bar.set_speaking(False)
            except Exception:
                pass

    def start_listening(self, callback) -> bool:
        if not hasattr(self, '_voice_engine'):
            self._voice_engine = VoiceEngine(self)
        ve = self._voice_engine

        def cb(data):
            action = data.get("action")
            text = data.get("text", "")
            if action == "chat":
                callback(text)
            elif action == "stop":
                self.stop_listening()
                callback(None)
            elif action == "quit":
                callback(None)
                from PySide6.QtWidgets import QApplication
                QApplication.quit()
            elif action == "silent":
                self.voice_enabled = False
                callback(None)
            elif action == "unsilent":
                self.voice_enabled = True
                callback(None)
            elif action == "screenshot":
                result = self._do_screenshot()
                callback(result)
            elif action == "help":
                callback("Я понимаю команды: навигация (чат, заметки, система, аналитика), скриншот, настройки, выход. А ещё вопросы и разговоры.")
            else:
                callback(text)

        ok = ve.start(cb)
        if ok:
            self.listening = True
        return ok

    def stop_listening(self):
        if hasattr(self, '_voice_engine'):
            self._voice_engine.stop()
        self.listening = False

    # ── MCP ──

    def _auto_start_mcp(self):
        pass

    # ── MAIN PROCESS ──

    def process(self, text: str) -> str:
        logger.debug("Assistant.process: entry text=%r", text[:120])
        text = text.strip()
        if not text:
            logger.debug("Assistant.process: empty text -> ''")
            return ""

        # Image extension filter
        _IMG_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".ico", ".svg")
        if any(ext in text.lower() for ext in _IMG_EXTS):
            logger.debug("Assistant.process: image reference detected")
            self.add_history("user", text)
            return "Я — текстова модель і не бачу зображень. Опиши словами ✨"

        # File reference pre-check
        if re.search(r'\[Файл:\s*[^\]]+\]', text):
            logger.debug("Assistant.process: file reference detected")
            self.add_history("user", text)
            return "Я не підтримую файли. Будь ласка, використовуй текст або завантаж зображення."

        tl = text.lower()

        # Garbage detection
        if self._is_garbage(tl):
            logger.debug("Assistant.process: garbage -> ''")
            return ""

        # Fast path: simple greetings
        if tl in ("привет", "здравствуй", "хай", "hello", "hi", "добрый день", "доброе утро", "добрый вечер"):
            greeting = random.choice([
                "Привет! Чем могу помочь?",
                "Здравствуй! Я слушаю тебя.",
                "Приветствую! Задавай вопрос.",
                "Хай! Чем займёмся?",
            ])
            self.add_history("user", text)
            self.add_history("assistant", greeting)
            self._speak(greeting)
            return greeting

        # Fast path: how are you
        if tl in ("как дела", "как ты", "what's up", "how are you", "дела"):
            reply = random.choice([
                "У меня всё отлично! Чем могу помочь?",
                "Работаю в фоне, всё хорошо. Спрашивай!",
                "Всё супер! Я готов помочь.",
            ])
            self.add_history("user", text)
            self.add_history("assistant", reply)
            self._speak(reply)
            return reply

        # Fast path: simple questions
        if tl in ("кто ты", "что ты", "who are you", "что умеешь", "help", "помощь", "команды"):
            reply = (
                "Я Astra AI — твой голосовой ассистент. Умею:\n"
                "• Отвечать на вопросы\n"
                "• Создавать заметки\n"
                "• Напоминать о делах\n"
                "• Управлять системой\n"
                "• Интегрироваться с Home Assistant\n"
                "• Переводить текст\n"
                "• Работать через Telegram\n\n"
                "Просто спроси!"
            )
            self.add_history("user", text)
            self.add_history("assistant", reply)
            self._speak(reply)
            return reply

        # Plugin matching
        if self.plugins:
            matches = self.plugins.match(text, tl)
            if matches:
                best = matches[0]
                plugin = best.get("plugin")
                params = best.get("params", {})
                if plugin and hasattr(plugin, "execute"):
                    result = plugin.execute(params, self)
                    if result:
                        self.add_history("user", text)
                        self.add_history("assistant", result)
                        logger.debug("Assistant.process: plugin %s -> %r", plugin.name, result[:80])
                        return result

        # Thinking v2 (многошаговое мышление)
        try:
            if self.thinker and hasattr(self.thinker, "_reason_chain"):
                thought = self.thinker.think(text)
                self._thinking_ctx = thought or {}
            elif self.thinker:
                self._thinking_ctx = self.thinker.think(text, []) or {}
        except Exception as e:
            logger.debug("Assistant.process: think error: %s", e)

        # FractalProcessor enhancement
        if self.fractal:
            try:
                fractal_result = self.fractal.process(text)
                self._thinking_ctx["fractal"] = fractal_result
            except Exception as e:
                logger.debug("Assistant.process: fractal error: %s", e)

        # CoreModel
        if self.core:
            try:
                resp = self.core.process(text)
                logger.debug("Assistant.process: core -> %r", (resp or "")[:120])
                if resp and resp.strip() and resp != "__IMAGE_ERROR__":
                    self.add_history("user", text)
                    self.add_history("assistant", resp)
                    if self.fractal:
                        self.fractal.learn(text, resp, True)
                    self._speak(resp)
                    return resp
            except Exception as e:
                logger.warning("CoreModel process error: %s", e)

        # Local LLM (llama.cpp GGUF)
        try:
            from modules.local_llm import generate, start
            start()
            llm_resp = generate(text)
            if llm_resp and llm_resp.strip():
                self.add_history("user", text)
                self.add_history("assistant", llm_resp)
                self._speak(llm_resp)
                return llm_resp
        except Exception as e:
            logger.debug("Local LLM: %s", e)

        # Fallback: CAPS
        try:
            caps = __import__("modules.cognitive_pipeline", fromlist=["CognitivePipeline"])
            pipeline = caps.CognitivePipeline(self)
            resp = pipeline.execute(text)
            logger.debug("Assistant.process: CAPS -> %r", (resp or "")[:120])
            if resp and resp.strip() and resp != "__IMAGE_ERROR__":
                self.add_history("user", text)
                self.add_history("assistant", resp)
                self._speak(resp)
                return resp
        except Exception as e:
            logger.warning("CAPS fallback error: %s", e)

        # Final fallback: dialogue
        if self.dialogue:
            try:
                resp = self.dialogue.respond(text)
                if resp:
                    self.add_history("user", text)
                    self.add_history("assistant", resp)
                    self._speak(resp)
                    return resp
            except Exception as e:
                logger.warning("Dialogue fallback: %s", e)

        # Absolute fallback
        fallback = "Вибачте, я не можу відповісти на це питання. Будь ласка, спробуйте інакше."
        if self.fractal:
            self.fractal.learn(text, fallback, False)
        logger.debug("Assistant.process: all engines failed -> fallback")
        return fallback

    # ── COMMAND HANDLERS ──

    def _do_help(self) -> str:
        return (
            "��� �������� ������:\n"
            "- ������, ���, ������, ����������\n"
            "- ������, �����, �����������\n"
            "- ³ ��������, ���������\n"
            "- ������, ������������, ������\n"
            "- ���, �����, ���������\n"
            "- �����, �������� – �����������\n"
            "- ³ ���/���� – ���������\n"
            "- ����� ������/���� – ������\n"
            "- �������� – ���������, ��������, ������ ���"
        )

    def _do_time(self) -> str:
        return datetime.datetime.now().strftime("%H:%M")

    def _do_date(self) -> str:
        return datetime.datetime.now().strftime("%d.%m.%Y, %A")

    def _do_screenshot(self) -> str:
        try:
            import pyautogui
            path = str(Path.home() / "Pictures" / f"screenshot_{int(time.time())}.png")
            pyautogui.screenshot(path)
            return f"³������ ��������: {path}"
        except Exception as e:
            return f"������ ������: {e}"

    def _do_system(self) -> str:
        info = {}
        try:
            import psutil
            info["cpu"] = f"{psutil.cpu_percent(interval=0.5)}%"
            mem = psutil.virtual_memory()
            info["ram"] = f"{mem.percent}% ({mem.used // 1024**3}��/{mem.total // 1024**3}��)"
            info["disk"] = f"{psutil.disk_usage('/').percent}%"
            info["processes"] = len(psutil.pids())
            import platform
            info["os"] = f"{platform.system()} {platform.release()}"
            import socket
            info["host"] = socket.gethostname()
        except Exception:
            info["error"] = "psutil not available"
        return json.dumps(info, ensure_ascii=False, indent=2)

    def _do_processes(self) -> str:
        try:
            import psutil
            procs = sorted(psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]),
                key=lambda p: p.info.get("cpu_percent", 0) or 0, reverse=True)[:10]
            lines = ["CPU  %  MEM  %  PID  NAME"]
            for p in procs:
                lines.append(f"{p.info.get('cpu_percent', 0):>5.1f}  {p.info.get('memory_percent', 0):>5.1f}  {p.info['pid']:<6} {p.info['name'][:30]}")
            return "\n".join(lines)
        except Exception as e:
            return f"������: {e}"

    def _h_weather(self, city: str | None = None) -> str:
        if not city:
            city = "Moscow"
        try:
            import requests
            r = requests.get(f"https://wttr.in/{city}?format=%C+%t+%w+%h&lang=ru", timeout=10)
            if r.status_code == 200:
                return f"{city}: {r.text.strip()}"
            return "³ ��� �������� ������."
        except Exception as e:
            return f"������: {e}"

    def _h_web_search(self, query: str) -> str:
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=4))
            if not results:
                return "������ �� ������."
            lines = [f"�� {r['title']}: {r['href']}" for r in results]
            return "\n".join(lines)
        except Exception:
            webbrowser.open(f"https://google.com/search?q={query}")
            return f"�������� ����� � ��������: {query}"

    def _h_add_note(self, text: str) -> str:
        note = {"id": str(datetime.datetime.now().timestamp()), "text": text,
                "created": datetime.datetime.now().strftime("%d.%m.%Y %H:%M"), "done": False}
        self.notes.append(note)
        self._save_notes()
        return f"������� ���������: {text}"

    def _h_fast_search(self, query: str) -> str:
        q = query.lower()
        results = []
        for h in self.history:
            if q in h.get("content", "").lower():
                results.append(f"[{h.get('role','?')}] {h['content'][:100]}")
        for n in self.notes:
            if q in n.get("text", "").lower():
                results.append(f"[�������] {n['text'][:100]}")
        if not results:
            return "������ �� ������."
        return "\n".join(results[:10])

    def _h_mood_report(self, _=None) -> str:
        if not self.emotion:
            return "������ ������ ����������."
        return self.emotion.report()

    def _h_ai_engine(self, params: str | None = None) -> str:
        try:
            from modules.ai_engine import AIEngine
            engine = AIEngine()
            result = engine.generate(params or "say something")
            return result or "AI Engine �������� ������."
        except Exception as e:
            return f"AI Engine ������: {e}"

    def generate_image(self, prompt: str):
        return None, "Генерация изображений недоступна (локальный режим)."

    # ── UTILITIES ──

    def _is_garbage(self, tl: str) -> bool:
        garbage = ["блять", "сука", "пиздец", "хуй", "нахуй", "похуй", "херня",
                   "фигня", "ёбаный", "ебаный", "пидор", "гандон", "мудак",
                   "долбоеб", "дебил", "абьюз", "травля"]
        return any(g in tl for g in garbage)

    def _extract_city(self, text: str) -> str | None:
        tl = text.lower()
        for word in tl.split():
            if word in ("в", "во", "на", "в городе"):
                idx = tl.split().index(word)
                words = text.split()
                if idx + 1 < len(words):
                    return words[idx + 1].strip(".,!?")
        return None

    def _remember_preference(self, text: str):
        if not self.db:
            return
        patterns = [
            r"(?:зовут|имя|называют)\s+(\w+)",
            r"(?:я|меня)\s+(\w+)\s+(?:и|а|,)",  # context-based name extraction
        ]
        for pat in patterns:
            m = re.search(pat, text.lower())
            if m:
                name = m.group(1).capitalize()
                self._thinking_ctx["user_name"] = name
                break

    def _proactive_check(self) -> list[str]:
        suggestions = []
        try:
            if self.history:
                last = self.history[-1].get("content", "")
                if "привет" in last.lower():
                    suggestions.append("Спросить, как дела")
        except Exception:
            pass
        return suggestions

    def _think(self, text: str) -> str:
        if self.thinker:
            try:
                if hasattr(self.thinker, "_reason_chain"):
                    self._thinking_ctx = self.thinker.think(text) or {}
                else:
                    self._thinking_ctx = self.thinker.think(text, []) or {}
            except Exception as e:
                logger.debug("Think error: %s", e)
        return ""
