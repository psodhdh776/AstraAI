import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest


class TestAiEngineReexports:
    def test_import_submodules(self):
        from modules.ai_engine import (
            StaticArena, ScratchpadArena, TensorView,
            QuantizedOps, Int8Kernel, Int8Graph,
            AiEngine, engine, engine_threaded, MemoryArena,
            GenerativeOps, LlmSampler, ExtremeSampler,
            KVCache, PagedKVCache, RUSSIAN_CHARS, GenerativeEngine,
            BigramTrainer, WordLevelEngine, TrigramEngine, CorpusWordEngine,
            RequestStatus, Sequence, ContinuousBatchScheduler,
        )
        assert StaticArena is not None
        assert AiEngine is not None
        assert engine is not None

    def test_all_defined(self):
        from modules.ai_engine import __all__
        assert "StaticArena" in __all__
        assert "AiEngine" in __all__
        assert "engine" in __all__
        assert "LlmSampler" in __all__
