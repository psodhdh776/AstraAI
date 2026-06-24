"""Tests for EmotionEngine — sentiment and mood detection."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "modules"))

import pytest
from emotion_engine import EmotionEngine


class TestEmotionEngine:
    def setup_method(self):
        self.em = EmotionEngine()

    def test_analyze_positive(self):
        result = self.em.analyze("Я так счастлив! Всё отлично!")
        assert "primary" in result
        assert "confidence" in result

    def test_analyze_negative(self):
        result = self.em.analyze("Мне очень грустно и одиноко")
        assert result["primary"] is not None

    def test_analyze_neutral(self):
        result = self.em.analyze("Сегодня вторник")
        assert result["primary"] is not None

    def test_empathetic_response(self):
        self.em.analyze("Мне грустно")
        response = self.em.get_empathetic_response()
        assert isinstance(response, str)
        assert len(response) > 0

    def test_should_empathize(self):
        result = self.em.analyze("Я ужасно себя чувствую")
        assert isinstance(self.em.should_empathize(result), bool)

    def test_should_not_empathize_neutral(self):
        result = self.em.analyze("2 + 2 = 4")
        # neutral mood_value ~0.5 should not trigger empathy
        assert self.em.should_empathize(result) is False

    def test_average_emotion(self):
        self.em.analyze("Я счастлив")
        self.em.analyze("Мне грустно")
        avg = self.em.get_average_emotion()
        assert avg is not None

    def test_mood_report(self):
        self.em.analyze("Отлично!")
        self.em.analyze("Прекрасно!")
        report = self.em.get_mood_report()
        assert isinstance(report, str)
        assert len(report) > 0

    def test_suggest_activity(self):
        self.em.analyze("Мне скучно")
        activity = self.em.suggest_activity()
        assert isinstance(activity, str)

    def test_mood_history(self):
        for _ in range(5):
            self.em.analyze("Всё хорошо")
        assert len(self.em.emotion_history) >= 5
