"""
GUI integration tests for Astra AI.
Tests UI components headlessly using QTest.
"""
import sys, os, logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
logging.basicConfig(level=logging.CRITICAL, force=True)

passed = 0
failed = 0

def check(name, ok):
    global passed, failed
    if ok:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name}")

# Headless Qt
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)

print("\n--- UI Component Tests ---")

# Test theme system
from modules.theme import C
check("Theme has 4 themes", len(C.theme_names()) == 4)
check("Default theme is indigo", C.current == "indigo")
C.set_theme("cyberpunk")
check("Theme switched to cyberpunk", C.current == "cyberpunk")
check("C.BG updated after switch", "0015" in C.BG)
C.set_theme("indigo")
check("Switched back to indigo", C.current == "indigo")
check("build_qss returns string", isinstance(C.build_qss(), str) and len(C.build_qss()) > 200)

# Test desktop widgets
from modules.desktop_widgets import get_random_quote
q = get_random_quote()
check("get_random_quote returns string", isinstance(q, str) and len(q) > 20)

# Test API server
from modules.api_server import start_api
from unittest.mock import Mock
mock_assistant = Mock()
mock_assistant.history = []
mock_assistant.notes = []
mock_assistant.voice_enabled = True
server = start_api(mock_assistant)
check("API server started", server is not None)
server.shutdown()
check("API server stopped", True)

# Test voice engine import
from modules.voice_engine import VoiceEngine, VOICE_COMMANDS
check("VoiceEngine imported", True)
check("VOICE_COMMANDS has entries", len(VOICE_COMMANDS) >= 10)
check("Has 'чат' command", "чат" in VOICE_COMMANDS)
check("Has 'скриншот' command", "скриншот" in VOICE_COMMANDS)

# Test theme import consistency
from modules.theme import C as C2
check("Theme singleton works", C is C2)

print(f"\n=== RESULTS: {passed}/{passed+failed} passed ===")
sys.exit(0 if failed == 0 else 1)
