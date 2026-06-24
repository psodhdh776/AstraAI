import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "modules"))

import json
import pytest


class TestMCPHelpers:
    def test_get_time(self):
        from mcp_server import _get_time
        result = _get_time({})
        assert "datetime" in result
        assert "date" in result
        assert "time" in result
        assert "weekday" in result

    def test_get_system_info(self):
        from mcp_server import _get_system_info
        result = _get_system_info({})
        assert "hostname" in result
        assert "platform" in result


class TestMCPHandleTool:
    def test_handle_get_time(self):
        from mcp_server import _handle_tool
        result = _handle_tool("get_time", {})
        assert "result" in result
        assert "datetime" in result["result"]

    def test_handle_get_system_info(self):
        from mcp_server import _handle_tool
        result = _handle_tool("get_system_info", {})
        assert "result" in result
        assert "hostname" in result["result"]

    def test_handle_unknown_tool(self):
        from mcp_server import _handle_tool
        result = _handle_tool("nonexistent_tool", {})
        assert "error" in result

    def test_handle_open_url(self):
        from mcp_server import _handle_tool
        result = _handle_tool("open_url", {"url": "https://example.com"})
        assert "result" in result

    def test_handle_open_url_no_scheme(self):
        from mcp_server import _handle_tool
        result = _handle_tool("open_url", {"url": "example.com"})
        assert "result" in result

    def test_handle_run_command_safe(self):
        from mcp_server import _handle_tool
        result = _handle_tool("run_command", {"command": "echo hello"})
        assert "result" in result
        out = result["result"]["stdout"]
        assert "hello" in out

    def test_handle_run_command_forbidden(self):
        from mcp_server import _handle_tool
        result = _handle_tool("run_command", {"command": "rm -rf /"})
        assert "result" in result
        assert "error" in result["result"]


class TestMCPMessageHandling:
    def test_handle_initialize(self):
        from mcp_server import _handle_message
        msg = {"id": 1, "method": "initialize", "params": {}}
        _handle_message(msg)

    def test_handle_tools_list(self):
        from mcp_server import _handle_message
        msg = {"id": 2, "method": "tools/list", "params": {}}
        _handle_message(msg)

    def test_handle_unknown_method(self):
        from mcp_server import _handle_message
        msg = {"id": 3, "method": "unknown", "params": {}}
        _handle_message(msg)

    def test_handle_notifications(self):
        from mcp_server import _handle_message
        msg = {"id": 4, "method": "notifications/initialized", "params": {}}
        _handle_message(msg)

    def test_handle_tools_call(self):
        from mcp_server import _handle_message
        msg = {
            "id": 5,
            "method": "tools/call",
            "params": {"name": "get_time", "arguments": {}},
        }
        _handle_message(msg)

    def test_handle_invalid_json(self):
        from mcp_server import _handle_message
        msg = {"id": 6, "method": "tools/call", "params": {}}
        _handle_message(msg)
