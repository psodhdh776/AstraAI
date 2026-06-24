import re
import json
import os
import logging
import threading
import time
import queue
from pathlib import Path

logger = logging.getLogger("Astra.VoiceEngine")

VOICE_COMMANDS = {
    "чат": ("chat", 1),
    "заметки": ("notes", 2),
    "система": ("system", 3),
    "аналитика": ("analytics", 4),
    "главная": ("dashboard", 0),
    "домой": ("dashboard", 0),
    "настройки": ("settings", None),
    "скриншот": ("screenshot", None),
    "помощь": ("help", None),
    "справка": ("help", None),
    "стоп": ("stop", None),
    "хватит": ("stop", None),
    "тихо": ("silent", None),
    "включи звук": ("unsilent", None),
    "выйти": ("quit", None),
    "пока": ("quit", None),
}


class VoiceEngine:
    def __init__(self, assistant):
        self.assistant = assistant
        self.listening = False
        self._thread = None
        self._wake_word = "астра"
        self._use_online = False
        self._model = None
        self._recognizer = None
        self._microphone = None
        self._init_offline()
        if not self._model:
            self._init_online()

    def _init_offline(self):
        try:
            from vosk import Model, KaldiRecognizer
            model_paths = [
                r"C:\Users\admin\Desktop\AbsoluteAssistant\models\vosk",
                r"C:\Users\admin\Desktop\AbsoluteAssistant\data\vosk",
                str(Path.home() / ".cache" / "vosk"),
            ]
            for mp in model_paths:
                if os.path.isdir(mp) and any(f.endswith(".vosk") or "vosk" in f.lower() for f in os.listdir(mp) if os.path.isdir(os.path.join(mp, f))):
                    self._model = Model(mp)
                    logger.info("Vosk model loaded from %s", mp)
                    break
            if self._model is None:
                for mp in model_paths:
                    if os.path.isdir(mp):
                        try:
                            self._model = Model(mp)
                            logger.info("Vosk model loaded from %s", mp)
                            break
                        except Exception:
                            continue
        except ImportError:
            logger.info("Vosk not installed, falling back to online STT")
        except Exception as e:
            logger.warning("Vosk init failed: %s", e)

    def _init_online(self):
        try:
            import speech_recognition as sr
            self._recognizer = sr.Recognizer()
            self._microphone = sr.Microphone()
            self._use_online = True
            logger.info("Online STT (Google) initialized")
        except Exception as e:
            logger.warning("Online STT init failed: %s", e)
            self._recognizer = None
            self._microphone = None

    def start(self, callback):
        if self.listening or (not self._model and not self._recognizer):
            return False
        self.listening = True
        self._callback = callback
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return True

    def stop(self):
        self.listening = False
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

    def _loop(self):
        import sounddevice as sd
        samplerate = 16000

        try:
            logger.info("Voice engine listening started")
        except Exception as e:
            logger.error("Audio init failed: %s", e)
            self.listening = False
            return

        if self._model and not self._use_online:
            from vosk import KaldiRecognizer
            rec = KaldiRecognizer(self._model, samplerate)
            rec.SetWords(False)

            def callback(indata, frames, time_info, status):
                if not self.listening:
                    raise sd.CallbackStop
                if rec.AcceptWaveform(indata.tobytes()):
                    result = json.loads(rec.Result())
                    text = result.get("text", "").strip()
                    if text:
                        self._handle_text(text)

            try:
                with sd.InputStream(samplerate=samplerate, channels=1,
                                    dtype='int16', callback=callback):
                    while self.listening:
                        sd.sleep(100)
            except Exception as e:
                logger.debug("Vosk stream: %s", e)
        elif self._use_online and self._recognizer:
            import speech_recognition as sr
            import sounddevice as sd
            try:
                with self._microphone as source:
                    self._recognizer.adjust_for_ambient_noise(source, duration=0.3)
            except Exception:
                pass
            while self.listening:
                try:
                    with self._microphone as source:
                        audio = self._recognizer.listen(source, timeout=1, phrase_time_limit=8)
                    text = self._recognizer.recognize_google(audio, language="ru-RU")
                    if text:
                        self._handle_text(text)
                except sr.WaitTimeoutError:
                    continue
                except sr.UnknownValueError:
                    continue
                except Exception as e:
                    logger.debug("Online STT: %s", e)
                    time.sleep(0.5)
        else:
            time.sleep(0.5)

        self.listening = False

    def _handle_text(self, text):
        tl = text.lower().strip()
        logger.info("Recognized: %s", tl)

        # Wake word check
        if self._wake_word and self._wake_word not in tl:
            return

        # Strip wake word
        cmd = re.sub(r'\b' + re.escape(self._wake_word) + r'\b', '', tl).strip()
        if not cmd:
            return

        # Check voice commands
        action = self._match_command(cmd)
        if action:
            self._callback({"action": action, "text": cmd, "raw": text})
            return

        # Fallback: send to assistant
        self._callback({"action": "chat", "text": cmd, "raw": text})

    def _match_command(self, text):
        for pattern, (action, _) in VOICE_COMMANDS.items():
            if pattern in text:
                return action
        return None

    def get_action_data(self, action):
        for pattern, (act, tab_idx) in VOICE_COMMANDS.items():
            if act == action:
                return {"action": action, "tab_index": tab_idx}
        return {"action": action, "tab_index": None}
