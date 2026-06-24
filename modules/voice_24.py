"""
24/7 voice assistant — always listening in background with wake-word.
"""
import logging
import threading
import time
import json
import re
import sounddevice as sd
import numpy as np

logger = logging.getLogger("Astra.Voice24")

SAMPLE_RATE = 16000
WAKE_WORD = "астра"
SILENCE_THRESHOLD = 500


class VoiceAssistant24:
    def __init__(self, assistant):
        self.assistant = assistant
        self._running = False
        self._thread = None
        self._wake_word = WAKE_WORD
        self._vosk_model = None
        self._recognizer = None
        self._try_vosk()

    def _try_vosk(self):
        try:
            from vosk import Model, KaldiRecognizer
            paths = [
                r"C:\Users\admin\Desktop\AbsoluteAssistant\models\vosk",
                str(Path.home() / ".cache" / "vosk"),
            ]
            from pathlib import Path
            for p in paths:
                if Path(p).exists():
                    self._vosk_model = Model(p)
                    self._recognizer = KaldiRecognizer(self._vosk_model, SAMPLE_RATE)
                    logger.info("Vosk loaded for 24/7")
                    break
        except Exception:
            pass
        if not self._vosk_model:
            logger.info("No Vosk model, 24/7 voice disabled")

    def set_wake_word(self, word):
        self._wake_word = word.lower().strip()

    def start(self):
        if self._running or not self._vosk_model:
            return False
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return True

    def stop(self):
        self._running = False

    def _loop(self):
        import sounddevice as sd
        rec = self._recognizer.__class__(self._vosk_model, SAMPLE_RATE)
        rec.SetWords(False)

        def callback(indata, frames, time_info, status):
            if not self._running:
                raise sd.CallbackStop
            if np.max(np.abs(indata)) < SILENCE_THRESHOLD / 32768:
                return
            if rec.AcceptWaveform(indata.tobytes()):
                result = json.loads(rec.Result())
                text = result.get("text", "").strip().lower()
                if text:
                    self._on_speech(text)

        try:
            with sd.InputStream(samplerate=SAMPLE_RATE, channels=1,
                                dtype='int16', callback=callback):
                while self._running:
                    sd.sleep(100)
        except Exception as e:
            logger.warning("24/7 voice: %s", e)
        self._running = False

    def _on_speech(self, text):
        if self._wake_word and self._wake_word in text:
            cmd = re.sub(r'\b' + re.escape(self._wake_word) + r'\b', '', text).strip()
            if not cmd:
                return
            logger.info("Wake word detected: %s", cmd)
            cb = getattr(self.assistant, '_voice_callback', None)
            if cb:
                cb(cmd)
            elif hasattr(self.assistant, 'process'):
                result = self.assistant.process(cmd)
                if hasattr(self.assistant, '_speak') and self.assistant.voice_enabled:
                    self.assistant._speak(result or "Слушаю")
