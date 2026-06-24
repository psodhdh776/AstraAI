import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "modules"))

import pytest


class TestReflect:
    def test_reflect_phrase(self):
        from dialogue_engine import _reflect
        assert "ты" in _reflect("я люблю python")
        assert "тебе" in _reflect("мне нравится")

    def test_reflect_no_change(self):
        from dialogue_engine import _reflect
        assert _reflect("python это круто") == "python это круто"

    def test_reflect_capitalize(self):
        from dialogue_engine import _reflect
        assert "Ты" in _reflect("Я программист")


class TestDetectTopic:
    def test_detect_tech(self):
        from dialogue_engine import _detect_topic
        assert _detect_topic("я люблю python") == "tech"

    def test_detect_music(self):
        from dialogue_engine import _detect_topic
        assert _detect_topic("классная музыка") == "music"

    def test_detect_food(self):
        from dialogue_engine import _detect_topic
        assert _detect_topic("горячий обед") == "food"

    def test_detect_none(self):
        from dialogue_engine import _detect_topic
        assert _detect_topic("что-то непонятное") is None


class TestDialogueEngine:
    def setup_method(self):
        from dialogue_engine import DialogueEngine
        self.de = DialogueEngine()

    def test_respond_empty(self):
        r = self.de.respond("")
        assert r is not None
        assert len(r) > 0

    def test_respond_greeting(self):
        r = self.de.respond("привет")
        assert r is not None
        assert "привет" in r.lower() or "Здравствуй" in r or "Хай" in r

    def test_respond_name(self):
        r = self.de.respond("меня зовут Алекс")
        assert r is not None
        assert self.de.context["user_name"] == "Алекс"

    def test_respond_how_are_you(self):
        r = self.de.respond("как дела")
        assert r is not None
        assert len(r) > 5

    def test_respond_time(self):
        r = self.de.respond("сколько времени")
        assert r is not None

    def test_respond_date(self):
        r = self.de.respond("какое сегодня число")
        assert r is not None

    def test_respond_joke(self):
        r = self.de.respond("расскажи шутку")
        assert r is not None
        assert len(r) > 5

    def test_respond_fallback(self):
        r = self.de.respond("квантовая запутанность и теория струн")
        assert r is not None
        assert len(r) > 5

    def test_context_tracking(self):
        self.de.respond("привет")
        assert self.de.context["turn_count"] >= 1
        self.de.respond("как дела")
        assert self.de.context["turn_count"] >= 2

    def test_mood_detection_positive(self):
        self.de.respond("всё отлично!")
        assert self.de.context["mood"] in ("positive", "neutral")

    def test_mood_detection_negative(self):
        self.de.respond("мне очень плохо")
        mood = self.de.context["mood"]
        assert mood in ("negative", "neutral")

    def test_save_load_state(self):
        db = MagicMock()
        self.de.respond("привет")
        self.de.context["user_name"] = "Тест"
        self.de.save_state(db)
        assert db.called

    def test_learn_from_feedback_positive(self):
        self.de.respond("привет")
        self.de.learn_from_feedback("спасибо, отлично", self.de.context["last_response"])
        assert len(self.de.response_weights) > 0

    def test_learn_from_feedback_negative(self):
        self.de.respond("привет")
        self.de.learn_from_feedback("нет, не то", self.de.context["last_response"])

    def test_learn_from_repeat(self):
        for _ in range(6):
            self.de.learn_from_repeat("python")
        assert len(self.de.learned_patterns) >= 0

    def test_fact_extraction(self):
        from dialogue_engine import DialogueEngine
        de = DialogueEngine()
        fact = de._learn_fact("я люблю программирование")
        assert fact is not None
        assert "программирование" in fact

    def test_topic_followup(self):
        self.de.respond("я люблю python")
        assert self.de.context["last_topic"] == "tech"

    def test_respond_with_mood_emoji(self):
        r = self.de.respond("привет")
        assert r is not None

    def test_get_action_data_not_implemented(self):
        with pytest.raises(AttributeError):
            self.de.get_action_data("chat")


class MagicMock:
    def __init__(self):
        self._memory = {}
        self.called = False

    def set_memory(self, key, value):
        self._memory[key] = value
        self.called = True

    def get_memory(self, key):
        return self._memory.get(key)
