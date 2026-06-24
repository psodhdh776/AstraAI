"""MCP (Model Context Protocol) server for system tools.

Provides AI models with safe, structured access to
system information and actions via the standard MCP protocol.
"""

import json
import sys
import os
import datetime
import platform
import subprocess
import webbrowser
import socket
import urllib.request


# ── Tool definitions ──

TOOLS = [
    {
        "name": "get_system_info",
        "description": "Get CPU, RAM, disk, battery, and uptime information",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_processes",
        "description": "Get top processes by CPU usage",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of processes to return (default 10)",
                }
            },
        },
    },
    {
        "name": "get_time",
        "description": "Get current date and time",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "open_url",
        "description": "Open a URL in the default browser",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to open"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "run_command",
        "description": "Run a shell command (read-only commands only)",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Command to run"},
            },
            "required": ["command"],
        },
    },
    {
        "name": "get_external_ip",
        "description": "Get the external IP address",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "screencapture",
        "description": "Capture a screenshot and return the file path",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]


# ── Tool handlers ──

def _handle_tool(name, arguments):
    handlers = {
        "get_system_info": _get_system_info,
        "get_processes": _get_processes,
        "get_time": _get_time,
        "open_url": _open_url,
        "run_command": _run_command,
        "get_external_ip": _get_external_ip,
        "screencapture": _screencapture,
    }
    handler = handlers.get(name)
    if not handler:
        return {"error": f"Unknown tool: {name}"}
    try:
        result = handler(arguments or {})
        return {"result": result}
    except Exception as e:
        return {"error": str(e)}


def _get_system_info(args):
    info = {"hostname": platform.node(), "platform": platform.platform()}
    try:
        import psutil
        info["cpu"] = f"{psutil.cpu_percent(interval=0)}%"
        mem = psutil.virtual_memory()
        info["memory"] = f"{mem.percent}% ({mem.used//1024**3}/{mem.total//1024**3} GB)"
        disk = psutil.disk_usage("/")
        info["disk"] = f"{disk.percent}% ({disk.used//1024**3}/{disk.total//1024**3} GB)"
        bat = psutil.sensors_battery()
        if bat:
            info["battery"] = f"{bat.percent}% {'🔌' if bat.power_plugged else '🔋'}"
        boot = datetime.datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.datetime.now() - boot
        info["uptime"] = f"{uptime.days}d {uptime.seconds//3600}h {(uptime.seconds%3600)//60}m"
    except Exception as e:
        info["error"] = str(e)
    return info


def _get_processes(args):
    limit = args.get("limit", 10)
    try:
        import psutil
        procs = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                procs.append(p.info)
            except Exception:
                pass
        procs.sort(key=lambda x: (x.get("cpu_percent") or 0), reverse=True)
        return procs[:limit]
    except Exception as e:
        return {"error": str(e)}


def _get_time(args):
    now = datetime.datetime.now()
    return {
        "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
        "date": now.strftime("%d.%m.%Y"),
        "time": now.strftime("%H:%M"),
        "weekday": now.strftime("%A"),
    }


def _open_url(args):
    url = args["url"]
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    webbrowser.open(url)
    return {"opened": url}


def _run_command(args):
    command = args["command"]
    forbidden = ["rm", "del", "format", "mkfs", ">", "|", ";", "&&", "||"]
    for f in forbidden:
        if f in command:
            return {"error": f"Command contains forbidden pattern: {f}"}
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=30
        )
        return {
            "stdout": result.stdout[:2000],
            "stderr": result.stderr[:500],
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"error": "Command timed out"}
    except Exception as e:
        return {"error": str(e)}


def _get_external_ip(args):
    try:
        ip = urllib.request.urlopen("https://api.ipify.org", timeout=5).read().decode()
        return {"ip": ip}
    except Exception as e:
        return {"error": str(e)}


def _screencapture(args):
    try:
        import pyautogui
        import sys
        from pathlib import Path
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        if getattr(sys, 'frozen', False) or hasattr(sys, '_MEIPASS'):
            import os
            _appdata = Path(os.environ.get('APPDATA', str(Path.home() / '.astra'))) / 'AstraAI'
            data_dir = _appdata / 'data'
        else:
            data_dir = Path(__file__).resolve().parent.parent / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        path = str(data_dir / f"screenshot_{ts}.png")
        pyautogui.screenshot().save(path)
        return {"path": path}
    except Exception as e:
        return {"error": str(e)}


# ── JSON-RPC message handling ──

def _respond(request_id, result=None, error=None):
    response = {"jsonrpc": "2.0", "id": request_id}
    if error:
        response["error"] = {"code": -32000, "message": str(error)}
    else:
        response["result"] = result
    sys.stdout.write(json.dumps(response) + "\n")
    sys.stdout.flush()


def _handle_message(msg):
    msg_id = msg.get("id")
    method = msg.get("method", "")
    params = msg.get("params", {})

    if method == "initialize":
        _respond(msg_id, {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "absolute-assistant-mcp", "version": "1.0.0"},
        })
    elif method == "tools/list":
        _respond(msg_id, TOOLS)
    elif method == "tools/call":
        name = params.get("name", "")
        args = params.get("arguments", {})
        result = _handle_tool(name, args)
        _respond(msg_id, result)
    elif method == "notifications/initialized":
        pass  # No response needed
    else:
        _respond(msg_id, None, f"Unknown method: {method}")


def serve_stdio():
    """Run the MCP server over stdio transport."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
            _handle_message(msg)
        except json.JSONDecodeError as e:
            _respond(None, None, f"Invalid JSON: {e}")
        except Exception as e:
            _respond(msg.get("id") if isinstance(msg, dict) else None, None, str(e))


if __name__ == "__main__":
    serve_stdio()
