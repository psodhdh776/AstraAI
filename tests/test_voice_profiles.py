import pytest
import tempfile
from pathlib import Path
from modules.voice_profiles import (
    get_profiles, get_profile, save_profile, delete_profile, apply_profile
)


@pytest.fixture(autouse=True)
def _patch_profiles_file(monkeypatch):
    import modules.voice_profiles as vp
    with tempfile.TemporaryDirectory() as tmp:
        vp.PROFILES_FILE = Path(tmp) / "voice_profiles.json"
        yield


class TestVoiceProfiles:
    def test_get_profiles_default(self):
        profiles = get_profiles()
        assert "default" in profiles
        assert profiles["default"]["name"] == "Основной"
        assert profiles["default"]["wake_word"] == "астра"

    def test_get_profile_default(self):
        profile = get_profile()
        assert profile["name"] == "Основной"

    def test_get_profile_nonexistent_falls_back(self):
        profile = get_profile("nonexistent")
        assert profile is not None

    def test_save_and_get_profile(self):
        data = {"name": "Test", "wake_word": "test", "voice_enabled": True,
                "tts_rate": 200, "tts_volume": 0.5}
        result = save_profile("test_profile", data)
        assert result["status"] == "ok"

        loaded = get_profile("test_profile")
        assert loaded["name"] == "Test"
        assert loaded["wake_word"] == "test"

    def test_save_profile_overwrites(self):
        save_profile("dup", {"name": "First"})
        save_profile("dup", {"name": "Second"})
        loaded = get_profile("dup")
        assert loaded["name"] == "Second"

    def test_delete_profile(self):
        save_profile("del_me", {"name": "To Delete"})
        result = delete_profile("del_me")
        assert result["status"] == "ok"
        assert get_profile("del_me") is not None

    def test_delete_default_profile_fails(self):
        result = delete_profile("default")
        assert "error" in result

    def test_delete_nonexistent_profile(self):
        result = delete_profile("ghost")
        assert "error" in result

    def test_apply_profile(self):
        class FakeVoiceEngine:
            _wake_word = "астра"
        class FakeTtsEngine:
            def setProperty(self, k, v):
                pass
        class FakeAssistant:
            _voice_engine = FakeVoiceEngine()
            tts_engine = FakeTtsEngine()
            voice_enabled = False

        save_profile("test_apply", {
            "name": "Apply Test", "wake_word": "test_word",
            "voice_enabled": True, "tts_rate": 180, "tts_volume": 0.8
        })
        a = FakeAssistant()
        result = apply_profile(a, "test_apply")
        assert result["name"] == "Apply Test"
        assert a._voice_engine._wake_word == "test_word"
        assert a.voice_enabled is True
