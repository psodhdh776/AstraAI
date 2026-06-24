"""
Local LLM integration — llama.cpp backend for text generation.
Falls back to existing bigram engine if no model file found.
"""
import json
import logging
import os
import subprocess
import threading
from pathlib import Path

logger = logging.getLogger("Astra.LLM")

LLM_DIR = Path(__file__).parent.parent / "models" / "llm"
LLAMA_CPP = LLM_DIR / "llama-server.exe"
MODEL_PATH = None

# Find first available model
for ext in (".gguf", ".bin", ".ggml"):
    for f in LLM_DIR.glob(f"*{ext}"):
        MODEL_PATH = f
        break
    if MODEL_PATH:
        break

_llm_process = None
_llm_port = 8080


def is_available():
    return MODEL_PATH is not None and MODEL_PATH.exists()


def start():
    global _llm_process
    if _llm_process or not is_available():
        return _llm_process is not None
    try:
        cmd = [
            str(LLAMA_CPP),
            "-m", str(MODEL_PATH),
            "--host", "127.0.0.1",
            "--port", str(_llm_port),
            "-ngl", "99",
            "-c", "2048",
        ]
        if not LLAMA_CPP.exists():
            logger.info("llama-server not found, using built-in engine")
            return False
        _llm_process = subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        import time
        time.sleep(2)
        logger.info("LLM server started on port %d", _llm_port)
        return True
    except Exception as e:
        logger.warning("LLM start: %s", e)
        return False


def stop():
    global _llm_process
    if _llm_process:
        _llm_process.terminate()
        _llm_process = None


def generate(prompt, max_tokens=256, temperature=0.7):
    if not is_available():
        return None
    try:
        import urllib.request
        import json as j
        data = j.dumps({
            "prompt": prompt,
            "n_predict": max_tokens,
            "temperature": temperature,
            "stop": ["\n\n", "User:", "---"],
        }).encode()
        req = urllib.request.Request(
            f"http://127.0.0.1:{_llm_port}/completion",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=30)
        result = j.loads(resp.read())
        return result.get("content", "")
    except Exception as e:
        logger.debug("LLM generate: %s", e)
        return None


def generate_async(prompt, callback, max_tokens=256):
    def run():
        result = generate(prompt, max_tokens)
        if result:
            callback(result)
    threading.Thread(target=run, daemon=True).start()
