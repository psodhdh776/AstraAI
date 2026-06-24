"""
Auto-updater — checks GitHub releases for new versions.
"""
import json
import logging
import os
import ssl
import subprocess
import sys
import tempfile
import threading
import urllib.request
from pathlib import Path

logger = logging.getLogger("Astra.Updater")

CURRENT_VERSION = "2.2.0"
REPO = "psodhdh776/AstraAI"
API_URL = f"https://api.github.com/repos/{REPO}/releases/latest"

def _get_token():
    try:
        from pathlib import Path
        cfg = Path(__file__).parent.parent / "data" / "github_config.json"
        if cfg.exists():
            import json
            return json.loads(cfg.read_text(encoding="utf-8")).get("github_token", "")
    except Exception:
        pass
    return ""

# Graceful 404 → no update available


def check_version():
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        headers = {"User-Agent": "AstraAI"}
        token = _get_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(API_URL, headers=headers)
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            data = json.loads(resp.read())
        latest = data.get("tag_name", "").lstrip("v")
        if not latest:
            return {}
        is_newer = _compare_versions(latest, CURRENT_VERSION) > 0
        return {
            "latest": latest,
            "current": CURRENT_VERSION,
            "has_update": is_newer,
            "url": data.get("html_url", ""),
            "body": data.get("body", ""),
        }
    except Exception as e:
        logger.debug("Check update: %s", e)
        return {"error": str(e)}


def _compare_versions(v1, v2):
    import re
    p1 = [int(x) for x in re.split(r"[.]", v1)]
    p2 = [int(x) for x in re.split(r"[.]", v2)]
    for a, b in zip(p1, p2):
        if a != b:
            return a - b
    return len(p1) - len(p2)


def check_async(callback):
    def run():
        result = check_version()
        callback(result)
    threading.Thread(target=run, daemon=True).start()
