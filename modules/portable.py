"""
Portable version helper — enables USB/Temp usage with relative paths.
"""
from pathlib import Path

_DATA_DIR = Path(__file__).parent.parent / "data"
_MODULES_DIR = Path(__file__).parent


def ensure_dirs():
    for d in (_DATA_DIR, _DATA_DIR / "backups", _DATA_DIR / "plugins", _DATA_DIR / "profiles"):
        d.mkdir(parents=True, exist_ok=True)
