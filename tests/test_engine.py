import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest


class TestAiEngine:
    def setup_method(self):
        from modules.engine import AiEngine
        self.engine = AiEngine()

    def test_default_build(self):
        self.engine.build()
        assert self.engine._compiled

    def test_build_custom_layers(self):
        self.engine.build(layer_sizes=[4, 16, 3])
        assert self.engine._compiled

    def test_predict_default(self):
        self.engine.build()
        result = self.engine.predict([0.5, -0.3, 0.8, 0.1])
        assert len(result) == 3
        assert all(isinstance(v, float) for v in result)

    def test_predict_different_input(self):
        self.engine.build()
        r1 = self.engine.predict([1.0, 0.0, -1.0, 0.5])
        r2 = self.engine.predict([-1.0, 0.0, 1.0, -0.5])
        assert r1 != r2

    def test_get_logits(self):
        self.engine.build()
        logits = self.engine.get_logits([0.2, 0.1, -0.3, 0.4])
        assert len(logits) >= 3

    def test_engine_singleton(self):
        from modules.engine import engine, engine_threaded
        assert engine is not None
        assert engine_threaded is not None
        assert engine is not engine_threaded

    def test_scratch_arena_property(self):
        self.engine.build()
        assert self.engine.scratch_arena is not None

    def test_static_arena_property(self):
        self.engine.build()
        assert self.engine.static_arena is not None

    def test_predict_auto_build(self):
        from modules.engine import AiEngine
        e = AiEngine()
        result = e.predict([0.1, 0.2, 0.3, 0.4])
        assert len(result) == 3
