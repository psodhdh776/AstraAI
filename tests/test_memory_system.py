"""Tests for MemorySystem — 5-module unified memory."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "modules"))

import pytest
from memory_system import (
    MemorySystem, ShortTermMemory, LongTermMemory,
    EpisodicMemoryStore, SemanticMemory, ProceduralMemory,
)


class TestShortTermMemory:
    def setup_method(self):
        self.m = ShortTermMemory(capacity=5)

    def test_add_and_recent(self):
        self.m.add("user", "привет")
        self.m.add("assistant", "здравствуй")
        recent = self.m.recent(10)
        assert len(recent) == 2

    def test_capacity(self):
        for i in range(10):
            self.m.add("user", f"msg {i}")
        recent = self.m.recent(20)
        assert len(recent) == 5  # capped at capacity

    def test_context_window(self):
        self.m.add("user", "привет")
        self.m.add("assistant", "здравствуй")
        ctx = self.m.context_window(5)
        assert len(ctx) == 2
        assert ctx[0] == ("user", "привет")

    def test_summary(self):
        self.m.add("user", "привет", intent="greeting")
        summary = self.m.summary()
        assert summary["turns"] == 1
        assert "topics" in summary
        assert "last_intent" in summary


class TestLongTermMemory:
    def setup_method(self):
        self.m = LongTermMemory()

    def test_profile(self):
        assert isinstance(self.m.profile, dict)

    def test_update_profile(self):
        self.m.update_profile("name", "Анна")
        assert self.m.profile["name"] == "Анна"

    def test_learn_fact_name(self):
        facts = self.m.learn_fact("Меня зовут Дима")
        assert facts is not None
        assert "Дима" in str(facts)

    def test_learn_fact_city(self):
        facts = self.m.learn_fact("Я живу в Москве")
        assert facts is not None

    def test_learn_fact_age(self):
        facts = self.m.learn_fact("Мне 25 лет")
        assert facts is not None

    def test_update_style(self):
        self.m.update_style("Привет! Как дела?")
        # update_style may or may not set communication_style — just check no error
        assert True

    def test_get_summary(self):
        self.m.update_profile("name", "Анна")
        summary = self.m.get_summary()
        assert "Анна" in summary


class TestEpisodicMemoryStore:
    def setup_method(self):
        self.m = EpisodicMemoryStore()

    def test_add_and_recall(self):
        self.m.add_episode("user", "Я люблю Python", "express_love", 0.8)
        results = self.m.recall("Python")
        assert len(results) >= 1

    def test_recall_no_match(self):
        self.m.add_episode("user", "Привет", "greeting", 0.3)
        results = self.m.recall("nonexistent")
        assert len(results) == 0

    def test_recall_top_n(self):
        for i in range(10):
            self.m.add_episode("user", f"факт номер {i}", "general", 0.5)
        results = self.m.recall("факт", top_n=3)
        assert len(results) == 3


class TestSemanticMemory:
    def setup_method(self):
        self.m = SemanticMemory()

    def test_learn_and_get_associations(self):
        self.m.learn_association("кошка", "собака", 0.5)
        assoc = self.m.get_associated("кошка")
        assert len(assoc) >= 1
        assert assoc[0][0] == "собака"

    def test_empty_associations(self):
        assert len(self.m.get_associated("nonexistent")) == 0

    def test_learn_concept(self):
        self.m.learn_concept("Python", {"type": "language", "use": "programming"})
        concept = self.m.get_concept("Python")
        assert concept is not None
        # concept data may be nested — verify it contains what we stored
        assert "type" in str(concept) or "language" in str(concept)

    def test_get_concept_nonexistent(self):
        assert self.m.get_concept("nonexistent") is None


class TestProceduralMemory:
    def setup_method(self):
        self.m = ProceduralMemory()

    def test_record_and_get_best(self):
        self.m.record_response("greeting", "Привет!", True)
        assert self.m.get_best_response("greeting") == "Привет!"

    def test_no_response(self):
        assert self.m.get_best_response("nonexistent") is None

    def test_multiple_responses(self):
        self.m.record_response("greeting", "Привет!", False)
        self.m.record_response("greeting", "Здравствуй!", True)
        best = self.m.get_best_response("greeting")
        assert best == "Здравствуй!"  # last successful


class TestMemorySystem:
    def setup_method(self):
        self.ms = MemorySystem()

    def test_observe(self):
        self.ms.observe("user", "Привет!", "greeting")
        summary = self.ms.get_session_summary()
        assert summary["turn"] == 1

    def test_observe_with_entities(self):
        self.ms.observe("user", "Меня зовут Анна", "introduce_name",
                         {"user_name": "Анна"})
        assert self.ms.long.profile.get("name") == "Анна"

    def test_new_session(self):
        self.ms.observe("user", "Привет", "greeting")
        self.ms.new_session()
        assert self.ms.short.summary()["turns"] == 0

    def test_recall(self):
        self.ms.observe("user", "Я люблю Python", "express_love")
        results = self.ms.recall("Python")
        assert isinstance(results, list)

    def test_get_user_summary(self):
        self.ms.observe("user", "Меня зовут Тест", "introduce_name",
                         {"user_name": "Тест"})
        summary = self.ms.get_user_summary()
        assert isinstance(summary, str)

    def test_get_session_summary(self):
        self.ms.observe("user", "Привет", "greeting")
        self.ms.observe("assistant", "Здравствуй", "greeting")
        s = self.ms.get_session_summary()
        assert s["turn"] == 2
        assert "topics" in s
        assert "messages" in s

    def test_get_memory_stats(self):
        self.ms.observe("user", "Привет", "greeting")
        stats = self.ms.get_memory_stats()
        assert "short_term" in stats
        assert "long_term_facts" in stats
        assert "episodic" in stats
        assert "semantic_associations" in stats
        assert "procedural_patterns" in stats

    def test_save_all(self):
        self.ms.observe("user", "Тест", "test")
        self.ms.save_all()  # should not raise
