import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "modules"))

import json
import pytest
from unittest.mock import MagicMock
from http.server import HTTPServer, BaseHTTPRequestHandler


@pytest.fixture
def handler():
    from api_server import _Handler
    h = _Handler.__new__(_Handler)
    h.assistant = MagicMock()
    h.assistant.history = []
    h.assistant.notes = []
    h.assistant.voice_enabled = True
    h.assistant.process = MagicMock(return_value="hello from test")
    h.assistant.add_history = MagicMock()
    h.assistant.memory = MagicMock()
    h.assistant.memory.get_memory_stats = MagicMock(return_value={"total": 10})
    h.assistant.memory.get_user_summary = MagicMock(return_value={"name": "Test"})
    h.assistant.memory.get_session_summary = MagicMock(return_value={"turns": 5})
    h.send_response = MagicMock()
    h.send_header = MagicMock()
    h.end_headers = MagicMock()
    h.wfile = MagicMock()
    return h


class TestApiServer:
    def test_send(self, handler):
        handler._send({"status": "ok"})
        args, _ = handler.wfile.write.call_args
        data = json.loads(args[0])
        assert data["status"] == "ok"

    def test_status_endpoint(self, handler):
        handler.path = "/status"
        handler.do_GET()
        args, _ = handler.wfile.write.call_args
        data = json.loads(args[0])
        assert data["status"] == "ok"

    def test_history_endpoint(self, handler):
        handler.path = "/history"
        handler.do_GET()
        handler.wfile.write.assert_called_once()

    def test_memory_endpoint(self, handler):
        handler.path = "/memory"
        handler.do_GET()
        args, _ = handler.wfile.write.call_args
        data = json.loads(args[0])
        assert "total" in data

    def test_memory_user_endpoint(self, handler):
        handler.path = "/memory/user"
        handler.do_GET()
        args, _ = handler.wfile.write.call_args
        data = json.loads(args[0])
        assert "summary" in data
        assert "session" in data

    def test_not_found(self, handler):
        handler.path = "/nonexistent"
        handler.do_GET()
        args, _ = handler.wfile.write.call_args
        data = json.loads(args[0])
        assert data["error"] == "not found"

    def test_chat_post(self, handler):
        handler.path = "/chat"
        handler.headers = {"Content-Length": "20"}
        body = json.dumps({"text": "hi"}).encode()
        handler.rfile = MagicMock()
        handler.rfile.read = MagicMock(return_value=body)
        handler.do_POST()
        args, _ = handler.wfile.write.call_args
        data = json.loads(args[0])
        assert data["response"] == "hello from test"

    def test_chat_post_empty(self, handler):
        handler.path = "/chat"
        handler.headers = {"Content-Length": "2"}
        handler.rfile = MagicMock()
        handler.rfile.read = MagicMock(return_value=b"{}")
        handler.do_POST()
        args, _ = handler.wfile.write.call_args
        data = json.loads(args[0])
        assert data["error"] == "empty text"

    def test_start_api(self):
        from api_server import start_api
        asst = MagicMock()
        server = start_api(asst)
        assert isinstance(server, HTTPServer)
        server.shutdown()

    def test_options(self, handler):
        handler.do_OPTIONS()
        handler.send_response.assert_called_with(200)
