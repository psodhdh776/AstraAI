"""Tests for chat engine components."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "modules"))

import pytest
from chat_engine import (
    SemanticParser, DialogueStateMachine, PersonalityCore,
    CreativeEngine, SelfLearning,
)


class TestSemanticParser:
    def setup_method(self):
        self.p = SemanticParser()

    def test_parse_basic(self):
        result = self.p.parse("Привет!")
        assert isinstance(result, dict)
        assert "intent" in result

    def test_parse_with_context(self):
        result = self.p.parse("Как дела?", {"last_intent": "greeting"})
        assert result is not None


class TestDialogueStateMachine:
    def setup_method(self):
        self.dsm = DialogueStateMachine()

    def test_transition(self):
        stage = self.dsm.transition("greeting")
        assert isinstance(stage, str)

    def test_conversation_stage(self):
        self.dsm.transition("greeting")
        self.dsm.transition("ask_question")
        stage = self.dsm.get_conversation_stage()
        assert stage is not None

    def test_should_change_topic(self):
        assert isinstance(self.dsm.should_change_topic(), bool)


class TestPersonalityCore:
    def setup_method(self):
        self.p = PersonalityCore()

    def test_adjust_mood(self):
        self.p.adjust_mood("express_positive")
        assert self.p.should_use_emoji() in (True, False)

    def test_greeting(self):
        g = self.p.get_greeting()
        assert isinstance(g, str)
        assert len(g) > 0

    def test_sign_off(self):
        s = self.p.sign_off()
        assert isinstance(s, str)


class TestCreativeEngine:
    def setup_method(self):
        self.ce = CreativeEngine()

    def test_generate_story(self):
        story = self.ce.generate_story()
        assert isinstance(story, str)
        assert len(story) > 10

    def test_generate_joke(self):
        joke = self.ce.generate_joke()
        assert isinstance(joke, str)

    def test_generate_poem(self):
        poem = self.ce.generate_poem("любовь")
        assert isinstance(poem, str)

    def test_generate_idea(self):
        idea = self.ce.generate_idea("путешествие")
        assert isinstance(idea, str)

    def test_generate_advice(self):
        advice = self.ce.generate_advice("работа")
        assert isinstance(advice, str)


class TestSelfLearning:
    def setup_method(self):
        self.sl = SelfLearning()

    def test_learn_from_feedback(self):
        self.sl.learn_from_feedback("привет", "greeting")
        best = self.sl.get_best_intent_for("привет")
        assert best is None or best == "greeting"

    def test_learn_from_response(self):
        self.sl.learn_from_response("greeting", "positive")
        report = self.sl.get_quality_report()
        assert isinstance(report, dict)

    def test_learned_words(self):
        self.sl.learn_from_feedback("я люблю Python", "express_love")
        self.sl.learn_from_feedback("Python программирование", "topic_programming")
        words = self.sl.get_learned_words(min_freq=1)
        assert isinstance(words, dict)

    def test_quality_report(self):
        self.sl.learn_from_response("greeting", "positive")
        self.sl.learn_from_response("farewell", "negative")
        report = self.sl.get_quality_report()
        assert isinstance(report, dict)
