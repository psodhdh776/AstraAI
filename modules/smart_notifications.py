"""
Smart notifications — context-based reminders and alerts.
"""

import logging
import re
import threading
import time
from datetime import datetime, timedelta

logger = logging.getLogger("Astra.Notifications")

# Time patterns
TIME_PATTERNS = [
    (re.compile(r'через\s+(\d+)\s*(мин|минут|минуту|чаc|час|часов)'), lambda m, now: _parse_delta(m, now)),
    (re.compile(r'в\s+(\d{1,2}):(\d{2})'), lambda m, now: _parse_time(m, now)),
    (re.compile(r'завтра\s+в\s+(\d{1,2}):(\d{2})'), lambda m, now: _parse_tomorrow(m, now)),
    (re.compile(r'через\s+(\d+)\s*(с|сек|секунд)'), lambda m, now: now + timedelta(seconds=int(m.group(1)))),
    (re.compile(r'через\s+(\d+)\s*(д|дня|дней|день)'), lambda m, now: now + timedelta(days=int(m.group(1)))),
]

KEYWORD_TIMERS = {
    "напомни": 300, "не забудь": 300, "запомни": 3600,
    "через час": 3600, "через 30 мин": 1800, "через 5 мин": 300,
}


def _parse_delta(m, now):
    num = int(m.group(1))
    unit = m.group(2)
    if unit.startswith("мин"):
        return now + timedelta(minutes=num)
    return now + timedelta(hours=num)


def _parse_time(m, now):
    h, mi = int(m.group(1)), int(m.group(2))
    t = now.replace(hour=h, minute=mi, second=0)
    if t <= now:
        t += timedelta(days=1)
    return t


def _parse_tomorrow(m, now):
    h, mi = int(m.group(1)), int(m.group(2))
    t = now.replace(hour=h, minute=mi, second=0) + timedelta(days=1)
    return t


def detect_reminder(text):
    """Returns (reminder_text, trigger_time) or None."""
    text = text.lower().strip()
    now = datetime.now()

    # Check explicit time patterns
    for pattern, parser in TIME_PATTERNS:
        m = pattern.search(text)
        if m:
            reminder = pattern.sub("", text).strip()
            trigger = parser(m, now)
            if trigger:
                return (reminder or "Напоминание", trigger)

    # Check keyword-based timers
    for kw, delay in KEYWORD_TIMERS.items():
        if kw in text:
            reminder = text.replace(kw, "").strip()
            if not reminder:
                reminder = kw
            return (reminder, now + timedelta(seconds=delay))

    return None


def check_due_reminders(reminders):
    """Returns list of due reminders from a list of (text, timestamp) tuples."""
    now = datetime.now().timestamp()
    due = []
    remaining = []
    for text, ts in reminders:
        if ts <= now:
            due.append(text)
        else:
            remaining.append((text, ts))
    return due, remaining
