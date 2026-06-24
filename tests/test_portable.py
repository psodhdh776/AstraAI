import pytest
import tempfile
from pathlib import Path
from modules.portable import ensure_dirs


class TestPortable:
    def test_ensure_dirs_creates_directories(self):
        import modules.portable as p
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "data"
            p._DATA_DIR = base
            p._MODULES_DIR = Path(tmp) / "modules"
            p._MODULES_DIR.mkdir(exist_ok=True)
            ensure_dirs()
            assert (base / "backups").exists()
            assert (base / "plugins").exists()
            assert (base / "profiles").exists()

    def test_ensure_dirs_idempotent(self):
        import modules.portable as p
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "data"
            p._DATA_DIR = base
            p._MODULES_DIR = Path(tmp) / "modules"
            p._MODULES_DIR.mkdir(exist_ok=True)
            ensure_dirs()
            ensure_dirs()
            assert (base / "backups").exists()
