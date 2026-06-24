"""Tests for cognitive pipeline — CapsQLearning, CapsLearner."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "modules"))

import pytest
from cognitive_pipeline import CapsQLearning, CapsLearner


class TestCapsQLearning:
    def setup_method(self):
        self.q = CapsQLearning()

    def test_choose_action(self):
        candidates = [{"path": "chat", "confidence": 0.8}, {"path": "semantic", "confidence": 0.5}]
        action = self.q.choose_action("greeting", 0.3, "stable", 0, candidates)
        assert action in ("chat", "semantic", "fallback", "explore")

    def test_learn(self):
        candidates = [{"path": "chat", "confidence": 0.8}]
        self.q.choose_action("greeting", 0.3, "stable", 0, candidates)
        self.q.learn(1.0)
        summary = self.q.get_q_summary()
        assert summary is not None

    def test_save_load(self):
        candidates = [{"path": "chat", "confidence": 0.8}]
        self.q.choose_action("greeting", 0.3, "stable", 0, candidates)
        self.q.learn(0.5)
        data = self.q.to_dict()
        assert "q_table" in data

        q2 = CapsQLearning()
        q2.from_dict(data)
        assert len(q2.q_table) >= 1


class TestCapsLearner:
    def setup_method(self):
        self.l = CapsLearner(None)

    def test_record_success(self):
        self.l.record_success("chat")
        rate = self.l.get_success_rate("chat")
        assert rate > 0

    def test_record_error(self):
        self.l.record_error("fallback")
        rate = self.l.get_error_rate("fallback")
        assert rate > 0

    def test_update_quality(self):
        self.l.update_quality("chat", 0.1)
        trend = self.l.get_quality_trend("chat")
        assert trend is not None

    def test_confusion_rate(self):
        self.l.record_success("chat")
        self.l.record_error("chat")
        self.l.record_success("chat")
        rate = self.l.get_confusion_rate()
        assert 0 <= rate <= 1

    def test_multiple_paths(self):
        self.l.record_success("chat")
        self.l.record_success("command")
        self.l.record_error("fallback")
        assert self.l.get_success_rate("chat") > 0
        assert self.l.get_success_rate("command") > 0
        assert self.l.get_error_rate("fallback") > 0
