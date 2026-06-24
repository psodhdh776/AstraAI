import pytest
import json
import tempfile
from pathlib import Path
from modules.cloud_sync import export_data, local_backup, local_restore, list_backups, cloud_push


class FakeAssistant:
    history = [{"role": "user", "text": "hello"}]
    notes = [{"text": "my note"}]
    voice_enabled = True


class TestCloudSync:
    def test_export_data(self):
        a = FakeAssistant()
        data = export_data(a)
        assert data["version"] == "3.2"
        assert len(data["history"]) == 1
        assert len(data["notes"]) == 1
        assert data["config"]["voice_enabled"] is True

    def test_export_empty(self):
        class Empty:
            history = []
            notes = []
            voice_enabled = False
        data = export_data(Empty())
        assert data["history"] == []
        assert data["notes"] == []

    def test_local_backup_and_restore(self, monkeypatch):
        import modules.cloud_sync as cs
        with tempfile.TemporaryDirectory() as tmp:
            cs.BACKUP_DIR = Path(tmp) / "backups"
            a = FakeAssistant()
            path = local_backup(a)
            assert Path(path).exists()
            data = local_restore(path)
            assert data["version"] == "3.2"
            assert len(data["history"]) == 1

    def test_local_restore_file_not_found(self):
        result = local_restore("nonexistent.json")
        assert "error" in result
        assert "File not found" in result["error"]

    def test_local_restore_invalid_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bad.json"
            p.write_text("not json", encoding="utf-8")
            result = local_restore(str(p))
            assert "error" in result
            assert "Invalid backup" in result["error"]

    def test_list_backups(self, monkeypatch):
        import modules.cloud_sync as cs
        with tempfile.TemporaryDirectory() as tmp:
            cs.BACKUP_DIR = Path(tmp) / "backups"
            backups = list_backups()
            assert backups == []

    def test_cloud_push_file(self, monkeypatch):
        import modules.cloud_sync as cs
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "source.json"
            src.write_text("{}", encoding="utf-8")
            dest = Path(tmp) / "dest" / "file.json"
            result = cloud_push(str(src), f"file://{dest}")
            assert result["status"] == "ok"
            assert dest.exists()
