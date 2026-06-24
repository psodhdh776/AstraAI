import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "modules"))

import pytest
from unittest.mock import MagicMock


class TestPipelineIntegration:
    """Verify that all pipeline stages can be created and chained together."""

    @pytest.fixture
    def pipeline_components(self):
        from thinking_engine import ThinkingEngineV2
        from fractal_processor import FractalProcessor
        from dialogue_engine import DialogueEngine

        thinker = ThinkingEngineV2()
        fractal = FractalProcessor()
        dialogue = DialogueEngine()
        return thinker, fractal, dialogue

    def test_thinking_engine_chain(self, pipeline_components):
        thinker, _, _ = pipeline_components
        thought = thinker.think("привет")
        assert thought is not None

    def test_fractal_processor_chain(self, pipeline_components):
        _, fractal, _ = pipeline_components
        result = fractal.process("привет как дела")
        assert result is not None
        assert "engine" in result
        assert result["engine"] in ("fractal", "semantic", "command", "question", "chat", "creative")

    def test_fractal_learn_chain(self, pipeline_components):
        _, fractal, _ = pipeline_components
        fractal.learn("привет", "и тебе привет", True)
        fractal.learn("как дела", "нормально", True)
        insights = fractal.get_insights()
        assert isinstance(insights, list)
        stats = fractal.get_stats()
        assert "holograms" in stats or "total_learned" in stats or "insights" in stats

    def test_dialogue_chain(self, pipeline_components):
        _, _, dialogue = pipeline_components
        r = dialogue.respond("привет")
        assert r is not None
        assert len(r) > 0

    def test_thinking_then_fractal(self, pipeline_components):
        thinker, fractal, _ = pipeline_components
        text = "расскажи про python"
        thought = thinker.think(text)
        result = fractal.process(text)
        assert thought is not None
        assert result is not None

    def test_full_pipeline_no_core(self):
        from thinking_engine import ThinkingEngineV2
        from fractal_processor import FractalProcessor
        from dialogue_engine import DialogueEngine

        mock_asst = MagicMock()
        mock_asst.thinker = ThinkingEngineV2()
        mock_asst.fractal = FractalProcessor()
        mock_asst.dialogue = DialogueEngine()
        mock_asst.core = None
        mock_asst.plugins = []
        mock_asst.history = []
        mock_asst.voice_enabled = False
        mock_asst.add_history = MagicMock()
        mock_asst._speak = MagicMock()

        text = "привет"
        tl = text.lower()

        thought = mock_asst.thinker.think(text)
        assert thought is not None

        fractal_result = mock_asst.fractal.process(text)
        assert fractal_result is not None

        resp = mock_asst.dialogue.respond(text)
        assert resp is not None
        assert len(resp) > 0

    def test_thinking_learn_then_recall(self, pipeline_components):
        thinker, _, _ = pipeline_components
        thinker.think("меня зовут Иван")
        thinker.learn_fact("имя", "Иван")
        fact = thinker.get_fact("имя")
        assert fact == "Иван"

    def test_cross_component_data_flow(self, pipeline_components):
        thinker, fractal, dialogue = pipeline_components
        text = "привет! меня зовут Анна"
        thought = thinker.think(text)
        fractal_result = fractal.process(text)
        dialogue.respond(text)
        assert thought is not None
        assert fractal_result is not None
