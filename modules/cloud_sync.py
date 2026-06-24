"""
Cloud sync — backup and restore history & notes to cloud storage.
Supports: local file backup, S3-compatible, WebDAV.
"""

import json
import logging
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("Astra.CloudSync")

DATA_DIR = Path(__file__).parent.parent / "data"
BACKUP_DIR = Path(__file__).parent.parent / "backups"


def _timestamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def export_data(assistant):
    """Export all data to a JSON file."""
    data = {
        "version": "3.2",
        "exported_at": _timestamp(),
        "history": getattr(assistant, "history", []),
        "notes": getattr(assistant, "notes", []),
        "config": {
            "voice_enabled": assistant.voice_enabled,
        },
    }
    return data


def local_backup(assistant):
    """Create a local backup file."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    data = export_data(assistant)
    path = BACKUP_DIR / f"astra_backup_{_timestamp()}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Backup saved: %s", path)
    return str(path)


def local_restore(path):
    """Restore from a local backup file."""
    p = Path(path)
    if not p.exists():
        return {"error": f"File not found: {path}"}
    try:
        data = json.loads(p.read_text("utf-8"))
        logger.info("Restored backup: %s (%d events)", path, len(data.get("history", [])))
        return data
    except Exception as e:
        return {"error": f"Invalid backup: {e}"}


def list_backups():
    """List available local backups."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backups = sorted(BACKUP_DIR.glob("astra_backup_*.json"), reverse=True)
    return [
        {
            "path": str(b),
            "name": b.name,
            "size": b.stat().st_size,
            "date": datetime.fromtimestamp(b.stat().st_mtime).isoformat(),
        }
        for b in backups
    ]


def cloud_push(source_path, destination_url):
    """
    Push a file to cloud storage.
    Supports: file:// copies locally, others try urllib.
    """
    if destination_url.startswith("file://"):
        dest = destination_url[7:]
        Path(dest).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, dest)
        return {"status": "ok", "destination": dest}
    try:
        import urllib.request
        with open(source_path, "rb") as f:
            data = f.read()
        req = urllib.request.Request(destination_url, data=data, method="PUT")
        req.add_header("Content-Type", "application/json")
        urllib.request.urlopen(req, timeout=10)
        return {"status": "ok", "destination": destination_url}
    except ImportError:
        return {"error": "urllib not available"}
    except Exception as e:
        return {"error": str(e)}
