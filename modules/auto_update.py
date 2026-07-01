"""
Auto-updater — checks GitHub releases for new versions, downloads updates.
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
import zipfile
from pathlib import Path

logger = logging.getLogger("Astra.Updater")

CURRENT_VERSION = "2.2.0"
REPO = "psodhdh776/AstraAI"
API_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
ZIP_URL = f"https://github.com/{REPO}/archive/refs/heads/main.zip"

def _get_token():
    try:
        cfg = Path(__file__).parent.parent / "data" / "github_config.json"
        if cfg.exists():
            return json.loads(cfg.read_text(encoding="utf-8")).get("github_token", "")
    except Exception:
        pass
    return ""

def _headers():
    h = {"User-Agent": "AstraAI"}
    token = _get_token()
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h

def _ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

def check_version():
    try:
        req = urllib.request.Request(API_URL, headers=_headers())
        with urllib.request.urlopen(req, timeout=10, context=_ctx()) as resp:
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
        callback(check_version())
    threading.Thread(target=run, daemon=True).start()


def download_update(progress_callback=None):
    """
    Download latest source from GitHub main branch and extract over installation.
    Returns True on success.
    """
    try:
        import io, shutil
        req = urllib.request.Request(ZIP_URL, headers=_headers())
        if progress_callback:
            progress_callback("downloading")
        with urllib.request.urlopen(req, timeout=60, context=_ctx()) as resp:
            data = resp.read()
        if progress_callback:
            progress_callback("extracting")
        root = Path(__file__).parent.parent
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            # First entry is the top-level folder, strip it
            members = [m for m in z.namelist() if "/" in m]
            prefix = members[0].split("/")[0] + "/"
            for m in members:
                rel = m[len(prefix):]
                if not rel:
                    continue
                target = root / rel
                if m.endswith("/"):
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with z.open(m) as src, open(target, "wb") as dst:
                        shutil.copyfileobj(src, dst)
        if progress_callback:
            progress_callback("done")
        logger.info("Update downloaded and extracted to %s", root)
        return True
    except Exception as e:
        logger.error("Download update failed: %s", e)
        if progress_callback:
            progress_callback(f"error: {e}")
        return False


def update_async(on_done, progress_callback=None):
    def run():
        result = download_update(progress_callback)
        on_done(result)
    threading.Thread(target=run, daemon=True).start()
