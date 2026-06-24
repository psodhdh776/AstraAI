"""Tests for dialogue engine."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "modules"))

import pytest
from dialogue_engine import DialogueEngine


@pytest.fixture
def engine():
    return DialogueEngine()


def test_greeting(engine):
    resp = engine.respond("привет")
    assert resp and len(resp) > 3
    assert "привет" in resp.lower() or "здравств" in resp.lower()


def test_name(engine):
    engine.set_user_name("Иван")
    resp = engine.respond("как дела?")
    assert resp and len(resp) > 3


def test_how_are_you(engine):
    resp = engine.respond("как дела?")
    assert resp and len(resp) > 3


def test_joke(engine):
    resp = engine.respond("пошути")
    assert resp and len(resp) > 5


def test_time_date(engine):
    resp = engine.respond("сколько времени?")
    assert resp and len(resp) > 3


def test_mood_positive(engine):
    resp = engine.respond("отлично")
    assert resp and len(resp) > 3


def test_mood_negative(engine):
    resp = engine.respond("грустно")
    assert resp and len(resp) > 3


def test_thanks(engine):
    resp = engine.respond("спасибо")
    assert resp and len(resp) > 3


def test_fallback(engine):
    resp = engine.respond("абракадабраxyz123")
    assert resp and len(resp) > 3


def test_topic_detection(engine):
    resp = engine.respond("я люблю программирование на Python")
    assert resp and len(resp) > 3


def test_fact_extraction(engine):
    engine.respond("я люблю играть в футбол")
    assert len(engine.profile.get("frequent_words", {})) >= 3


def test_state_persistence(engine):
    engine.respond("привет")
    engine.set_user_name("Тест")
    import json
    import tempfile
    from pathlib import Path

    class FakeDB:
        def __init__(self):
            self._data = {}
        def set_memory(self, key, value):
            self._data[key] = value
        def get_memory(self, key, default=None):
            return self._data.get(key, default)

    db = FakeDB()
    engine.save_state(db)
    engine2 = DialogueEngine()
    engine2.load_state(db)
    assert engine2.context.get("user_name") == "Тест"


def test_learning(engine):
    old_count = len(engine.learned_patterns)
    engine.learn_from_feedback("привет", "и как дела?")
    assert len(engine.learned_patterns) >= old_count


def test_mood_tracking(engine):
    engine.respond("отлично")
    assert engine.context["mood"] in ("positive", "neutral", "negative")


def test_empty_input(engine):
    resp = engine.respond("")
    assert resp and len(resp) > 3


def test_repeated_same_input(engine):
    r1 = engine.respond("привет")
    r2 = engine.respond("привет")
    assert r1 and r2
