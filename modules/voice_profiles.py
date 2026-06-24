"""
Voice profiles — different wake-word and TTS settings per user/profile.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger("Astra.VoiceProfiles")

PROFILES_FILE = Path(__file__).parent.parent / "data" / "voice_profiles.json"

DEFAULT_PROFILES = {
    "default": {
        "name": "Основной",
        "wake_word": "астра",
        "voice_enabled": True,
        "tts_rate": 160,
        "tts_volume": 0.9,
    }
}


def _load():
    if PROFILES_FILE.exists():
        try:
            return json.loads(PROFILES_FILE.read_text("utf-8"))
        except Exception as e:
            logger.warning("Voice profiles load: %s", e)
    return dict(DEFAULT_PROFILES)


def _save(profiles):
    PROFILES_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROFILES_FILE.write_text(json.dumps(profiles, ensure_ascii=False, indent=2), encoding="utf-8")


def get_profiles():
    return _load()


def get_profile(name="default"):
    profiles = _load()
    return profiles.get(name, profiles.get("default", DEFAULT_PROFILES["default"]))


def save_profile(name, data):
    profiles = _load()
    profiles[name] = data
    _save(profiles)
    return {"status": "ok", "profile": name}


def delete_profile(name):
    if name == "default":
        return {"error": "Cannot delete default profile"}
    profiles = _load()
    if name in profiles:
        del profiles[name]
        _save(profiles)
        return {"status": "ok"}
    return {"error": f"Profile '{name}' not found"}


def apply_profile(assistant, name="default"):
    profile = get_profile(name)
    if hasattr(assistant, '_voice_engine') and assistant._voice_engine:
        assistant._voice_engine._wake_word = profile.get("wake_word", "астра")
    assistant.voice_enabled = profile.get("voice_enabled", True)
    if hasattr(assistant, 'tts_engine') and assistant.tts_engine:
        try:
            assistant.tts_engine.setProperty("rate", profile.get("tts_rate", 160))
            assistant.tts_engine.setProperty("volume", profile.get("tts_volume", 0.9))
        except Exception:
            pass
    return profile
