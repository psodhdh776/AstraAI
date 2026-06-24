"""Tests for FractalProcessor — multidimensional fractal processing engine."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "modules"))

import pytest
from fractal_processor import (
    FractalProcessor, FractalDecomposer, HolographicProjector,
    QuantumSuperposition, ResonanceCollapser, PhaseMemory,
)


class TestFractalDecomposer:
    def test_decompose_basic(self):
        result = FractalDecomposer.decompose("Привет мир!")
        assert "levels" in result
        assert "signature" in result
        assert "depth" in result
        assert result["depth"] > 0

    def test_decompose_levels(self):
        result = FractalDecomposer.decompose("Привет мир! Это тест.")
        levels = result["levels"]
        assert "character" in levels
        assert "word" in levels
        assert "sentence" in levels
        assert levels["sentence"]["count"] == 2

    def test_decompose_empty(self):
        result = FractalDecomposer.decompose("")
        assert "levels" in result
        assert "signature" in result

    def test_decompose_signature_unique(self):
        r1 = FractalDecomposer.decompose("Привет")
        r2 = FractalDecomposer.decompose("Пока")
        assert r1["signature"] != r2["signature"]


class TestHolographicProjector:
    def setup_method(self):
        self.p = HolographicProjector()

    def test_project_basic(self):
        holo = self.p.project("Привет! Как дела?")
        assert "semantic" in holo
        assert "emotional" in holo
        assert "temporal" in holo
        assert "structural" in holo
        assert "associative" in holo
        assert "phase" in holo
        assert "magnitude" in holo
        assert holo["phase"] != 0 or holo["magnitude"] > 0

    def test_project_with_fractal(self):
        profile = FractalDecomposer.decompose("Тестовое сообщение")
        holo = self.p.project("Привет", profile)
        assert holo["magnitude"] > 0

    def test_learn_and_get_associations(self):
        self.p.learn_association("привет", "здравствуй", 0.5)
        assoc = self.p.get_associations("привет")
        assert len(assoc) >= 1
        assert assoc[0][0] == "здравствуй"

    def test_compare(self):
        h1 = self.p.project("Привет")
        h2 = self.p.project("Здравствуй")
        sim = self.p.compare(h1, h2)
        assert 0 <= sim <= 1

    def test_compare_identical(self):
        h = self.p.project("Привет")
        assert self.p.compare(h, h) == 1.0


class TestQuantumSuperposition:
    def setup_method(self):
        self.q = QuantumSuperposition()

    def test_add_and_collapse(self):
        self.q.add_hypothesis("greeting", {"text": "привет"}, 1.0)
        self.q.add_hypothesis("farewell", {"text": "пока"}, 0.5)
        assert len(self.q) == 2
        result = self.q.collapse()
        assert result is not None
        assert result["name"] in ("greeting", "farewell")

    def test_probabilities(self):
        self.q.add_hypothesis("a", {"v": 1}, 2.0)
        self.q.add_hypothesis("b", {"v": 2}, 1.0)
        probs = self.q.get_probabilities()
        assert len(probs) == 2
        total = sum(p["prob"] for p in probs)
        assert abs(total - 1.0) < 0.01

    def test_empty_collapse(self):
        assert self.q.collapse() is None

    def test_interfere(self):
        q1 = QuantumSuperposition()
        q1.add_hypothesis("a", {"v": 1}, 1.0)
        q2 = QuantumSuperposition()
        q2.add_hypothesis("b", {"v": 2}, 1.0)
        q3 = q1.interfere(q2)
        # interfere creates new superposition with combined amplitudes
        assert isinstance(q3, QuantumSuperposition)


class TestResonanceCollapser:
    def setup_method(self):
        self.r = ResonanceCollapser()
        self.p = HolographicProjector()

    def test_resonate_basic(self):
        self.r.add_resonator("greeting", 1.0, ["привет", "здравствуй"])
        holo = self.p.project("Привет мир!")
        name, score = self.r.resonate(holo, "Привет мир!")
        assert name is not None
        assert 0 <= score <= 1

    def test_resonate_no_match(self):
        self.r.add_resonator("greeting", 1.0, ["привет"])
        holo = self.p.project("математика")
        name, score = self.r.resonate(holo, "математика")
        assert score >= 0  # always returns at least 0

    def test_multiple_resonators(self):
        self.r.add_resonator("greeting", 1.0, ["привет"])
        self.r.add_resonator("math", 1.0, ["математика"])
        holo = self.p.project("математика")
        name, _ = self.r.resonate(holo, "математика")
        assert name == "math"


class TestPhaseMemory:
    def setup_method(self):
        self.pm = PhaseMemory()

    def test_record_and_predict(self):
        self.pm.record("A")
        self.pm.record("B")
        self.pm.record("A")
        predictions = self.pm.predict_next(3)
        assert len(predictions) >= 1

    def test_phase_transition(self):
        self.pm.record("A")
        self.pm.record("B")
        assert self.pm.get_phase_transition("A") >= 0
        assert isinstance(self.pm.get_phase_transition("A"), float)

    def test_similarity(self):
        self.pm.record("A")
        self.pm.record("B")
        sim = self.pm.similarity("A", "B")
        assert 0 <= sim <= 1

    def test_entropy(self):
        self.pm.record("A")
        self.pm.record("B")
        ent = self.pm.get_entropy()
        assert ent >= 0

    def test_to_dict(self):
        self.pm.record("A")
        data = self.pm.to_dict()
        assert "states" in data
        assert "transitions" in data
        assert "entropy" in data


class TestFractalProcessor:
    def setup_method(self):
        self.fp = FractalProcessor()

    def test_process_basic(self):
        result = self.fp.process("Привет! Как дела?")
        assert result["engine"] in ("fractal", "command", "question", "chat", "semantic", "creative")
        assert 0 <= result["confidence"] <= 1
        assert "hologram" in result
        assert "quantum_hypotheses" in result
        assert "insights" in result
        assert "signature" in result

    def test_process_different_texts(self):
        r1 = self.fp.process("Привет")
        r2 = self.fp.process("Математика")
        assert r1["signature"] != r2["signature"]

    def test_learn(self):
        self.fp.learn("Привет", "Здравствуй!", True)
        stats = self.fp.get_stats()
        assert "holograms" in stats

    def test_get_insights(self):
        self.fp.process("Первый тест")
        self.fp.process("Второй тест")
        insights = self.fp.get_insights(10)
        assert isinstance(insights, list)

    def test_get_stats(self):
        stats = self.fp.get_stats()
        assert "holograms" in stats
        assert "phase_states" in stats
        assert "phase_entropy" in stats
        assert "resonators" in stats
        assert "insights" in stats
