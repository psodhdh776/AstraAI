"""
Simple REST API plugin for Astra AI.
Runs an HTTP server on localhost:8741 for remote control.
"""

import json
import logging
import threading
import os
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

WEB_DIR = Path(__file__).parent / "web_ui"

logger = logging.getLogger("Astra.API")

API_PORT = 8741


class _Handler(BaseHTTPRequestHandler):
    assistant = None

    def log_message(self, fmt, *args):
        logger.debug("API: %s", fmt % args)

    def _send(self, data, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def do_GET(self):
        a = self.assistant
        if not a:
            self._send({"error": "no assistant"}, 500)
            return
        if self.path == "/" or self.path == "/web":
            try:
                html = (WEB_DIR / "index.html").read_text("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(html.encode("utf-8"))
                return
            except Exception:
                self._send({"error": "web ui not found"}, 404)
                return
        if self.path == "/landing":
            try:
                html = (WEB_DIR / "landing.html").read_text("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(html.encode("utf-8"))
                return
            except Exception:
                self._send({"error": "landing page not found"}, 404)
                return
        if self.path == "/status":
            self._send({
                "status": "ok",
                "history": len(a.history),
                "notes": len(getattr(a, "notes", [])),
                "voice_enabled": a.voice_enabled,
            })
        elif self.path == "/history":
            self._send(a.history[-50:])
        elif self.path == "/notes":
            self._send(getattr(a, "notes", []))
        elif self.path == "/theme":
            from modules.theme import C
            self._send({"theme": C.current, "themes": C.theme_names()})
        elif self.path == "/plugins/available":
            from modules.plugin_market import get_available_plugins
            self._send(get_available_plugins())
        elif self.path == "/plugins/installed":
            from modules.plugin_market import get_installed_plugins
            self._send(get_installed_plugins())
        elif self.path == "/profiles":
            from modules.voice_profiles import get_profiles
            self._send(get_profiles())
        elif self.path == "/backups":
            from modules.cloud_sync import list_backups
            self._send(list_backups())
        elif self.path == "/memory":
            if hasattr(a, "memory"):
                self._send(a.memory.get_memory_stats())
            else:
                self._send({"error": "memory not available"}, 404)
        elif self.path == "/memory/user":
            if hasattr(a, "memory"):
                self._send({
                    "summary": a.memory.get_user_summary(),
                    "session": a.memory.get_session_summary(),
                    "stats": a.memory.get_memory_stats(),
                })
            else:
                self._send({"error": "memory not available"}, 404)
        elif self.path == "/github/status":
            from modules.auto_update import CURRENT_VERSION as ver
            from pathlib import Path
            git_dir = Path(__file__).parent.parent / ".git"
            self._send({
                "version": ver,
                "repo": "psodhdh776/AstraAI",
                "git_initialized": git_dir.exists(),
                "push_script": Path(__file__).parent.parent.joinpath("push_to_github.ps1").exists(),
                "release_script": Path(__file__).parent.parent.joinpath("create_release.py").exists(),
                "endpoints": {
                    "push": "POST /github/push  (body: {\"message\": \"...\"})",
                    "release": "POST /github/release  (body: {\"tag\": \"v2.2.0\", \"title\": \"...\", \"body\": \"...\"})",
                    "check_update": "GET /github/check-update",
                    "update": "POST /github/update",
                },
            })
        elif self.path == "/github/check-update":
            from modules.auto_update import check_version
            self._send(check_version())
        else:
            self._send({"error": "not found", "paths": ["/status", "/history", "/notes", "/theme", "/plugins/available", "/plugins/installed", "/profiles", "/backups", "/memory", "/memory/user", "/web", "/landing", "/github/status", "/github/check-update", "/github/push", "/github/release", "/github/update"]}, 404)

    def do_POST(self):
        a = self.assistant
        if not a:
            self._send({"error": "no assistant"}, 500)
            return
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(body)
        except Exception:
            data = {}

        if self.path == "/chat":
            text = data.get("text", "")
            if text:
                result = a.process(text)
                self._send({"response": result})
            else:
                self._send({"error": "empty text"}, 400)
        elif self.path == "/note":
            text = data.get("text", "")
            if text and hasattr(a, "_h_add_note"):
                a._h_add_note(text)
                self._send({"status": "ok", "note": text})
            else:
                self._send({"error": "empty text"}, 400)
        elif self.path == "/theme":
            name = data.get("theme", "")
            from modules.theme import C
            if name in C.theme_names():
                C.set_theme(name)
                self._send({"status": "ok", "theme": name})
            else:
                self._send({"error": f"unknown theme: {name}", "themes": C.theme_names()}, 400)
        elif self.path == "/voice":
            enabled = data.get("enabled", not a.voice_enabled)
            a.voice_enabled = bool(enabled)
            self._send({"status": "ok", "voice_enabled": a.voice_enabled})
        elif self.path == "/screenshot":
            if hasattr(a, "_do_screenshot"):
                result = a._do_screenshot()
                self._send({"status": "ok", "result": result})
            else:
                self._send({"error": "screenshot not available"}, 500)
        elif self.path == "/plugins/install":
            plugin_id = data.get("plugin", "")
            from modules.plugin_market import install_plugin
            result = install_plugin(plugin_id)
            self._send(result)
        elif self.path == "/plugins/uninstall":
            plugin_id = data.get("plugin", "")
            from modules.plugin_market import uninstall_plugin
            result = uninstall_plugin(plugin_id)
            self._send(result)
        elif self.path == "/profile":
            from modules.theme import C
            self._send({"theme": C.current, "voice_enabled": a.voice_enabled})
        elif self.path == "/backup":
            from modules.cloud_sync import local_backup
            result = local_backup(a)
            self._send({"status": "ok", "path": result})
        elif self.path == "/profiles/save":
            name = data.get("name", "default")
            from modules.voice_profiles import save_profile
            result = save_profile(name, data.get("settings", {}))
            self._send(result)
        elif self.path == "/profiles/apply":
            name = data.get("name", "default")
            from modules.voice_profiles import apply_profile
            result = apply_profile(a, name)
            self._send({"status": "ok", "profile": result})
        elif self.path == "/backup/restore":
            path = data.get("path", "")
            from modules.cloud_sync import local_restore
            result = local_restore(path)
            self._send(result if isinstance(result, dict) else {"status": "ok", "data": result})
        elif self.path == "/telegram/set":
            token = data.get("token", "")
            from modules.telegram_bot import set_token
            set_token(token)
            self._send({"status": "ok"})
        elif self.path == "/telegram/start":
            from modules.telegram_bot import start_bot
            ok = start_bot(a)
            self._send({"status": "ok" if ok else "failed"})
        elif self.path == "/github/push":
            import subprocess, sys
            script = Path(__file__).parent.parent / "push_to_github.ps1"
            if not script.exists():
                self._send({"error": "push_to_github.ps1 not found"}, 404)
                return
            msg = data.get("message", f"auto-update from Astra")
            try:
                result = subprocess.run(
                    ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(script),
                     "-CommitMessage", msg],
                    capture_output=True, text=True, timeout=120
                )
                self._send({
                    "status": "ok" if result.returncode == 0 else "error",
                    "returncode": result.returncode,
                    "stdout": result.stdout[-500:],
                    "stderr": result.stderr[-500:],
                })
            except subprocess.TimeoutExpired:
                self._send({"error": "push timed out after 120s"}, 504)
            except Exception as e:
                self._send({"error": str(e)}, 500)
        elif self.path == "/github/release":
            import urllib.request, urllib.error, ssl
            token = ""
            cfg = Path(__file__).parent.parent / "data" / "github_config.json"
            if cfg.exists():
                try:
                    token = json.loads(cfg.read_text("utf-8")).get("github_token", "")
                except Exception:
                    pass
            if not token:
                self._send({"error": "token not found in data/github_config.json"}, 500)
                return
            tag = data.get("tag", "")
            if not tag:
                self._send({"error": "tag is required"}, 400)
                return
            payload = {
                "tag_name": tag,
                "name": data.get("title", tag),
                "body": data.get("body", ""),
                "draft": data.get("draft", False),
                "prerelease": data.get("prerelease", False),
            }
            api_url = "https://api.github.com/repos/psodhdh776/AstraAI/releases"
            body_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(api_url, data=body_bytes, method="POST")
            req.add_header("Authorization", f"Bearer {token}")
            req.add_header("User-Agent", "AstraAI")
            req.add_header("Content-Type", "application/json")
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            try:
                with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
                    result = json.loads(resp.read())
                self._send({"status": "ok", "html_url": result.get("html_url", ""), "tag": tag})
            except urllib.error.HTTPError as e:
                detail = e.read().decode()
                self._send({"error": f"GitHub API error {e.code}: {detail}"}, 502)
            except Exception as e:
                self._send({"error": str(e)}, 500)
        elif self.path == "/github/update":
            from modules.auto_update import download_update
            try:
                ok = download_update()
                self._send({"status": "ok" if ok else "error", "updated": ok})
            except Exception as e:
                self._send({"error": str(e)}, 500)
        else:
            self._send({"error": "not found"}, 404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


def start_api(assistant):
    _Handler.assistant = assistant
    server = HTTPServer(("127.0.0.1", API_PORT), _Handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    logger.info("REST API running on http://127.0.0.1:%d", API_PORT)
    return server
