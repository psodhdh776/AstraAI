import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "modules"))

import pytest


class TestLocalLLM:
    def test_is_available_no_model(self):
        from local_llm import is_available
        assert not is_available()

    def test_generate_no_model(self):
        from local_llm import generate
        result = generate("привет")
        assert result is None

    def test_stop_no_process(self):
        from local_llm import stop
        stop()

    def test_start_no_model(self):
        from local_llm import start
        result = start()
        assert not result

    def test_generate_async_no_model(self):
        from local_llm import generate_async
        called = False
        def cb(text):
            nonlocal called
            called = True
        generate_async("привет", cb)
        import time
        time.sleep(0.1)
        assert not called
