"""Tests for storage module (Database v2)."""
import json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "modules"))
import pytest
from storage import Database


@pytest.fixture
def db(tmp_path):
    d = Database(str(tmp_path / "test.db"))
    yield d
    d.close()


def test_config(db):
    db.set_config("test_key", "hello")
    rows = db.query("config", where={"key": "test_key"})
    assert rows[0]["value"] == "hello"
    rows = db.query("config", where={"key": "nonexistent"})
    assert len(rows) == 0


def test_notes(db):
    db.save_notes([{"id": "1", "text": "test note", "created": "today", "done": False}])
    notes = db.get_notes()
    assert len(notes) == 1
    assert notes[0]["text"] == "test note"
    assert notes[0]["done"] is False

    # get_notes() filters done=0, so saving as done=1 removes from results
    db.save_notes([{"id": "2", "text": "second note", "created": "today", "done": False}])
    notes = db.get_notes()
    assert len(notes) == 1
    assert notes[0]["id"] == "2"


def test_history(db):
    db.add_history("user", "hello")
    db.add_history("assistant", "hi there")
    hist = db.get_history()
    assert len(hist) == 2
    assert hist[0]["role"] == "user"
    assert hist[1]["role"] == "assistant"

    # Clear via positive test: add then query again
    db.add_history("user", "extra")
    hist2 = db.get_history()
    assert len(hist2) == 3


def test_history_fts(db):
    db.add_history("user", "как дела?")
    db.add_history("assistant", "всё отлично!")
    # Rebuild FTS index explicitly after insert
    db.execute("INSERT INTO history_fts(history_fts) VALUES('rebuild')")
    import time
    time.sleep(0.5)
    results = db.search("дела")
    assert len(results) >= 1


def test_reminders(db):
    db.add_reminder("test reminder", 60)
    reminders = db.get_reminders()
    assert len(reminders) == 1


def test_memory(db):
    db.insert("memory", {"key": "key1", "value": json.dumps({"nested": "value"})})
    rows = db.query("memory", where={"key": "key1"})
    assert json.loads(rows[0]["value"]) == {"nested": "value"}
    rows = db.query("memory", where={"key": "nonexistent"})
    assert len(rows) == 0


def test_daily_stats(db):
    db.log_daily()
    db.log_daily()
    rows = db.query("daily_stats")
    assert len(rows) >= 1


def test_command_usage(db):
    import datetime
    now = datetime.datetime.now().isoformat()
    db.insert("command_usage", {"command": "screenshot", "timestamp": now, "duration_ms": 150})
    db.insert("command_usage", {"command": "search", "timestamp": now, "duration_ms": 200})
    rows = db.execute(
        "SELECT command, COUNT(*) as cnt FROM command_usage GROUP BY command ORDER BY cnt DESC"
    )
    assert len(rows) == 2


def test_dialogue_feedback(db):
    import datetime
    now = datetime.datetime.now().isoformat()
    db.insert("dialogue_feedback", {"user_text": "hello", "response_text": "hi", "rating": 5, "timestamp": now})
    db.insert("dialogue_feedback", {"user_text": "bad", "response_text": "sorry", "rating": 1, "timestamp": now})
    assert db.count("dialogue_feedback") == 2


def test_mood_log(db):
    import datetime
    now = datetime.datetime.now().isoformat()
    db.insert("mood_log", {"mood": "happy", "timestamp": now})
    db.insert("mood_log", {"mood": "sad", "timestamp": now})
    rows = db.query("mood_log", order_by="id ASC")
    assert len(rows) >= 2


def test_vocabulary(db):
    import datetime
    now = datetime.datetime.now().isoformat()
    db.execute(
        "INSERT OR REPLACE INTO learned_vocabulary (word, frequency, first_seen, last_seen) "
        "VALUES (?, COALESCE((SELECT frequency + 1 FROM learned_vocabulary WHERE word = ?), 1), ?, ?)",
        ["привет", "привет", now, now]
    )
    db.execute(
        "INSERT OR REPLACE INTO learned_vocabulary (word, frequency, first_seen, last_seen) "
        "VALUES (?, COALESCE((SELECT frequency + 1 FROM learned_vocabulary WHERE word = ?), 1), ?, ?)",
        ["привет", "привет", now, now]
    )
    rows = db.query("learned_vocabulary", where={"word": "привет"})
    assert rows[0]["frequency"] == 2


def test_knowledge_base(db):
    import datetime
    now = datetime.datetime.now().isoformat()
    db.insert("knowledge_base", {"question": "What is Python?", "answer": "A programming language", "category": "tech", "created": now})
    rows = db.execute("SELECT * FROM knowledge_base WHERE question LIKE ?", ["%Python%"])
    assert len(rows) >= 1
    assert "programming" in rows[0]["answer"]


def test_quick_replies(db):
    import datetime
    now = datetime.datetime.now().isoformat()
    db.insert("quick_replies", {"trigger": "hello", "response": "Hi there!", "created": now})
    rows = db.query("quick_replies", where={"trigger": "hello"})
    assert rows[0]["response"] == "Hi there!"
    rows = db.query("quick_replies", where={"trigger": "nonexistent"})
    assert len(rows) == 0


def test_plugin_config(db):
    db.insert("plugin_config", {"plugin": "test_plugin", "key": "api_key", "value": "abc123"})
    rows = db.query("plugin_config", where={"plugin": "test_plugin", "key": "api_key"})
    assert rows[0]["value"] == "abc123"
    rows = db.query("plugin_config", where={"plugin": "test_plugin", "key": "nonexistent"})
    assert len(rows) == 0


def test_preferences(db):
    import datetime
    now = datetime.datetime.now().isoformat()
    db.insert("user_preferences", {"key": "theme", "value": "dark", "updated_at": now})
    rows = db.query("user_preferences", where={"key": "theme"})
    assert rows[0]["value"] == "dark"


def test_health(db):
    health = db.health_check()
    assert health["status"] == "ok"
    assert health["integrity"] == "ok"
    assert "tables" in health


def test_backup(db):
    db.set_config("test", "value")
    result = db.backup()
    assert result is not None
    assert Path(result).exists()


def test_table_count(db):
    cnt = db.table_count()
    assert cnt >= 10


def test_insert_many(db):
    import datetime
    now = datetime.datetime.now().isoformat()
    rows_data = [
        {"key": f"k{i}", "value": f"v{i}"}
        for i in range(10)
    ]
    # Use memory table for bulk insert test
    db.insert_many("memory", [{"key": f"bulk_{i}", "value": f"val_{i}"} for i in range(5)])
    assert db.count("memory", where={"key": "bulk_0"}) == 1


def test_encryption(db):
    db.add_history("user", "secret text")
    hist = db.get_history()
    last_id = db.execute("SELECT MAX(id) as mid FROM history")[0]["mid"]
    db.set_encrypted("history", last_id, "secret text")
    decrypted = db.get_encrypted("history", last_id)
    assert decrypted == "secret text"
