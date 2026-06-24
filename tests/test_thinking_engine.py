"""Tests for ThinkingEngineV2 — chain-of-thought reasoning engine."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "modules"))

import pytest
from thinking_engine import ThinkingEngineV2, Thought, TraceGraph


class TestThought:
    def test_creation(self):
        t = Thought("observe", "user said hello", 0.95)
        assert t.stage == "observe"
        assert t.content == "user said hello"
        assert t.score == 0.95

    def test_repr(self):
        t = Thought("observe", "test", 0.5)
        r = repr(t)
        assert "OBSERVE" in r or "observe" in r


class TestTraceGraph:
    def setup_method(self):
        self.g = TraceGraph()

    def test_add_node(self):
        idx = self.g.add(Thought("observe", "step 1"))
        assert idx == 0
        assert len(self.g.nodes) == 1

    def test_add_with_parent(self):
        p = self.g.add(Thought("observe", "parent"))
        c = self.g.add(Thought("reason", "child"), parent_idx=p)
        assert c == 1
        assert len(self.g.edges) == 1

    def test_to_text(self):
        self.g.add(Thought("observe", "first"))
        self.g.add(Thought("conclude", "second"))
        text = self.g.to_text()
        assert "first" in text
        assert "second" in text


class TestThinkingEngineV2:
    def setup_method(self):
        self.t = ThinkingEngineV2()

    def test_think_basic(self):
        result = self.t.think("Привет!")
        assert result["intent"] in ("deep", "info", "action", "chat")
        assert 0 <= result["confidence"] <= 1
        assert "trace" in result
        assert "conclusion" in result
        assert "context" in result

    def test_think_context_updates(self):
        self.t.think("Привет")
        assert self.t.context["turn"] == 1
        self.t.think("Как дела?")
        assert self.t.context["turn"] == 2
        assert self.t.context["last_intent"] is not None

    def test_think_unknown(self):
        result = self.t.think("абырвалгхз")
        assert result is not None

    def test_reason_deep(self):
        steps = self.t.reason_deep("Привет мир!")
        assert len(steps) >= 2
        stages = [s[0] for s in steps]
        assert "preprocess" in stages

    def test_learn_from_feedback(self):
        old_len = len(self.t._response_memory)
        self.t.learn_from_feedback("привет", "здравствуй", True)
        assert len(self.t._response_memory) == old_len + 1

    def test_learn_fact_and_get(self):
        self.t.learn_fact("user_name", "Анна")
        assert self.t.get_fact("user_name") == "Анна"
        assert self.t.get_fact("nonexistent") is None

    def test_get_thinking_trace(self):
        self.t.think("Привет")
        trace = self.t.get_thinking_trace()
        assert isinstance(trace, str)
        assert len(trace) > 0

    def test_save_and_load_state(self):
        self.t.think("Привет")
        self.t.learn_fact("user_name", "Тест")
        data = self.t.save_state()
        assert "context" in data
        assert data["context"]["turn"] == 1

        t2 = ThinkingEngineV2()
        t2.load_state(data)
        assert t2.context["turn"] == 1

    def test_multiple_turns(self):
        for msg in ["Привет", "Как дела?", "Что нового?"]:
            self.t.think(msg)
        assert self.t.context["turn"] == 3
        assert len(self.t.context["last_topics"]) <= 10

    def test_entity_extraction(self):
        result = self.t.think("Меня зовут Александр")
        assert result is not None
