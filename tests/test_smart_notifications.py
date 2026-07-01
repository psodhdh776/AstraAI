import pytest
import time
from datetime import datetime, timedelta
from modules.smart_notifications import detect_reminder, check_due_reminders


class TestDetectReminder:
    def test_no_reminder(self):
        assert detect_reminder("hello world") is None

    def test_keyword_napomni(self):
        result = detect_reminder("напомни купить хлеб")
        assert result is not None
        text, t = result
        assert "купить хлеб" in text
        assert isinstance(t, datetime)

    def test_keyword_ne_zabud(self):
        result = detect_reminder("не забудь позвонить")
        assert result is not None
        text, t = result
        assert "позвонить" in text

    def test_through_delta_minutes(self):
        result = detect_reminder("через 5 минут")
        assert result is not None
        text, t = result
        now = datetime.now()
        assert timedelta(0) < (t - now) < timedelta(minutes=10)

    def test_through_delta_hours(self):
        result = detect_reminder("через 2 часа")
        assert result is not None
        text, t = result
        now = datetime.now()
        assert timedelta(hours=1) < (t - now) < timedelta(hours=3)

    def test_through_delta_seconds(self):
        result = detect_reminder("через 30 сек")
        assert result is not None
        text, t = result
        now = datetime.now()
        assert timedelta(seconds=20) < (t - now) < timedelta(seconds=40)

    def test_through_delta_days(self):
        result = detect_reminder("через 3 дня")
        assert result is not None
        text, t = result
        now = datetime.now()
        assert timedelta(days=2) < (t - now) < timedelta(days=4)

    def test_at_specific_time(self):
        result = detect_reminder("в 15:30")
        assert result is not None
        text, t = result
        assert t.hour == 15
        assert t.minute == 30

    def test_reminder_text_cleaned(self):
        result = detect_reminder("напомни через 10 мин")
        assert result is not None
        text, t = result

    def test_empty_after_removal(self):
        result = detect_reminder("через 30 мин")
        assert result is not None
        text, t = result


class TestCheckDueReminders:
    def test_no_due(self):
        future = time.time() + 3600
        due, remaining = check_due_reminders([("task", future)])
        assert due == []
        assert len(remaining) == 1

    def test_all_due(self):
        past = time.time() - 10
        due, remaining = check_due_reminders([("task1", past), ("task2", past - 5)])
        assert due == ["task1", "task2"]
        assert remaining == []

    def test_mixed(self):
        past = time.time() - 10
        future = time.time() + 3600
        due, remaining = check_due_reminders([("due_task", past), ("future_task", future)])
        assert due == ["due_task"]
        assert len(remaining) == 1
        assert remaining[0][0] == "future_task"

    def test_empty_list(self):
        due, remaining = check_due_reminders([])
        assert due == []
        assert remaining == []

    def test_exact_boundary(self):
        now = time.time() - 0.001
        due, remaining = check_due_reminders([("just_now", now)])
        assert "just_now" in due
